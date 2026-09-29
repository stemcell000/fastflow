import json
import os
from pathlib import Path

from django import forms
from django.conf import settings
from django.contrib import messages
from django.core.files.storage import default_storage
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
)
from .models import (
    Sample, Protocol, NgsSample, SequencingBatch, SequencingBatchFile,
    SequencingProduct, Fastq, FastqFile, ChunkedUpload, ManualRun, Script,
    ScriptParameter, ScriptLanguage, Setting, Count, Analysis,
    PipelineTemplate, PipelineStep, PipelineRun, StepRun, StepArtifact,
)
from .tasks import launch_pipeline_run as _launch_pipeline_run


# ─── Accueil ──────────────────────────────────────────────────────────────────

class HomeView(TemplateView):
    template_name = 'ngs/home.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['stats'] = [
            {'label': 'Samples', 'count': Sample.objects.count(), 'url': 'ngs:sample-list'},
            {'label': 'Protocols', 'count': Protocol.objects.count(), 'url': 'ngs:protocol-list'},
            {'label': 'NGS Samples', 'count': NgsSample.objects.count(), 'url': 'ngs:ngssample-list'},
            {'label': 'Sequencing batches', 'count': SequencingBatch.objects.count(), 'url': 'ngs:sequencingbatch-list'},
            {'label': 'Sequencing products', 'count': SequencingProduct.objects.count(), 'url': 'ngs:sequencingproduct-list'},
            {'label': 'Pipelines', 'count': PipelineTemplate.objects.count(), 'url': 'ngs:pipelinetemplate-list'},
            {'label': 'Scripts', 'count': Script.objects.count(), 'url': 'ngs:script-list'},
        ]
        ctx['recent_samples'] = Sample.objects.all()[:5]
        return ctx


# ─── Samples ──────────────────────────────────────────────────────────────────

class SampleListView(ListView):
    model = Sample
    template_name = 'ngs/sample_list.html'
    context_object_name = 'samples'
    paginate_by = 20


class SampleDetailView(DetailView):
    model = Sample
    template_name = 'ngs/sample_detail.html'
    context_object_name = 'sample'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['protocols'] = self.object.protocols.all()
        return ctx


SAMPLE_FIELDS = [
    'name', 'project_name', 'sample_type', 'sample_type_other', 'plasmid_number',
    'production_number', 'biological_model', 'organ', 'organ_other', 'serotype',
    'serotype_other', 'condition', 'injection_type', 'injection_type_other', 'description',
]


class SampleCreateView(CreateView):
    model = Sample
    template_name = 'ngs/sample_form.html'
    fields = SAMPLE_FIELDS
    success_url = reverse_lazy('ngs:sample-list')


class SampleUpdateView(UpdateView):
    model = Sample
    template_name = 'ngs/sample_form.html'
    fields = SAMPLE_FIELDS
    success_url = reverse_lazy('ngs:sample-list')


class SampleDeleteView(DeleteView):
    model = Sample
    template_name = 'ngs/sample_confirm_delete.html'
    success_url = reverse_lazy('ngs:sample-list')


# ─── Protocols ────────────────────────────────────────────────────────────────

class ProtocolListView(ListView):
    model = Protocol
    template_name = 'ngs/protocol_list.html'
    context_object_name = 'protocols'
    paginate_by = 20


class ProtocolDetailView(DetailView):
    model = Protocol
    template_name = 'ngs/protocol_detail.html'
    context_object_name = 'protocol'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['ngs_samples'] = self.object.ngs_samples.all()
        return ctx


PROTOCOL_FIELDS = ['samples', 'primer_pair', 'commentary', 'protocol_description_file']


class ProtocolCreateView(CreateView):
    model = Protocol
    template_name = 'ngs/protocol_form.html'
    fields = PROTOCOL_FIELDS
    success_url = reverse_lazy('ngs:protocol-list')


class ProtocolUpdateView(UpdateView):
    model = Protocol
    template_name = 'ngs/protocol_form.html'
    fields = PROTOCOL_FIELDS
    success_url = reverse_lazy('ngs:protocol-list')


