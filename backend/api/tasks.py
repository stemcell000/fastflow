import logging
import os
import shutil
from pathlib import Path

import docker
from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone

from datetime import timedelta

from .models import ChunkedUpload, Fastq, PipelineRun, Setting, StepArtifact, StepRun

logger = logging.getLogger(__name__)


@shared_task
def cleanup_stale_chunked_uploads():
    """Deletes abandoned chunked uploads (no chunk received in the last
    STALE_UPLOAD_HOURS) and their associated temporary file — prevents
    orphaned files that can weigh several tens/hundreds of GB from
    accumulating for FASTQ uploads that were never completed."""
    cutoff = timezone.now() - timedelta(hours=settings.STALE_UPLOAD_HOURS)
    stale = ChunkedUpload.objects.filter(completed=False, updated_at__lt=cutoff)

    removed, errors = 0, 0
    for upload in stale:
        try:
            upload.temp_path.unlink(missing_ok=True)
        except OSError:
            logger.exception("Unable to delete the temporary file for upload %s", upload.pk)
            errors += 1
            continue
        upload.delete()
        removed += 1

    if removed or errors:
        logger.info("Cleanup of abandoned uploads: %s removed, %s error(s).", removed, errors)
    return {'removed': removed, 'errors': errors}


@shared_task
def send_reminders():
    """
        Nothing yet ...
    """


# ═══════════════════════════════════════════════════════════════════════════
# FASTQ pipeline execution engine (DAG of steps in isolated Docker
# containers). See models.py for PipelineTemplate/PipelineStep/
# PipelineRun/StepRun/StepArtifact.
# ═══════════════════════════════════════════════════════════════════════════

def _run_container_path(pipeline_run_id, step_id, media_root):
    return Path(media_root) / 'pipeline_runs' / str(pipeline_run_id) / str(step_id)


def _link_or_copy(src, dst):
    """Hard link (instant, no copy) when src/dst are on the same volume —
    essential for FASTQ files that can reach ~200 GB; falls back to a copy
    if the hard link isn't possible (different volumes)."""
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def launch_pipeline_run(pipeline_run_id):
    """Materializes one StepRun per template step, then starts the steps
    with no dependencies. Called once, when the PipelineRun is created."""
    with transaction.atomic():
        run = PipelineRun.objects.select_for_update().get(pk=pipeline_run_id)
        if run.status != PipelineRun.Status.PENDING:
            return
        steps = list(run.template.steps.all())
        StepRun.objects.bulk_create([
            StepRun(pipeline_run=run, step=step) for step in steps
        ])
        run.status = PipelineRun.Status.RUNNING
        run.started_at = timezone.now()
        run.save(update_fields=['status', 'started_at'])
    _advance_pipeline(pipeline_run_id)


def _advance_pipeline(pipeline_run_id):
    """Re-evaluates the DAG: queues steps whose dependencies have all
    succeeded, skips those with a failed dependency, and closes the run once
    every step is in a terminal state."""
    to_dispatch = []
    with transaction.atomic():
        run = PipelineRun.objects.select_for_update().get(pk=pipeline_run_id)
        step_runs = list(
            run.step_runs.select_related('step').prefetch_related('step__depends_on')
        )
        by_step_id = {sr.step_id: sr for sr in step_runs}

        for sr in step_runs:
            if sr.status != StepRun.Status.PENDING:
                continue
            dep_runs = [
                by_step_id[dep.id] for dep in sr.step.depends_on.all()
                if dep.id in by_step_id
            ]
            if any(d.status == StepRun.Status.FAILED or d.status == StepRun.Status.SKIPPED for d in dep_runs):
                sr.status = StepRun.Status.SKIPPED
                sr.save(update_fields=['status'])
            elif all(d.status == StepRun.Status.SUCCESS for d in dep_runs):
                sr.status = StepRun.Status.QUEUED
                sr.save(update_fields=['status'])
                to_dispatch.append(sr.id)

        terminal = {StepRun.Status.SUCCESS, StepRun.Status.FAILED, StepRun.Status.SKIPPED}
        if step_runs and all(sr.status in terminal for sr in step_runs):
            any_failed = any(sr.status == StepRun.Status.FAILED for sr in step_runs)
            run.status = PipelineRun.Status.FAILED if any_failed else PipelineRun.Status.SUCCESS
            run.finished_at = timezone.now()
            run.save(update_fields=['status', 'finished_at'])

    for step_run_id in to_dispatch:
        transaction.on_commit(lambda sid=step_run_id: execute_step_task.delay(sid))


