import uuid
from pathlib import Path

from django.conf import settings
from django.db import models


class Sample(models.Model):
    class SampleType(models.TextChoices):
        CELL_LINE = 'cell_line', 'Cell Line'
        PRIMARY_CULTURE = 'primary_culture', 'Primary Culture'
        TISSUE = 'tissue', 'Tissue'
        ORGANOID = 'organoid', 'Organoid'
        AAV = 'aav', 'AAV'
        PLASMID = 'plasmid', 'Plasmid'
        OTHER = 'other', 'Other'

    # Kept for backward compatibility with any code still importing it.
    SAMPLE_TYPE_CHOICES = SampleType.choices

    class BiologicalModel(models.TextChoices):
        HUMAN = 'human', 'Human'
        MACACA_MULATTA = 'macaca_mulatta', 'Macaca mulata'
        CHLOROCEBUS = 'chlorocebus', 'Chlorocebeus'
        MOUSE = 'mouse', 'Mouse'
        PIG = 'pig', 'Pig'
        OTHER = 'other', 'Other'

    class Organ(models.TextChoices):
        RETINA = 'retina', 'Retina'
        BRAIN_CORTEX = 'brain_cortex', 'Brain-Cortex'
        BRAIN_LGN = 'brain_lgn', 'Brain-LGN'
        MUSCLE = 'muscle', 'Muscle'
        COCHLEA = 'cochlea', 'Cochlea'
        OTHER = 'other', 'Other'

    class Serotype(models.TextChoices):
        AAV2 = 'aav2', 'AAV2'
        AAV5 = 'aav5', 'AAV5'
        AAV9 = 'aav9', 'AAV9'
        OTHER = 'other', 'Other'

    class Condition(models.TextChoices):
        EX_VIVO = 'ex_vivo', 'Ex vivo'
        IN_VIVO = 'in_vivo', 'In vivo'
        IN_VITRO = 'in_vitro', 'In vitro'

    class InjectionType(models.TextChoices):
        SUB_RETINAL = 'sub_retinal', 'Sub retinal'
        INTRA_VITREAL = 'intra_vitreal', 'Intra vitreal'
        OTHER = 'other', 'Other'

    created_at = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=255)
    project_name = models.CharField(max_length=255, blank=True)
    sample_type = models.CharField(max_length=50, choices=SampleType.choices, blank=True)
    sample_type_other = models.CharField(
        max_length=255, blank=True, verbose_name='Sample type (other)',
        help_text="Shown only when Sample type = Other.",
    )
    plasmid_number = models.IntegerField(
        null=True, blank=True, help_text="Shown only when Sample type = Plasmid.",
    )
    production_number = models.IntegerField(
        null=True, blank=True, help_text="Shown only when Sample type = AAV.",
    )
    biological_model = models.CharField(max_length=50, choices=BiologicalModel.choices, blank=True)
    organ = models.CharField(max_length=50, choices=Organ.choices, blank=True)
    organ_other = models.CharField(
        max_length=255, blank=True, verbose_name='Organ (other)',
        help_text="Shown only when Organ = Other.",
    )
    serotype = models.CharField(max_length=50, choices=Serotype.choices, blank=True)
    serotype_other = models.CharField(
        max_length=255, blank=True, verbose_name='Serotype (other)',
        help_text="Shown only when Serotype = Other.",
    )
    condition = models.CharField(
        max_length=50, choices=Condition.choices, blank=True, verbose_name='Conditions',
    )
    injection_type = models.CharField(max_length=50, choices=InjectionType.choices, blank=True)
    injection_type_other = models.CharField(
        max_length=255, blank=True, verbose_name='Injection type (other)',
        help_text="Shown only when Injection type = Other.",
    )
    description = models.CharField(max_length=1000, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.project_name})" if self.project_name else self.name