class ProtocolDeleteView(DeleteView):
    model = Protocol
    template_name = 'ngs/protocol_confirm_delete.html'
    success_url = reverse_lazy('ngs:protocol-list')


# ─── NGS Samples ──────────────────────────────────────────────────────────────

class NgsSampleListView(ListView):
    model = NgsSample
    template_name = 'ngs/ngssample_list.html'
    context_object_name = 'ngs_samples'
    paginate_by = 20


class NgsSampleDetailView(DetailView):
    model = NgsSample
    template_name = 'ngs/ngssample_detail.html'
    context_object_name = 'ngs_sample'


def _parse_float_or_none(value):
    value = (value or '').strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def ngssample_bulk_view(request):
    """A Protocol can be linked to several Samples (many-to-many); this view
    lets the user pick a Protocol and fill in one NGS-sample row per
    associated Sample in a single table, instead of one form per sample.
    Re-visiting for the same protocol lets you edit the rows already saved
    (NgsSample.sample is one-to-one, so this is a create-or-update)."""
    protocol_id = request.GET.get('protocol') or request.POST.get('protocol')
    protocol = None
    if protocol_id and protocol_id.isdigit():
        protocol = Protocol.objects.filter(pk=protocol_id).first()

    if request.method == 'POST' and protocol:
        samples = list(protocol.samples.all())
        row_errors = []
        with transaction.atomic():
            for sample in samples:
                prefix = f'sample_{sample.pk}_'
                operating_name = (request.POST.get(prefix + 'operating_name') or '').strip()
                if not operating_name:
                    row_errors.append(f"{sample.name}: operating name is required.")
                    continue
                NgsSample.objects.update_or_create(
                    sample=sample,
                    defaults={
                        'protocol': protocol,
                        'operating_name': operating_name,
                        'index_1': (request.POST.get(prefix + 'index_1') or '').strip(),
                        'index_2': (request.POST.get(prefix + 'index_2') or '').strip(),
                        'final_concentration': _parse_float_or_none(request.POST.get(prefix + 'final_concentration')),
                    },
                )
        if row_errors:
            for err in row_errors:
                messages.error(request, err)
        else:
            messages.success(request, f'NGS samples saved for protocol "{protocol.primer_pair or protocol.pk}".')
            return redirect('ngs:ngssample-list')

    rows = []
    if protocol:
        for sample in protocol.samples.all():
            existing = NgsSample.objects.filter(sample=sample).first()
            rows.append({
                'sample': sample,
                'operating_name': existing.operating_name if existing else sample.name,
                'index_1': existing.index_1 if existing else '',
                'index_2': existing.index_2 if existing else '',
                'final_concentration': existing.final_concentration if existing else '',
            })

    return render(request, 'ngs/ngssample_bulk_form.html', {
        'protocols': Protocol.objects.all(),
        'protocol': protocol,
        'rows': rows,
    })


NGSSAMPLE_FIELDS = ['sample', 'protocol', 'operating_name', 'index_1', 'index_2', 'final_concentration', 'bioanalyzer_file']


class NgsSampleUpdateView(UpdateView):
    model = NgsSample
    template_name = 'ngs/ngssample_form.html'
    fields = NGSSAMPLE_FIELDS
    success_url = reverse_lazy('ngs:ngssample-list')


class NgsSampleDeleteView(DeleteView):
    model = NgsSample
    template_name = 'ngs/ngssample_confirm_delete.html'
    success_url = reverse_lazy('ngs:ngssample-list')


# ─── Sequencing Batches ───────────────────────────────────────────────────────

class SequencingBatchListView(ListView):
    model = SequencingBatch
    template_name = 'ngs/sequencingbatch_list.html'
    context_object_name = 'batches'
    paginate_by = 20