def _prepare_workspace(step_run):
    """Copies the step's inputs (dependency outputs, or the original FASTQ
    files if the step is a DAG root) and its script into a dedicated
    workspace directory. Returns (host_path, django_container_path)."""
    container_root = _run_container_path(step_run.pipeline_run_id, step_run.step_id, settings.MEDIA_ROOT)
    host_root = _run_container_path(step_run.pipeline_run_id, step_run.step_id, settings.HOST_MEDIA_ROOT)
    in_dir = container_root / 'in'
    out_dir = container_root / 'out'
    in_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    step = step_run.step
    dep_step_ids = list(step.depends_on.values_list('id', flat=True))

    if dep_step_ids:
        dep_runs = StepRun.objects.filter(
            pipeline_run_id=step_run.pipeline_run_id, step_id__in=dep_step_ids
        ).prefetch_related('artifacts')
        for dep_run in dep_runs:
            for artifact in dep_run.artifacts.filter(kind=StepArtifact.Kind.OUTPUT):
                if artifact.file and Path(artifact.file.path).exists():
                    _link_or_copy(artifact.file.path, in_dir / Path(artifact.file.name).name)
    else:
        fastq = step_run.pipeline_run.fastq
        for fastq_file in fastq.fastq_files.all():
            if fastq_file.file and Path(fastq_file.file.path).exists():
                _link_or_copy(fastq_file.file.path, in_dir / Path(fastq_file.file.name).name)

    if step.script and step.script.script_file:
        ext = Path(step.script.script_file.name).suffix or ''
        shutil.copy2(step.script.script_file.path, container_root / f'script{ext}')

    return host_root, container_root


def _collect_outputs(step_run, container_root):
    out_dir = container_root / 'out'
    for path in sorted(out_dir.glob('**/*')):
        if path.is_file():
            relative = path.relative_to(settings.MEDIA_ROOT)
            StepArtifact.objects.create(
                step_run=step_run,
                kind=StepArtifact.Kind.OUTPUT,
                label=path.name,
                file=str(relative),
            )


@shared_task(bind=True)
def execute_step_task(self, step_run_id):
    step_run = StepRun.objects.select_related('step', 'pipeline_run').get(pk=step_run_id)
    step_run.status = StepRun.Status.RUNNING
    step_run.started_at = timezone.now()
    step_run.celery_task_id = self.request.id or ''
    step_run.save(update_fields=['status', 'started_at', 'celery_task_id'])

    try:
        host_root, container_root = _prepare_workspace(step_run)
        exit_code, logs = _run_step_container(step_run, host_root)
    except Exception as exc:
        logger.exception("Step %s failed (step_run=%s)", step_run.step.name, step_run_id)
        step_run.status = StepRun.Status.FAILED
        step_run.log = f"Execution error: {exc}"
        step_run.finished_at = timezone.now()
        step_run.save(update_fields=['status', 'log', 'finished_at'])
        _advance_pipeline(step_run.pipeline_run_id)
        return

    step_run.exit_code = exit_code
    step_run.log = logs
    step_run.finished_at = timezone.now()
    if exit_code == 0:
        step_run.status = StepRun.Status.SUCCESS
        step_run.save(update_fields=['exit_code', 'log', 'finished_at', 'status'])
        _collect_outputs(step_run, container_root)
    else:
        step_run.status = StepRun.Status.FAILED
        step_run.save(update_fields=['exit_code', 'log', 'finished_at', 'status'])

    _advance_pipeline(step_run.pipeline_run_id)


class StepExecutionError(Exception):
    """Infrastructure (Docker) error, distinct from a script that fails
    normally with a non-zero exit code."""


def _run_step_container(step_run, host_root):
    step = step_run.step
    timeout = step.timeout_seconds or settings.PIPELINE_STEP_DEFAULT_TIMEOUT

    try:
        client = docker.from_env()
    except docker.errors.DockerException as exc:
        raise StepExecutionError(f"Docker unavailable on the worker: {exc}") from exc

    try:
        container = client.containers.run(
            image=step.docker_image,
            command=["sh", "-c", step.command],
            working_dir="/work",
            volumes={str(host_root): {"bind": "/work", "mode": "rw"}},
            mem_limit=settings.PIPELINE_STEP_MEM_LIMIT,
            network_disabled=True,
            detach=True,
        )
    except docker.errors.ImageNotFound as exc:
        raise StepExecutionError(f"Docker image not found: {step.docker_image}") from exc
    except docker.errors.APIError as exc:
        raise StepExecutionError(f"Docker error while starting the container: {exc}") from exc

    timed_out = False
    try:
        result = container.wait(timeout=timeout)
        exit_code = result.get("StatusCode", 1)
    except Exception:
        timed_out = True
        try:
            container.kill()
        except docker.errors.APIError:
            pass  # already stopped
    finally:
        try:
            logs = container.logs(stdout=True, stderr=True).decode('utf-8', errors='replace')
        except docker.errors.APIError:
            logs = ""
        container.remove(force=True)

    if timed_out:
        raise StepExecutionError(
            f"Timeout exceeded ({timeout}s) — step interrupted.\nPartial log:\n{logs}"
        )

    return exit_code, logs
