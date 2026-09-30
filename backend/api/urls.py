from django.urls import path
from django.contrib.auth.decorators import login_required
from . import views

app_name = 'ngs'


def _v(view_class):
    """All views in the NGS module require an authenticated session."""
    return login_required(view_class.as_view())


urlpatterns = [
    # Samples
    path('samples/', _v(views.SampleListView), name='sample-list'),
    path('samples/<int:pk>/', _v(views.SampleDetailView), name='sample-detail'),
    path('samples/new/', _v(views.SampleCreateView), name='sample-create'),
    path('samples/<int:pk>/edit/', _v(views.SampleUpdateView), name='sample-update'),
    path('samples/<int:pk>/delete/', _v(views.SampleDeleteView), name='sample-delete'),

    # Protocols
    path('protocols/', _v(views.ProtocolListView), name='protocol-list'),
    path('protocols/<int:pk>/', _v(views.ProtocolDetailView), name='protocol-detail'),
    path('protocols/new/', _v(views.ProtocolCreateView), name='protocol-create'),
    path('protocols/<int:pk>/edit/', _v(views.ProtocolUpdateView), name='protocol-update'),
    path('protocols/<int:pk>/delete/', _v(views.ProtocolDeleteView), name='protocol-delete'),
    path('primers/quick-create/', login_required(views.primer_quick_create), name='primer-quick-create'),

    # NGS Samples
    path('ngs-samples/', _v(views.NgsSampleListView), name='ngssample-list'),
    path('ngs-samples/<int:pk>/', _v(views.NgsSampleDetailView), name='ngssample-detail'),
    path('ngs-samples/new/', login_required(views.ngssample_bulk_view), name='ngssample-create'),
    path('ngs-samples/<int:pk>/edit/', _v(views.NgsSampleUpdateView), name='ngssample-update'),
    path('ngs-samples/<int:pk>/delete/', _v(views.NgsSampleDeleteView), name='ngssample-delete'),

    # Sequencing Batches
    path('batches/', _v(views.SequencingBatchListView), name='sequencingbatch-list'),
    path('batches/<int:pk>/', _v(views.SequencingBatchDetailView), name='sequencingbatch-detail'),
    path('batches/new/', login_required(views.sequencingbatch_form_view), name='sequencingbatch-create'),
    path('batches/<int:pk>/edit/', login_required(views.sequencingbatch_form_view), name='sequencingbatch-update'),
    path('batches/<int:pk>/delete/', _v(views.SequencingBatchDeleteView), name='sequencingbatch-delete'),

    # Sequencing Batch Files
    path('batch-files/new/', _v(views.SequencingBatchFileCreateView), name='batchfile-create'),
    path('batch-files/<int:pk>/edit/', _v(views.SequencingBatchFileUpdateView), name='batchfile-update'),
    path('batch-files/<int:pk>/delete/', _v(views.SequencingBatchFileDeleteView), name='batchfile-delete'),

    # Sequencing Products
    path('products/', _v(views.SequencingProductListView), name='sequencingproduct-list'),
    path('products/<int:pk>/', _v(views.SequencingProductDetailView), name='sequencingproduct-detail'),
    path('products/new/', _v(views.SequencingProductCreateView), name='sequencingproduct-create'),
    path('products/<int:pk>/edit/', _v(views.SequencingProductUpdateView), name='sequencingproduct-update'),
    path('products/<int:pk>/delete/', _v(views.SequencingProductDeleteView), name='sequencingproduct-delete'),

    # FASTQ
    path('fastq/<int:pk>/', _v(views.FastqDetailView), name='fastq-detail'),
    path('fastq/new/', _v(views.FastqCreateView), name='fastq-create'),
    path('fastq/<int:pk>/delete/', _v(views.FastqDeleteView), name='fastq-delete'),

    # FASTQ Files
    path('fastq-files/new/', login_required(views.fastqfile_upload_view), name='fastqfile-create'),
    path('fastq-files/<int:pk>/delete/', _v(views.FastqFileDeleteView), name='fastqfile-delete'),
    path('products/<int:pk>/ngs-samples/', login_required(views.sequencingproduct_ngs_samples), name='sequencingproduct-ngssamples'),
    path('uploads/init/', login_required(views.chunked_upload_init), name='chunkedupload-init'),
    path('uploads/<uuid:upload_id>/status/', login_required(views.chunked_upload_status), name='chunkedupload-status'),
    path('uploads/<uuid:upload_id>/chunk/', login_required(views.chunked_upload_chunk), name='chunkedupload-chunk'),

    # Manual runs (formerly "Pipeline")
    path('manual-runs/', _v(views.ManualRunListView), name='manualrun-list'),
    path('manual-runs/<int:pk>/', _v(views.ManualRunDetailView), name='manualrun-detail'),
    path('manual-runs/new/', _v(views.ManualRunCreateView), name='manualrun-create'),
    path('manual-runs/<int:pk>/edit/', _v(views.ManualRunUpdateView), name='manualrun-update'),
    path('manual-runs/<int:pk>/delete/', _v(views.ManualRunDeleteView), name='manualrun-delete'),

    # Scripts (standalone registry, independent of any pipeline or manual run)
    path('scripts/', _v(views.ScriptListView), name='script-list'),
    path('scripts/<int:pk>/', _v(views.ScriptDetailView), name='script-detail'),
    path('scripts/new/', login_required(views.script_form_view), name='script-create'),
    path('scripts/<int:pk>/edit/', login_required(views.script_form_view), name='script-update'),
    path('scripts/<int:pk>/delete/', _v(views.ScriptDeleteView), name='script-delete'),

    # Settings
    path('settings/new/', _v(views.SettingCreateView), name='setting-create'),
    path('settings/<int:pk>/edit/', _v(views.SettingUpdateView), name='setting-update'),
    path('settings/<int:pk>/delete/', _v(views.SettingDeleteView), name='setting-delete'),

    # Counts
    path('counts/new/', _v(views.CountCreateView), name='count-create'),
    path('counts/<int:pk>/edit/', _v(views.CountUpdateView), name='count-update'),
    path('counts/<int:pk>/delete/', _v(views.CountDeleteView), name='count-delete'),

    # Analysis
    path('analysis/new/', _v(views.AnalysisCreateView), name='analysis-create'),
    path('analysis/<int:pk>/edit/', _v(views.AnalysisUpdateView), name='analysis-update'),
    path('analysis/<int:pk>/delete/', _v(views.AnalysisDeleteView), name='analysis-delete'),

    # Pipeline engine (DAG templates + runs)
    path('pipeline-templates/', _v(views.PipelineTemplateListView), name='pipelinetemplate-list'),
    path('pipeline-templates/<int:pk>/', _v(views.PipelineTemplateDetailView), name='pipelinetemplate-detail'),
    path('pipeline-templates/new/builder/', login_required(views.pipeline_builder_view), name='pipelinetemplate-builder-new'),
    path('pipeline-templates/<int:pk>/builder/', login_required(views.pipeline_builder_view), name='pipelinetemplate-builder'),
    path('pipeline-templates/new/builder/save/', login_required(views.pipeline_builder_save), name='pipelinetemplate-builder-save-new'),
    path('pipeline-templates/<int:pk>/builder/save/', login_required(views.pipeline_builder_save), name='pipelinetemplate-builder-save'),
    path('scripts/quick-create/', login_required(views.script_quick_create), name='script-quick-create'),
    path('fastq/<int:fastq_pk>/run/', login_required(views.pipeline_run_launch), name='pipelinerun-launch'),
    path('pipeline-runs/launch/', login_required(views.pipeline_run_launch), name='pipelinerun-launch-generic'),
    path('pipeline-runs/', _v(views.PipelineRunListView), name='pipelinerun-list'),
    path('pipeline-runs/<int:pk>/', _v(views.PipelineRunDetailView), name='pipelinerun-detail'),
]