class SequencingBatchDetailView(DetailView):
    model = SequencingBatch
    template_name = 'ngs/sequencingbatch_detail.html'
    context_object_name = 'batch'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['batch_files'] = self.object.batch_files.all()
        ctx['sequencing_products'] = self.object.sequencing_products.all()
        ctx['batch_ngs_samples'] = self.object.ngs_samples.all()
        return ctx


def sequencingbatch_form_view(request, pk=None):
    """A batch pools together several NGS samples (multiplexed by index) for
    one sequencing run — a one-to-many relation held as a FK on NgsSample.
    Only NGS samples with a non-empty index_1 can be added to a batch."""
    batch = get_object_or_404(SequencingBatch, pk=pk) if pk else None

    available = NgsSample.objects.exclude(index_1='')
    if batch:
        available = available | NgsSample.objects.filter(sequencing_batch=batch)
    available = available.distinct().select_related('sample').order_by('operating_name')

    if request.method == 'POST':
        selected_ids = request.POST.getlist('ngs_samples')
        with transaction.atomic():
            if batch is None:
                batch = SequencingBatch.objects.create()
            NgsSample.objects.filter(sequencing_batch=batch).exclude(pk__in=selected_ids).update(sequencing_batch=None)
            if selected_ids:
                NgsSample.objects.filter(pk__in=selected_ids).update(sequencing_batch=batch)
        messages.success(request, f'Sequencing batch #{batch.pk} saved.')
        return redirect('ngs:sequencingbatch-detail', pk=batch.pk)

    selected_ids = set(batch.ngs_samples.values_list('pk', flat=True)) if batch else set()
    return render(request, 'ngs/sequencingbatch_form.html', {
        'batch': batch,
        'available_samples': available,
        'selected_ids': selected_ids,
    })


class SequencingBatchDeleteView(DeleteView):
    model = SequencingBatch
    template_name = 'ngs/sequencingbatch_confirm_delete.html'
    success_url = reverse_lazy('ngs:sequencingbatch-list')


# ─── Sequencing Batch Files ───────────────────────────────────────────────────

class SequencingBatchFileCreateView(CreateView):
    model = SequencingBatchFile
    template_name = 'ngs/sequencingbatchfile_form.html'
    fields = ['sequencing_batch', 'file', 'table_de_calcul']
    success_url = reverse_lazy('ngs:sequencingbatch-list')


class SequencingBatchFileUpdateView(UpdateView):
    model = SequencingBatchFile
    template_name = 'ngs/sequencingbatchfile_form.html'
    fields = ['sequencing_batch', 'file', 'table_de_calcul']
    success_url = reverse_lazy('ngs:sequencingbatch-list')


class SequencingBatchFileDeleteView(DeleteView):
    model = SequencingBatchFile
    template_name = 'ngs/sequencingbatchfile_confirm_delete.html'
    success_url = reverse_lazy('ngs:sequencingbatch-list')


# ─── Sequencing Products ──────────────────────────────────────────────────────

class SequencingProductListView(ListView):
    model = SequencingProduct
    template_name = 'ngs/sequencingproduct_list.html'
    context_object_name = 'products'
    paginate_by = 20


class SequencingProductDetailView(DetailView):
    model = SequencingProduct
    template_name = 'ngs/sequencingproduct_detail.html'
    context_object_name = 'product'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['fastqs'] = self.object.fastqs.all()
        return ctx


class SequencingProductCreateView(CreateView):
    model = SequencingProduct
    template_name = 'ngs/sequencingproduct_form.html'
    fields = [
        'sequencing_batch', 'date', 'summary_file', 'sequencing_machine',
        'flowcell', 'read_length', 'read_depth', 'phix_proportion',
        'custom_recipe', 'custom_recipe_start', 'custom_recipe_end',
    ]
    success_url = reverse_lazy('ngs:sequencingproduct-list')


class SequencingProductUpdateView(UpdateView):
    model = SequencingProduct
    template_name = 'ngs/sequencingproduct_form.html'
    fields = [
        'sequencing_batch', 'date', 'summary_file', 'sequencing_machine',
        'flowcell', 'read_length', 'read_depth', 'phix_proportion',
        'custom_recipe', 'custom_recipe_start', 'custom_recipe_end',
    ]
    success_url = reverse_lazy('ngs:sequencingproduct-list')