class Protocol(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    primer_pair = models.CharField(max_length=255, blank=True)
    commentary = models.TextField(blank=True)
    protocol_description_file = models.FileField(
        upload_to='protocols/descriptions/', blank=True, null=True
    )
    samples = models.ManyToManyField(
        Sample, related_name='protocols',
        help_text="One protocol can be associated with several samples.",
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Protocol #{self.pk} — {self.primer_pair}"


class NgsSample(models.Model):
    # One NGS sample corresponds to exactly one originating Sample — a given
    # Sample can be prepped for sequencing at most once.
    sample = models.OneToOneField(
        Sample, on_delete=models.CASCADE, related_name='ngs_sample',
    )
    protocol = models.ForeignKey(
        Protocol, on_delete=models.CASCADE, related_name='ngs_samples'
    )
    operating_name = models.CharField(
        max_length=255,
        help_text="Sequencing operating name. Defaults to the originating sample's name.",
    )
    index_1 = models.CharField(max_length=255, blank=True, verbose_name='Index 1')
    index_2 = models.CharField(max_length=255, blank=True, verbose_name='Index 2')
    final_concentration = models.FloatField(null=True, blank=True)
    bioanalyzer_file = models.FileField(
        upload_to='ngs_samples/bioanalyzer/', blank=True, null=True
    )
    # A sequencing batch pools together several NGS samples (multiplexed by
    # index) for a single sequencing run — one batch, many NGS samples.
    sequencing_batch = models.ForeignKey(
        'SequencingBatch', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='ngs_samples',
    )

    def __str__(self):
        return f"NGS Sample #{self.pk} ({self.operating_name})"


class SequencingBatch(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Sequencing Batch #{self.pk}"


class SequencingBatchFile(models.Model):
    file = models.FileField(upload_to='sequencing_batches/files/', blank=True, null=True)
    table_de_calcul = models.FileField(
        verbose_name='calculation table',
        upload_to='sequencing_batches/tables/', blank=True, null=True
    )
    sequencing_batch = models.ForeignKey(
        SequencingBatch, on_delete=models.CASCADE, related_name='batch_files'
    )

    def __str__(self):
        return f"Batch File #{self.pk} (Batch #{self.sequencing_batch_id})"


class SequencingProduct(models.Model):
    date = models.CharField(max_length=50, blank=True)
    summary_file = models.FileField(
        upload_to='sequencing_products/summaries/', blank=True, null=True
    )
    sequencing_machine = models.CharField(max_length=255, blank=True)
    flowcell = models.CharField(max_length=255, blank=True)
    read_length = models.IntegerField(null=True, blank=True)
    read_depth = models.IntegerField(null=True, blank=True)
    phix_proportion = models.FloatField(null=True, blank=True)
    custom_recipe = models.BooleanField(default=False)
    custom_recipe_start = models.IntegerField(null=True, blank=True)
    custom_recipe_end = models.IntegerField(null=True, blank=True)
    sequencing_batch = models.ForeignKey(
        SequencingBatch, on_delete=models.CASCADE, related_name='sequencing_products'
    )

    def __str__(self):
        return f"Sequencing Product #{self.pk} — {self.sequencing_machine}"


class Fastq(models.Model):
    sequencing_product = models.ForeignKey(
        SequencingProduct, on_delete=models.CASCADE, related_name='fastqs'
    )
    # Which NGS sample (multiplexed within the sequencing product) this FASTQ
    # deliverable was demultiplexed for.
    ngs_sample = models.ForeignKey(
        NgsSample, on_delete=models.SET_NULL, null=True, blank=True, related_name='fastqs'
    )

    def __str__(self):
        return f"FASTQ #{self.pk}"


class FastqFile(models.Model):
    file = models.FileField(upload_to='fastq/files/', blank=True, null=True)
    comment = models.CharField(max_length=1000, blank=True)
    fastq = models.ForeignKey(
        Fastq, on_delete=models.CASCADE, related_name='fastq_files'
    )

    def __str__(self):
        return f"FASTQ File #{self.pk}"


class ChunkedUpload(models.Model):
    """Tracks a large file upload sent in chunks, resumable after a network
    interruption (FASTQ files can reach ~200 GB)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fastq = models.ForeignKey(Fastq, on_delete=models.CASCADE, related_name='chunked_uploads')
    filename = models.CharField(max_length=255)
    comment = models.CharField(max_length=1000, blank=True)
    total_size = models.BigIntegerField()
    offset = models.BigIntegerField(default=0)
    completed = models.BooleanField(default=False)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Chunked upload"
        verbose_name_plural = "Chunked uploads"

    def __str__(self):
        return f"{self.filename} ({self.offset}/{self.total_size})"

    @property
    def temp_path(self):
        upload_dir = Path(settings.MEDIA_ROOT) / 'uploads_tmp'
        upload_dir.mkdir(parents=True, exist_ok=True)
        return upload_dir / str(self.id)


class ManualRun(models.Model):
    """Manual file tracking for a sequencing product (script/settings/counts/
    analysis uploaded by hand). One manual run follows one sequencing product
    and, through it, all of the FASTQs demultiplexed from that product —
    distinct from the pipeline execution engine (PipelineTemplate/PipelineRun
    below), which actually runs the processing."""
    sequencing_product = models.OneToOneField(
        SequencingProduct, on_delete=models.CASCADE, related_name='manual_run'
    )

    @property
    def fastqs(self):
        return self.sequencing_product.fastqs.all()

    class Meta:
        verbose_name = "Manual run"
        verbose_name_plural = "Manual runs"

    def __str__(self):
        return f"Manual run #{self.pk}"


class ScriptLanguage(models.TextChoices):
    PYTHON = 'python', 'Python'
    C = 'c', 'C'
    CPP = 'cpp', 'C++'
    BASH = 'bash', 'Bash'
    OTHER = 'other', 'Other'


class Script(models.Model):
    """Versioned registry of reusable scripts: attachable to a manual run
    (legacy) and/or selectable as a pipeline step."""
    name = models.CharField(max_length=255, blank=True)
    script_file = models.FileField(upload_to='pipelines/scripts/', blank=True, null=True)
    language = models.CharField(max_length=20, choices=ScriptLanguage.choices, default=ScriptLanguage.PYTHON)
    version = models.CharField(max_length=50, blank=True)
    comment = models.CharField(max_length=1000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    manual_run = models.ForeignKey(
        ManualRun, on_delete=models.CASCADE, related_name='scripts', null=True, blank=True
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        label = self.name or f"Script #{self.pk}"
        return f"{label} ({self.get_language_display()}{f' v{self.version}' if self.version else ''})"


class ScriptParameter(models.Model):
    """A parameter the script expects to be run (e.g. a CLI argument), with a
    description of what to enter — documents how to execute the script."""
    script = models.ForeignKey(Script, on_delete=models.CASCADE, related_name='parameters')
    name = models.CharField(max_length=255)
    description = models.CharField(max_length=1000, blank=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return self.name


class Setting(models.Model):
    settings_json = models.FileField(
        upload_to='pipelines/settings/', blank=True, null=True
    )
    script = models.ForeignKey(
        Script, on_delete=models.CASCADE, related_name='settings'
    )

    def __str__(self):
        return f"Settings #{self.pk} (Script #{self.script_id})"


class Count(models.Model):
    counts_file = models.FileField(upload_to='pipelines/counts/', blank=True, null=True)
    manual_run = models.ForeignKey(
        ManualRun, on_delete=models.CASCADE, related_name='counts'
    )

    def __str__(self):
        return f"Count #{self.pk} (Manual run #{self.manual_run_id})"


class Analysis(models.Model):
    trimming_table_file = models.FileField(
        upload_to='pipelines/analysis/trimming/', blank=True, null=True
    )
    logo_plot_file = models.FileField(
        upload_to='pipelines/analysis/logo/', blank=True, null=True
    )
    manual_run = models.ForeignKey(
        ManualRun, on_delete=models.CASCADE, related_name='analyses'
    )

    def __str__(self):
        return f"Analysis #{self.pk} (Manual run #{self.manual_run_id})"

    class Meta:
        verbose_name = "Analysis"
        verbose_name_plural = "Analyses"


# ═══════════════════════════════════════════════════════════════════════════
# Pipeline execution engine for FASTQ files.
#
# A PipelineTemplate describes a reusable DAG of steps (PipelineStep +
# dependencies). A PipelineRun is the launch of that DAG on a given Fastq: it
# materializes one StepRun per step, executed in an isolated Docker container
# as soon as its dependencies have succeeded (independent branches therefore
# start in parallel). Produced files are tracked via StepArtifact and serve as
# input to the following steps.
# ═══════════════════════════════════════════════════════════════════════════

class PipelineTemplate(models.Model):
    name = models.CharField(max_length=255)
    description = models.CharField(max_length=1000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Pipeline template"
        verbose_name_plural = "Pipeline templates"

    def __str__(self):
        return self.name


class PipelineStep(models.Model):
    # Alias kept for compatibility: the language choices are defined once on
    # Script and shared here (the language chosen for the step filters the
    # list of scripts offered in the visual editor).
    Language = ScriptLanguage

    template = models.ForeignKey(
        PipelineTemplate, on_delete=models.CASCADE, related_name='steps'
    )
    name = models.CharField(max_length=255)
    language = models.CharField(max_length=20, choices=ScriptLanguage.choices, default=ScriptLanguage.PYTHON)
    docker_image = models.CharField(
        max_length=255,
        default='python:3.11-slim',
        help_text="Docker image that runs the step (e.g. python:3.11-slim, gcc:13, debian:bookworm-slim).",
    )
    script = models.ForeignKey(
        Script, on_delete=models.PROTECT, null=True, blank=True, related_name='pipeline_steps',
        help_text="Registry script to run (mounted in the container as /work/script.<ext>).",
    )
    command = models.TextField(
        help_text=(
            "Shell command executed in the container (cwd=/work). "
            "Inputs are available in /work/in/, outputs are expected in /work/out/. "
            "E.g.: python /work/script.py --input /work/in --output /work/out. "
            "If the script writes a report.json file to /work/out/, it is captured "
            "as the step's execution report and its contents are shown on the run's report page."
        ),
    )
    depends_on = models.ManyToManyField(
        'self', symmetrical=False, blank=True, related_name='dependents',
        help_text="Steps in the same template that must succeed before this one.",
    )
    timeout_seconds = models.IntegerField(
        null=True, blank=True,
        help_text="Maximum execution time before forced failure (defaults to the project-wide value).",
    )

    class Meta:
        ordering = ['template', 'name']
        verbose_name = "Pipeline step"
        verbose_name_plural = "Pipeline steps"

    def __str__(self):
        return f"{self.name} ({self.template.name})"


class PipelineRun(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        RUNNING = 'running', 'Running'
        SUCCESS = 'success', 'Success'
        FAILED = 'failed', 'Failed'

    fastq = models.ForeignKey(
        Fastq, on_delete=models.CASCADE, related_name='pipeline_runs'
    )
    template = models.ForeignKey(
        PipelineTemplate, on_delete=models.PROTECT, related_name='runs'
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    launched_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='pipeline_runs',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Pipeline run"
        verbose_name_plural = "Pipeline runs"

    def __str__(self):
        return f"{self.template.name} on FASTQ #{self.fastq_id} — {self.get_status_display()}"


class StepRun(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        QUEUED = 'queued', 'Queued'
        RUNNING = 'running', 'Running'
        SUCCESS = 'success', 'Success'
        FAILED = 'failed', 'Failed'
        SKIPPED = 'skipped', 'Skipped'

    pipeline_run = models.ForeignKey(
        PipelineRun, on_delete=models.CASCADE, related_name='step_runs'
    )
    step = models.ForeignKey(
        PipelineStep, on_delete=models.CASCADE, related_name='runs'
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    celery_task_id = models.CharField(max_length=255, blank=True)
    exit_code = models.IntegerField(null=True, blank=True)
    log = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['pipeline_run', 'step__name']
        unique_together = ('pipeline_run', 'step')
        verbose_name = "Step run"
        verbose_name_plural = "Step runs"

    def __str__(self):
        return f"{self.step.name} — {self.get_status_display()}"


class StepArtifact(models.Model):
    class Kind(models.TextChoices):
        INPUT = 'input', 'Input'
        OUTPUT = 'output', 'Output'
        REPORT = 'report', 'Report'

    step_run = models.ForeignKey(
        StepRun, on_delete=models.CASCADE, related_name='artifacts'
    )
    kind = models.CharField(max_length=10, choices=Kind.choices)
    label = models.CharField(max_length=255)
    file = models.FileField(upload_to='pipeline_runs/artifacts/%Y/%m/%d/')

    class Meta:
        ordering = ['step_run', 'kind', 'label']
        verbose_name = "Pipeline file"
        verbose_name_plural = "Pipeline files"

    def __str__(self):
        return f"{self.label} ({self.get_kind_display()})"
