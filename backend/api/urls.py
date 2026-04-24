from django.urls import path
from . import views

app_name = 'ngs'

urlpatterns = [
    # Samples
    path('samples/', views.SampleListView.as_view(), name='sample-list'),
    path('samples/<int:pk>/', views.SampleDetailView.as_view(), name='sample-detail'),
    path('samples/new/', views.SampleCreateView.as_view(), name='sample-create'),
    path('samples/<int:pk>/edit/', views.SampleUpdateView.as_view(), name='sample-update'),
    path('samples/<int:pk>/delete/', views.SampleDeleteView.as_view(), name='sample-delete'),

    # Protocols
    path('protocols/', views.ProtocolListView.as_view(), name='protocol-list'),
    path('protocols/<int:pk>/', views.ProtocolDetailView.as_view(), name='protocol-detail'),
    path('protocols/new/', views.ProtocolCreateView.as_view(), name='protocol-create'),
    path('protocols/<int:pk>/edit/', views.ProtocolUpdateView.as_view(), name='protocol-update'),
    path('protocols/<int:pk>/delete/', views.ProtocolDeleteView.as_view(), name='protocol-delete'),

    # NGS Samples
    path('ngs-samples/', views.NgsSampleListView.as_view(), name='ngssample-list'),
    path('ngs-samples/<int:pk>/', views.NgsSampleDetailView.as_view(), name='ngssample-detail'),
    path('ngs-samples/new/', views.NgsSampleCreateView.as_view(), name='ngssample-create'),
    path('ngs-samples/<int:pk>/edit/', views.NgsSampleUpdateView.as_view(), name='ngssample-update'),
    path('ngs-samples/<int:pk>/delete/', views.NgsSampleDeleteView.as_view(), name='ngssample-delete'),

    # Sequencing Batches
    path('batches/', views.SequencingBatchListView.as_view(), name='sequencingbatch-list'),
    path('batches/<int:pk>/', views.SequencingBatchDetailView.as_view(), name='sequencingbatch-detail'),
    path('batches/new/', views.SequencingBatchCreateView.as_view(), name='sequencingbatch-create'),
    path('batches/<int:pk>/edit/', views.SequencingBatchUpdateView.as_view(), name='sequencingbatch-update'),
    path('batches/<int:pk>/delete/', views.SequencingBatchDeleteView.as_view(), name='sequencingbatch-delete'),

    # Sequencing Batch Files
    path('batch-files/new/', views.SequencingBatchFileCreateView.as_view(), name='batchfile-create'),
    path('batch-files/<int:pk>/edit/', views.SequencingBatchFileUpdateView.as_view(), name='batchfile-update'),
    path('batch-files/<int:pk>/delete/', views.SequencingBatchFileDeleteView.as_view(), name='batchfile-delete'),

    # Sequencing Products
    path('products/', views.SequencingProductListView.as_view(), name='sequencingproduct-list'),
    path('products/<int:pk>/', views.SequencingProductDetailView.as_view(), name='sequencingproduct-detail'),
    path('products/new/', views.SequencingProductCreateView.as_view(), name='sequencingproduct-create'),
    path('products/<int:pk>/edit/', views.SequencingProductUpdateView.as_view(), name='sequencingproduct-update'),
    path('products/<int:pk>/delete/', views.SequencingProductDeleteView.as_view(), name='sequencingproduct-delete'),

    # FASTQ
    path('fastq/<int:pk>/', views.FastqDetailView.as_view(), name='fastq-detail'),
    path('fastq/new/', views.FastqCreateView.as_view(), name='fastq-create'),
    path('fastq/<int:pk>/delete/', views.FastqDeleteView.as_view(), name='fastq-delete'),

    # FASTQ Files
    path('fastq-files/new/', views.FastqFileCreateView.as_view(), name='fastqfile-create'),
    path('fastq-files/<int:pk>/delete/', views.FastqFileDeleteView.as_view(), name='fastqfile-delete'),

    # Pipelines
    path('pipelines/', views.PipelineListView.as_view(), name='pipeline-list'),
    path('pipelines/<int:pk>/', views.PipelineDetailView.as_view(), name='pipeline-detail'),
    path('pipelines/new/', views.PipelineCreateView.as_view(), name='pipeline-create'),
    path('pipelines/<int:pk>/delete/', views.PipelineDeleteView.as_view(), name='pipeline-delete'),

    # Scripts
    path('scripts/new/', views.ScriptCreateView.as_view(), name='script-create'),
    path('scripts/<int:pk>/edit/', views.ScriptUpdateView.as_view(), name='script-update'),
    path('scripts/<int:pk>/delete/', views.ScriptDeleteView.as_view(), name='script-delete'),

    # Settings
    path('settings/new/', views.SettingCreateView.as_view(), name='setting-create'),
    path('settings/<int:pk>/edit/', views.SettingUpdateView.as_view(), name='setting-update'),
    path('settings/<int:pk>/delete/', views.SettingDeleteView.as_view(), name='setting-delete'),

    # Counts
    path('counts/new/', views.CountCreateView.as_view(), name='count-create'),
    path('counts/<int:pk>/edit/', views.CountUpdateView.as_view(), name='count-update'),
    path('counts/<int:pk>/delete/', views.CountDeleteView.as_view(), name='count-delete'),

    # Analysis
    path('analysis/new/', views.AnalysisCreateView.as_view(), name='analysis-create'),
    path('analysis/<int:pk>/edit/', views.AnalysisUpdateView.as_view(), name='analysis-update'),
    path('analysis/<int:pk>/delete/', views.AnalysisDeleteView.as_view(), name='analysis-delete'),
]