class SequencingProductDeleteView(DeleteView):
    model = SequencingProduct
    template_name = 'ngs/sequencingproduct_confirm_delete.html'
    success_url = reverse_lazy('ngs:sequencingproduct-list')


# ─── FASTQ ────────────────────────────────────────────────────────────────────

class FastqDetailView(DetailView):
    model = Fastq
    template_name = 'ngs/fastq_detail.html'
    context_object_name = 'fastq'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['fastq_files'] = self.object.fastq_files.all()
        ctx['manual_run'] = getattr(self.object.sequencing_product, 'manual_run', None)
        return ctx


class FastqCreateView(CreateView):
    model = Fastq
    template_name = 'ngs/fastq_form.html'
    fields = ['sequencing_product', 'ngs_sample']
    success_url = reverse_lazy('ngs:sequencingproduct-list')


class FastqDeleteView(DeleteView):
    model = Fastq
    template_name = 'ngs/fastq_confirm_delete.html'
    success_url = reverse_lazy('ngs:sequencingproduct-list')


# ─── FASTQ Files (chunked upload with resume — files up to ~200 GB) ─────────

def fastqfile_upload_view(request):
    """FASTQ file upload page: chunked upload with resume after a network
    interruption, rather than a single HTTP POST (impractical at the scale
    of files that can reach several tens/hundreds of GB).

    The user picks a sequencing product, then an NGS sample from the list
    restricted to that product's batch (each NGS sample's operating name is
    conventionally also the uploaded file's name, so files added in bulk can
    be auto-matched to their NGS sample by filename)."""
    product_id = request.GET.get('product')
    selected_product = get_object_or_404(SequencingProduct, pk=product_id) if product_id else None
    ngs_sample_id = request.GET.get('ngs_sample')
    selected_ngs_sample = None
    if ngs_sample_id and selected_product:
        selected_ngs_sample = NgsSample.objects.filter(
            pk=ngs_sample_id, sequencing_batch=selected_product.sequencing_batch
        ).first()
    return render(request, 'ngs/fastqfile_upload.html', {
        'products': SequencingProduct.objects.all(),
        'selected_product': selected_product,
        'selected_ngs_sample': selected_ngs_sample,
        'chunk_size': settings.UPLOAD_CHUNK_SIZE,
    })


@require_GET
def sequencingproduct_ngs_samples(request, pk):
    """NGS samples available for a sequencing product: those belonging to the
    same sequencing batch — feeds the upload page's dynamic dropdown."""
    product = get_object_or_404(SequencingProduct, pk=pk)
    samples = product.sequencing_batch.ngs_samples.all() if product.sequencing_batch else NgsSample.objects.none()
    return JsonResponse({'ok': True, 'ngs_samples': [
        {'id': s.pk, 'operating_name': s.operating_name} for s in samples
    ]})


@require_POST
def chunked_upload_init(request):
    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({'ok': False, 'error': "Invalid request."}, status=400)

    product = get_object_or_404(SequencingProduct, pk=payload.get('sequencing_product_id'))
    ngs_sample = None
    ngs_sample_id = payload.get('ngs_sample_id')
    if ngs_sample_id:
        ngs_sample = get_object_or_404(NgsSample, pk=ngs_sample_id)
    fastq, _ = Fastq.objects.get_or_create(sequencing_product=product, ngs_sample=ngs_sample)

    filename = (payload.get('filename') or '').strip()
    total_size = payload.get('total_size')
    if not filename or not isinstance(total_size, int) or total_size <= 0:
        return JsonResponse({'ok': False, 'error': "Invalid filename or size."}, status=400)

    # Resume: an identical incomplete upload (same fastq/name/size) is resumed
    # instead of creating a new one — allows resuming after the browser was
    # closed, with nothing to store on the client side.
    upload = ChunkedUpload.objects.filter(
        fastq=fastq, filename=filename, total_size=total_size, completed=False,
    ).first()
    if upload is None:
        upload = ChunkedUpload.objects.create(
            fastq=fastq,
            filename=filename,
            comment=(payload.get('comment') or '').strip(),
            total_size=total_size,
            uploaded_by=request.user if request.user.is_authenticated else None,
        )
        upload.temp_path.touch(exist_ok=True)
    elif payload.get('comment'):
        upload.comment = payload['comment'].strip()
        upload.save(update_fields=['comment'])

    return JsonResponse({'ok': True, 'upload_id': str(upload.pk), 'offset': upload.offset, 'fastq_id': fastq.pk})


