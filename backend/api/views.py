from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView
)
from django.urls import reverse_lazy
from .models import (
    Sample, Protocol, NgsSample, SequencingBatch, SequencingBatchFile,
    SequencingProduct, Fastq, FastqFile, Pipeline, Script, Setting, Count, Analysis
)


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


class SampleCreateView(CreateView):
    model = Sample
    template_name = 'ngs/sample_form.html'
    fields = [
        'name', 'project_name', 'sample_type', 'plasmid_number',
        'production_number', 'biological_model', 'organ', 'serotype',
        'condition', 'description',
    ]
    success_url = reverse_lazy('ngs:sample-list')


class SampleUpdateView(UpdateView):
    model = Sample
    template_name = 'ngs/sample_form.html'
    fields = [
        'name', 'project_name', 'sample_type', 'plasmid_number',
        'production_number', 'biological_model', 'organ', 'serotype',
        'condition', 'description',
    ]
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


class ProtocolCreateView(CreateView):
    model = Protocol
    template_name = 'ngs/protocol_form.html'
    fields = ['sample', 'primer_pair', 'commentary', 'protocol_description_file']
    success_url = reverse_lazy('ngs:protocol-list')


class ProtocolUpdateView(UpdateView):
    model = Protocol
    template_name = 'ngs/protocol_form.html'
    fields = ['sample', 'primer_pair', 'commentary', 'protocol_description_file']
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

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['sequencing_batches'] = self.object.sequencing_batches.all()
        return ctx


class NgsSampleCreateView(CreateView):
    model = NgsSample
    template_name = 'ngs/ngssample_form.html'
    fields = ['protocol', 'index', 'final_concentration', 'bioanalyzer_file']
    success_url = reverse_lazy('ngs:ngssample-list')


class NgsSampleUpdateView(UpdateView):
    model = NgsSample
    template_name = 'ngs/ngssample_form.html'
    fields = ['protocol', 'index', 'final_concentration', 'bioanalyzer_file']
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
        return ctx


class SequencingBatchCreateView(CreateView):
    model = SequencingBatch
    template_name = 'ngs/sequencingbatch_form.html'
    fields = ['ngs_sample']
    success_url = reverse_lazy('ngs:sequencingbatch-list')


class SequencingBatchUpdateView(UpdateView):
    model = SequencingBatch
    template_name = 'ngs/sequencingbatch_form.html'
    fields = ['ngs_sample']
    success_url = reverse_lazy('ngs:sequencingbatch-list')


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
        ctx['pipelines'] = self.object.pipelines.all()
        return ctx


class FastqCreateView(CreateView):
    model = Fastq
    template_name = 'ngs/fastq_form.html'
    fields = ['sequencing_product']
    success_url = reverse_lazy('ngs:sequencingproduct-list')


class FastqDeleteView(DeleteView):
    model = Fastq
    template_name = 'ngs/fastq_confirm_delete.html'
    success_url = reverse_lazy('ngs:sequencingproduct-list')


# ─── FASTQ Files ──────────────────────────────────────────────────────────────

class FastqFileCreateView(CreateView):
    model = FastqFile
    template_name = 'ngs/fastqfile_form.html'
    fields = ['fastq', 'file']
    success_url = reverse_lazy('ngs:sequencingproduct-list')


class FastqFileDeleteView(DeleteView):
    model = FastqFile
    template_name = 'ngs/fastqfile_confirm_delete.html'
    success_url = reverse_lazy('ngs:sequencingproduct-list')


# ─── Pipelines ────────────────────────────────────────────────────────────────

class PipelineListView(ListView):
    model = Pipeline
    template_name = 'ngs/pipeline_list.html'
    context_object_name = 'pipelines'
    paginate_by = 20


class PipelineDetailView(DetailView):
    model = Pipeline
    template_name = 'ngs/pipeline_detail.html'
    context_object_name = 'pipeline'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['scripts'] = self.object.scripts.all()
        ctx['counts'] = self.object.counts.all()
        ctx['analyses'] = self.object.analyses.all()
        return ctx


class PipelineCreateView(CreateView):
    model = Pipeline
    template_name = 'ngs/pipeline_form.html'
    fields = ['fastq']
    success_url = reverse_lazy('ngs:pipeline-list')


class PipelineDeleteView(DeleteView):
    model = Pipeline
    template_name = 'ngs/pipeline_confirm_delete.html'
    success_url = reverse_lazy('ngs:pipeline-list')


# ─── Scripts ──────────────────────────────────────────────────────────────────

class ScriptCreateView(CreateView):
    model = Script
    template_name = 'ngs/script_form.html'
    fields = ['pipeline', 'script_file']
    success_url = reverse_lazy('ngs:pipeline-list')


class ScriptUpdateView(UpdateView):
    model = Script
    template_name = 'ngs/script_form.html'
    fields = ['pipeline', 'script_file']
    success_url = reverse_lazy('ngs:pipeline-list')


class ScriptDeleteView(DeleteView):
    model = Script
    template_name = 'ngs/script_confirm_delete.html'
    success_url = reverse_lazy('ngs:pipeline-list')


# ─── Settings ─────────────────────────────────────────────────────────────────

class SettingCreateView(CreateView):
    model = Setting
    template_name = 'ngs/setting_form.html'
    fields = ['script', 'settings_json']
    success_url = reverse_lazy('ngs:pipeline-list')


class SettingUpdateView(UpdateView):
    model = Setting
    template_name = 'ngs/setting_form.html'
    fields = ['script', 'settings_json']
    success_url = reverse_lazy('ngs:pipeline-list')


class SettingDeleteView(DeleteView):
    model = Setting
    template_name = 'ngs/setting_confirm_delete.html'
    success_url = reverse_lazy('ngs:pipeline-list')


# ─── Counts ───────────────────────────────────────────────────────────────────

class CountCreateView(CreateView):
    model = Count
    template_name = 'ngs/count_form.html'
    fields = ['pipeline', 'counts_file']
    success_url = reverse_lazy('ngs:pipeline-list')


class CountUpdateView(UpdateView):
    model = Count
    template_name = 'ngs/count_form.html'
    fields = ['pipeline', 'counts_file']
    success_url = reverse_lazy('ngs:pipeline-list')


class CountDeleteView(DeleteView):
    model = Count
    template_name = 'ngs/count_confirm_delete.html'
    success_url = reverse_lazy('ngs:pipeline-list')


# ─── Analysis ─────────────────────────────────────────────────────────────────

class AnalysisCreateView(CreateView):
    model = Analysis
    template_name = 'ngs/analysis_form.html'
    fields = ['pipeline', 'trimming_table_file', 'logo_plot_file']
    success_url = reverse_lazy('ngs:pipeline-list')


class AnalysisUpdateView(UpdateView):
    model = Analysis
    template_name = 'ngs/analysis_form.html'
    fields = ['pipeline', 'trimming_table_file', 'logo_plot_file']
    success_url = reverse_lazy('ngs:pipeline-list')


class AnalysisDeleteView(DeleteView):
    model = Analysis
    template_name = 'ngs/analysis_confirm_delete.html'
    success_url = reverse_lazy('ngs:pipeline-list')
