from django.contrib import admin
from .models import (
    Sample, Protocol, NgsSample, SequencingBatch, SequencingBatchFile,
    SequencingProduct, Fastq, FastqFile, Pipeline, Script, Setting, Count, Analysis
)


@admin.register(Sample)
class SampleAdmin(admin.ModelAdmin):
    list_display = ('name', 'project_name', 'sample_type', 'organ', 'serotype', 'created_at')
    list_filter = ('sample_type', 'project_name')
    search_fields = ('name', 'project_name', 'biological_model', 'organ')


@admin.register(Protocol)
class ProtocolAdmin(admin.ModelAdmin):
    list_display = ('id', 'primer_pair', 'sample', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('primer_pair', 'commentary')
    raw_id_fields = ('sample',)


@admin.register(NgsSample)
class NgsSampleAdmin(admin.ModelAdmin):
    list_display = ('id', 'index', 'final_concentration', 'protocol')
    search_fields = ('index',)
    raw_id_fields = ('protocol',)


class SequencingBatchFileInline(admin.TabularInline):
    model = SequencingBatchFile
    extra = 1


class SequencingProductInline(admin.TabularInline):
    model = SequencingProduct
    extra = 0
    fields = ('date', 'sequencing_machine', 'flowcell', 'read_length', 'read_depth')


@admin.register(SequencingBatch)
class SequencingBatchAdmin(admin.ModelAdmin):
    list_display = ('id', 'ngs_sample')
    inlines = [SequencingBatchFileInline, SequencingProductInline]
    raw_id_fields = ('ngs_sample',)


@admin.register(SequencingBatchFile)
class SequencingBatchFileAdmin(admin.ModelAdmin):
    list_display = ('id', 'sequencing_batch')
    raw_id_fields = ('sequencing_batch',)


class FastqInline(admin.TabularInline):
    model = Fastq
    extra = 0


@admin.register(SequencingProduct)
class SequencingProductAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'date', 'sequencing_machine', 'flowcell',
        'read_length', 'read_depth', 'custom_recipe',
    )
    list_filter = ('sequencing_machine', 'custom_recipe')
    inlines = [FastqInline]
    raw_id_fields = ('sequencing_batch',)


class FastqFileInline(admin.TabularInline):
    model = FastqFile
    extra = 1


class PipelineInline(admin.TabularInline):
    model = Pipeline
    extra = 0


@admin.register(Fastq)
class FastqAdmin(admin.ModelAdmin):
    list_display = ('id', 'sequencing_product')
    inlines = [FastqFileInline, PipelineInline]
    raw_id_fields = ('sequencing_product',)


@admin.register(FastqFile)
class FastqFileAdmin(admin.ModelAdmin):
    list_display = ('id', 'fastq')
    raw_id_fields = ('fastq',)


class ScriptInline(admin.TabularInline):
    model = Script
    extra = 0


class CountInline(admin.TabularInline):
    model = Count
    extra = 0


class AnalysisInline(admin.TabularInline):
    model = Analysis
    extra = 0


@admin.register(Pipeline)
class PipelineAdmin(admin.ModelAdmin):
    list_display = ('id', 'fastq')
    inlines = [ScriptInline, CountInline, AnalysisInline]
    raw_id_fields = ('fastq',)


class SettingInline(admin.TabularInline):
    model = Setting
    extra = 0


@admin.register(Script)
class ScriptAdmin(admin.ModelAdmin):
    list_display = ('id', 'pipeline')
    inlines = [SettingInline]
    raw_id_fields = ('pipeline',)


@admin.register(Setting)
class SettingAdmin(admin.ModelAdmin):
    list_display = ('id', 'script')
    raw_id_fields = ('script',)


@admin.register(Count)
class CountAdmin(admin.ModelAdmin):
    list_display = ('id', 'pipeline')
    raw_id_fields = ('pipeline',)


@admin.register(Analysis)
class AnalysisAdmin(admin.ModelAdmin):
    list_display = ('id', 'pipeline')
    raw_id_fields = ('pipeline',)