@require_GET
def chunked_upload_status(request, upload_id):
    upload = get_object_or_404(ChunkedUpload, pk=upload_id)
    return JsonResponse({'ok': True, 'offset': upload.offset, 'completed': upload.completed})


@require_POST
def chunked_upload_chunk(request, upload_id):
    upload = get_object_or_404(ChunkedUpload, pk=upload_id)
    if upload.completed:
        return JsonResponse({'ok': True, 'offset': upload.offset, 'completed': True})

    try:
        chunk_offset = int(request.headers.get('X-Chunk-Offset', -1))
    except (TypeError, ValueError):
        chunk_offset = -1

    if chunk_offset != upload.offset:
        # Client out of sync (resume): return the real offset so it can realign.
        return JsonResponse({'ok': False, 'error': 'offset_mismatch', 'offset': upload.offset}, status=409)

    chunk = request.body
    if not chunk:
        return JsonResponse({'ok': False, 'error': "Empty chunk."}, status=400)
    if upload.offset + len(chunk) > upload.total_size:
        return JsonResponse({'ok': False, 'error': "Exceeds the announced size."}, status=400)

    with open(upload.temp_path, 'ab') as f:
        f.write(chunk)
    upload.offset += len(chunk)

    if upload.offset == upload.total_size:
        upload.completed = True
        _finalize_chunked_upload(upload)
    upload.save(update_fields=['offset', 'completed', 'updated_at'])

    return JsonResponse({'ok': True, 'offset': upload.offset, 'completed': upload.completed})


def _finalize_chunked_upload(upload):
    desired_name = str(Path('fastq') / 'files' / upload.filename)
    final_name = default_storage.get_available_name(desired_name)
    final_abs = Path(settings.MEDIA_ROOT) / final_name
    final_abs.parent.mkdir(parents=True, exist_ok=True)
    os.replace(upload.temp_path, final_abs)  # same volume as MEDIA_ROOT: instant, even at 200 GB
    FastqFile.objects.create(fastq=upload.fastq, file=final_name, comment=upload.comment)


class FastqFileDeleteView(DeleteView):
    model = FastqFile
    template_name = 'ngs/fastqfile_confirm_delete.html'
    success_url = reverse_lazy('ngs:sequencingproduct-list')


# ─── Suivis manuels (ex-« Pipeline ») ─────────────────────────────────────────

class ManualRunListView(ListView):
    model = ManualRun
    template_name = 'ngs/manualrun_list.html'
    context_object_name = 'manual_runs'
    paginate_by = 20


class ManualRunDetailView(DetailView):
    model = ManualRun
    template_name = 'ngs/manualrun_detail.html'
    context_object_name = 'manual_run'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['scripts'] = self.object.scripts.all()
        ctx['counts'] = self.object.counts.all()
        ctx['analyses'] = self.object.analyses.all()
        ctx['fastqs'] = self.object.fastqs
        return ctx


class ManualRunCreateView(CreateView):
    model = ManualRun
    template_name = 'ngs/manualrun_form.html'
    fields = ['sequencing_product']
    success_url = reverse_lazy('ngs:manualrun-list')


class ManualRunUpdateView(UpdateView):
    model = ManualRun
    template_name = 'ngs/manualrun_form.html'
    fields = ['sequencing_product']
    success_url = reverse_lazy('ngs:manualrun-list')


class ManualRunDeleteView(DeleteView):
    model = ManualRun
    template_name = 'ngs/manualrun_confirm_delete.html'
    success_url = reverse_lazy('ngs:manualrun-list')


# ─── Scripts (standalone registry, independent of pipelines/manual runs) ──────

SCRIPT_FIELDS = ['name', 'language', 'version', 'comment', 'script_file', 'manual_run']


class ScriptListView(ListView):
    model = Script
    template_name = 'ngs/script_list.html'
    context_object_name = 'scripts'
    paginate_by = 20


class ScriptDetailView(DetailView):
    model = Script
    template_name = 'ngs/script_detail.html'
    context_object_name = 'script'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['pipeline_steps'] = self.object.pipeline_steps.select_related('template').all()
        return ctx


ScriptForm = forms.modelform_factory(Script, fields=SCRIPT_FIELDS)
ScriptParameterFormSet = forms.inlineformset_factory(
    Script, ScriptParameter, fields=['name', 'description'], extra=1, can_delete=True,
    widgets={
        'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'E.g. --input'}),
        'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'What to enter for this parameter'}),
    },
)


def script_form_view(request, pk=None):
    """Script create/edit, with an inline formset for its 1-n execution
    parameters (name + description of each argument to enter to run it)."""
    script = get_object_or_404(Script, pk=pk) if pk else None

    if request.method == 'POST':
        form = ScriptForm(request.POST, request.FILES, instance=script)
        formset = ScriptParameterFormSet(request.POST, instance=script)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                script = form.save()
                formset.instance = script
                formset.save()
            messages.success(request, f'Script "{script}" saved.')
            return redirect('ngs:script-list')
    else:
        form = ScriptForm(instance=script)
        formset = ScriptParameterFormSet(instance=script)

    return render(request, 'ngs/script_form.html', {
        'form': form, 'formset': formset, 'script': script,
    })


class ScriptDeleteView(DeleteView):
    model = Script
    template_name = 'ngs/script_confirm_delete.html'
    success_url = reverse_lazy('ngs:script-list')


# ─── Settings ─────────────────────────────────────────────────────────────────

class SettingCreateView(CreateView):
    model = Setting
    template_name = 'ngs/setting_form.html'
    fields = ['script', 'settings_json']
    success_url = reverse_lazy('ngs:manualrun-list')


class SettingUpdateView(UpdateView):
    model = Setting
    template_name = 'ngs/setting_form.html'
    fields = ['script', 'settings_json']
    success_url = reverse_lazy('ngs:manualrun-list')


class SettingDeleteView(DeleteView):
    model = Setting
    template_name = 'ngs/setting_confirm_delete.html'
    success_url = reverse_lazy('ngs:manualrun-list')


# ─── Counts ───────────────────────────────────────────────────────────────────

class CountCreateView(CreateView):
    model = Count
    template_name = 'ngs/count_form.html'
    fields = ['manual_run', 'counts_file']
    success_url = reverse_lazy('ngs:manualrun-list')


class CountUpdateView(UpdateView):
    model = Count
    template_name = 'ngs/count_form.html'
    fields = ['manual_run', 'counts_file']
    success_url = reverse_lazy('ngs:manualrun-list')


class CountDeleteView(DeleteView):
    model = Count
    template_name = 'ngs/count_confirm_delete.html'
    success_url = reverse_lazy('ngs:manualrun-list')


# ─── Analysis ─────────────────────────────────────────────────────────────────

class AnalysisCreateView(CreateView):
    model = Analysis
    template_name = 'ngs/analysis_form.html'
    fields = ['manual_run', 'trimming_table_file', 'logo_plot_file']
    success_url = reverse_lazy('ngs:manualrun-list')


class AnalysisUpdateView(UpdateView):
    model = Analysis
    template_name = 'ngs/analysis_form.html'
    fields = ['manual_run', 'trimming_table_file', 'logo_plot_file']
    success_url = reverse_lazy('ngs:manualrun-list')


class AnalysisDeleteView(DeleteView):
    model = Analysis
    template_name = 'ngs/analysis_confirm_delete.html'
    success_url = reverse_lazy('ngs:manualrun-list')


# ─── Pipeline execution engine (DAG of steps in containers) ─────────────────

class PipelineTemplateListView(ListView):
    model = PipelineTemplate
    template_name = 'ngs/pipelinetemplate_list.html'
    context_object_name = 'templates'
    paginate_by = 20


class PipelineTemplateDetailView(DetailView):
    model = PipelineTemplate
    template_name = 'ngs/pipelinetemplate_detail.html'
    context_object_name = 'template'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['steps'] = self.object.steps.prefetch_related('depends_on').all()
        return ctx


def pipeline_builder_view(request, pk=None):
    """Visual editor (nodes + connectors) for a pipeline template."""
    template = get_object_or_404(PipelineTemplate, pk=pk) if pk else None
    steps = list(template.steps.prefetch_related('depends_on').all()) if template else []

    drawflow_id = {step.pk: i for i, step in enumerate(steps, start=1)}
    nodes = [
        {
            'db_id': step.pk,
            'name': step.name,
            'language': step.language,
            'docker_image': step.docker_image,
            'script_id': step.script_id,
            'command': step.command,
            'timeout_seconds': step.timeout_seconds,
            'pos_x': 60 + (drawflow_id[step.pk] - 1) % 4 * 260,
            'pos_y': 60 + (drawflow_id[step.pk] - 1) // 4 * 240,
            'depends_on': [d.pk for d in step.depends_on.all() if d.pk in drawflow_id],
        }
        for step in steps
    ]
    scripts = [
        {'id': s.pk, 'label': str(s), 'language': s.language}
        for s in Script.objects.all()
    ]

    context = {
        'template': template,
        'initial_nodes_json': json.dumps(nodes),
        'language_choices_json': json.dumps(list(PipelineStep.Language.choices)),
        'scripts_json': json.dumps(scripts),
    }
    return render(request, 'ngs/pipelinetemplate_builder.html', context)


@require_POST
def script_quick_create(request):
    """Quick script creation from the pipeline visual editor."""
    name = (request.POST.get('name') or '').strip()
    if not name:
        return JsonResponse({'ok': False, 'error': "The script name is required."}, status=400)

    script = Script.objects.create(
        name=name,
        language=request.POST.get('language') or ScriptLanguage.PYTHON,
        version=(request.POST.get('version') or '').strip(),
        comment=(request.POST.get('comment') or '').strip(),
        script_file=request.FILES.get('script_file'),
    )
    return JsonResponse({'ok': True, 'id': script.pk, 'label': str(script), 'language': script.language})


@require_POST
def pipeline_builder_save(request, pk=None):
    """Receives the visual editor's graph (JSON) and converts it into
    PipelineTemplate/PipelineStep/depends_on."""
    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({'ok': False, 'error': "Invalid data."}, status=400)

    name = (payload.get('name') or '').strip()
    if not name:
        return JsonResponse({'ok': False, 'error': "The template name is required."}, status=400)

    submitted_nodes = payload.get('nodes', [])
    if not submitted_nodes:
        return JsonResponse({'ok': False, 'error': "Add at least one step."}, status=400)

    with transaction.atomic():
        if pk:
            template = get_object_or_404(PipelineTemplate, pk=pk)
            template.name = name
            template.description = payload.get('description', '')
            template.save(update_fields=['name', 'description'])
        else:
            template = PipelineTemplate.objects.create(name=name, description=payload.get('description', ''))

        submitted_ids = {n['db_id'] for n in submitted_nodes if n.get('db_id')}
        template.steps.exclude(pk__in=submitted_ids).delete()

        client_to_step = {}
        for n in submitted_nodes:
            fields = {
                'name': (n.get('name') or 'Étape').strip(),
                'language': n.get('language') or PipelineStep.Language.PYTHON,
                'docker_image': (n.get('docker_image') or 'python:3.11-slim').strip(),
                'script_id': n.get('script_id') or None,
                'command': n.get('command') or '',
                'timeout_seconds': n.get('timeout_seconds') or None,
            }
            if n.get('db_id'):
                step = template.steps.get(pk=n['db_id'])
                for key, value in fields.items():
                    setattr(step, key, value)
                step.save()
            else:
                step = template.steps.create(**fields)
            client_to_step[str(n['client_id'])] = step

        deps_by_target = {}
        for edge in payload.get('edges', []):
            deps_by_target.setdefault(str(edge['to']), []).append(str(edge['from']))

        for client_id, step in client_to_step.items():
            dep_steps = [
                client_to_step[c] for c in deps_by_target.get(client_id, [])
                if c in client_to_step
            ]
            step.depends_on.set(dep_steps)

    return JsonResponse({
        'ok': True,
        'redirect': reverse('ngs:pipelinetemplate-detail', args=[template.pk]),
    })


def pipeline_run_launch(request, fastq_pk=None):
    """Choose a FASTQ (unless already given) and a pipeline template, then
    launch it. Reachable either from a FASTQ's detail page (FASTQ pre-set) or
    from the pipeline-runs list page (FASTQ picked from a dropdown)."""
    fastq = get_object_or_404(Fastq, pk=fastq_pk) if fastq_pk else None
    templates = PipelineTemplate.objects.all()
    fastqs = Fastq.objects.select_related('sequencing_product', 'ngs_sample').all() if fastq is None else None

    if request.method == 'POST':
        if fastq is None:
            fastq_id = request.POST.get('fastq', '')
            fastq = Fastq.objects.filter(pk=fastq_id).first() if fastq_id.isdigit() else None
        template_id = request.POST.get('template', '')
        template = templates.filter(pk=template_id).first() if template_id.isdigit() else None
        if fastq is None:
            messages.error(request, "Please choose a valid FASTQ.")
        elif template is None:
            messages.error(request, "Please choose a valid pipeline template.")
        elif not template.steps.exists():
            messages.error(request, "This pipeline template has no steps.")
        else:
            run = PipelineRun.objects.create(
                fastq=fastq,
                template=template,
                launched_by=request.user if request.user.is_authenticated else None,
            )
            _launch_pipeline_run(run.pk)
            messages.success(request, f'Pipeline "{template.name}" launched.')
            return redirect('ngs:pipelinerun-detail', pk=run.pk)

    return render(request, 'ngs/pipelinerun_launch.html', {
        'fastq': fastq, 'templates': templates, 'fastqs': fastqs,
    })


class PipelineRunListView(ListView):
    model = PipelineRun
    template_name = 'ngs/pipelinerun_list.html'
    context_object_name = 'runs'
    paginate_by = 20


class PipelineRunDetailView(DetailView):
    model = PipelineRun
    template_name = 'ngs/pipelinerun_detail.html'
    context_object_name = 'run'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        step_runs = list(
            self.object.step_runs
            .select_related('step')
            .prefetch_related('step__depends_on', 'artifacts')
            .all()
        )
        for sr in step_runs:
            sr.report_items = None
            sr.report_raw = None
            sr.report_error = None
            all_artifacts = list(sr.artifacts.all())
            sr.output_artifacts = [a for a in all_artifacts if a.kind == StepArtifact.Kind.OUTPUT]
            report_artifact = next(
                (a for a in all_artifacts if a.kind == StepArtifact.Kind.REPORT), None
            )
            if report_artifact and report_artifact.file:
                try:
                    with report_artifact.file.open('rb') as f:
                        data = json.loads(f.read().decode('utf-8'))
                    if isinstance(data, dict):
                        sr.report_items = data.items()
                    else:
                        sr.report_raw = json.dumps(data, indent=2)
                except (OSError, ValueError):
                    sr.report_error = "Could not read report.json (invalid JSON or missing file)."
        ctx['step_runs'] = step_runs
        return ctx
