import logging
from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.template.response import TemplateResponse
from django.contrib import messages

from .models import (
    Sample, Protocol, Primer, NgsSample, SequencingBatch, SequencingBatchFile,
    SequencingProduct, Fastq, FastqFile, ChunkedUpload, ManualRun, Script, ScriptParameter,
    Setting, Count, Analysis,
    PipelineTemplate, PipelineStep, PipelineRun, StepRun, StepArtifact,
)

logger = logging.getLogger(__name__)


# ─── Import CSV ───────────────────────────────────────────────────────────────

def _read_csv(file_obj):
    import csv, io
    content = file_obj.read()
    if isinstance(content, bytes):
        content = content.decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(content)))

def _parse_int(v):
    v = str(v).strip()
    return int(v) if v else None

def _parse_float(v):
    v = str(v).strip()
    return float(v) if v else None

def _parse_bool(v):
    return str(v).strip().lower() in ("true", "1", "yes", "oui")


def import_samples(f):
    created, skipped, errors = 0, 0, []
    for i, row in enumerate(_read_csv(f), 2):
        name = row.get("name", "").strip()
        project_name = row.get("project_name", "").strip()
        if not name:
            errors.append(f"Row {i}: 'name' is required.")
            skipped += 1; continue
        _, was_created = Sample.objects.get_or_create(
            name=name, project_name=project_name,
            defaults={
                "sample_type":          row.get("sample_type", "").strip(),
                "sample_type_other":    row.get("sample_type_other", "").strip(),
                "plasmid_number":       _parse_int(row.get("plasmid_number", "")),
                "production_number":    _parse_int(row.get("production_number", "")),
                "biological_model":     row.get("biological_model", "").strip(),
                "organ":                row.get("organ", "").strip(),
                "organ_other":          row.get("organ_other", "").strip(),
                "serotype":             row.get("serotype", "").strip(),
                "serotype_other":       row.get("serotype_other", "").strip(),
                "condition":            row.get("condition", "").strip(),
                "injection_type":       row.get("injection_type", "").strip(),
                "injection_type_other": row.get("injection_type_other", "").strip(),
                "description":          row.get("description", "").strip(),
            },
        )
        created += 1 if was_created else 0
        skipped += 0 if was_created else 1
    return {"created": created, "skipped": skipped, "errors": errors}


def import_primers(f):
    created, skipped, errors = 0, 0, []
    for i, row in enumerate(_read_csv(f), 2):
        name = row.get("name", "").strip()
        if not name:
            errors.append(f"Row {i}: 'name' is required."); skipped += 1; continue
        _, was_created = Primer.objects.get_or_create(name=name)
        created += 1 if was_created else 0
        skipped += 0 if was_created else 1
    return {"created": created, "skipped": skipped, "errors": errors}


def import_protocols(f):
    # Protocol <-> Sample is many-to-many: a row adds `sample_name` to the
    # protocol identified by its (primer_1, primer_2) pair, creating that
    # protocol (and any missing Primer) on first use. Repeat the same primer
    # pair on several rows (different sample_name) to associate multiple
    # samples with one protocol.
    created, skipped, errors = 0, 0, []
    for i, row in enumerate(_read_csv(f), 2):
        sample_name = row.get("sample_name", "").strip()
        if not sample_name:
            errors.append(f"Row {i}: 'sample_name' is required."); skipped += 1; continue
        try:
            sample = Sample.objects.get(name=sample_name)
        except Sample.DoesNotExist:
            errors.append(f"Row {i}: Sample '{sample_name}' not found."); skipped += 1; continue
        except Sample.MultipleObjectsReturned:
            errors.append(f"Row {i}: Multiple samples named '{sample_name}'."); skipped += 1; continue

        primer_1_name = row.get("primer_1", "").strip()
        primer_2_name = row.get("primer_2", "").strip()
        primer_1 = Primer.objects.get_or_create(name=primer_1_name)[0] if primer_1_name else None
        primer_2 = Primer.objects.get_or_create(name=primer_2_name)[0] if primer_2_name else None

        protocol, was_created = Protocol.objects.get_or_create(
            primer_1=primer_1, primer_2=primer_2,
            defaults={
                "name": row.get("name", "").strip(),
                "commentary": row.get("commentary", "").strip(),
            },
        )
        protocol.samples.add(sample)
        created += 1 if was_created else 0
        skipped += 0 if was_created else 1
    return {"created": created, "skipped": skipped, "errors": errors}


def import_ngs_samples(f):
    # One row = one NGS sample for one (protocol, sample) pair. `sample` is
    # unique on NgsSample (a sample is sequenced-prepped at most once), so
    # re-importing the same protocol_sample_name updates it instead of
    # erroring.
    created, skipped, errors = 0, 0, []
    for i, row in enumerate(_read_csv(f), 2):
        primer_1_name = row.get("protocol_primer_1", "").strip()
        primer_2_name = row.get("protocol_primer_2", "").strip()
        sample_name = row.get("protocol_sample_name", "").strip()
        if not sample_name or (not primer_1_name and not primer_2_name):
            errors.append(
                f"Row {i}: 'protocol_sample_name' and at least one of "
                "'protocol_primer_1'/'protocol_primer_2' are required."
            )
            skipped += 1; continue
        qs = Protocol.objects.filter(samples__name=sample_name)
        if primer_1_name:
            qs = qs.filter(primer_1__name=primer_1_name)
        if primer_2_name:
            qs = qs.filter(primer_2__name=primer_2_name)
        try:
            protocol = qs.get()
        except Protocol.DoesNotExist:
            errors.append(f"Row {i}: Protocol '{primer_1_name}/{primer_2_name}' / '{sample_name}' not found.")
            skipped += 1; continue
        except Protocol.MultipleObjectsReturned:
            errors.append(f"Row {i}: Multiple matching protocols."); skipped += 1; continue
        sample = protocol.samples.get(name=sample_name)
        operating_name = row.get("operating_name", "").strip() or sample_name
        _, was_created = NgsSample.objects.get_or_create(
            sample=sample,
            defaults={
                "protocol": protocol,
                "operating_name": operating_name,
                "index_1": row.get("index_1", "").strip(),
                "index_2": row.get("index_2", "").strip(),
                "final_concentration": _parse_float(row.get("final_concentration", "")),
            },
        )
        created += 1 if was_created else 0
        skipped += 0 if was_created else 1
    return {"created": created, "skipped": skipped, "errors": errors}


def import_sequencing_batches(f):
    # A batch pools several NGS samples together (one-to-many): rows sharing
    # the same 'batch_key' are added to the same new SequencingBatch. Only
    # NGS samples with a non-empty index_1 can be pooled into a batch.
    created, skipped, errors = 0, 0, []
    batches_by_key = {}
    for i, row in enumerate(_read_csv(f), 2):
        index_1      = row.get("ngs_sample_index_1", "").strip()
        primer_1_name = row.get("ngs_sample_protocol_primer_1", "").strip()
        primer_2_name = row.get("ngs_sample_protocol_primer_2", "").strip()
        batch_key   = row.get("batch_key", "").strip() or f"__row_{i}"
        if not index_1:
            errors.append(f"Row {i}: 'ngs_sample_index_1' is required."); skipped += 1; continue
        qs = NgsSample.objects.exclude(index_1="").filter(index_1=index_1)
        if primer_1_name:
            qs = qs.filter(protocol__primer_1__name=primer_1_name)
        if primer_2_name:
            qs = qs.filter(protocol__primer_2__name=primer_2_name)
        try:
            ngs_sample = qs.get()
        except NgsSample.DoesNotExist:
            errors.append(f"Row {i}: NGS Sample with index_1='{index_1}' not found."); skipped += 1; continue
        except NgsSample.MultipleObjectsReturned:
            errors.append(f"Row {i}: Ambiguous index_1='{index_1}' — specify ngs_sample_protocol_primer_1/2."); skipped += 1; continue
        batch = batches_by_key.get(batch_key)
        if batch is None:
            batch = SequencingBatch.objects.create()
            batches_by_key[batch_key] = batch
        ngs_sample.sequencing_batch = batch
        ngs_sample.save(update_fields=["sequencing_batch"])
        created += 1
    return {"created": created, "skipped": skipped, "errors": errors}


def import_sequencing_batch_files(f):
    created, skipped, errors = 0, 0, []
    for i, row in enumerate(_read_csv(f), 2):
        batch_id = _parse_int(row.get("sequencing_batch_id", ""))
        if not batch_id:
            errors.append(f"Row {i}: 'sequencing_batch_id' is required."); skipped += 1; continue
        try:
            batch = SequencingBatch.objects.get(pk=batch_id)
        except SequencingBatch.DoesNotExist:
            errors.append(f"Row {i}: SequencingBatch id={batch_id} not found."); skipped += 1; continue
        SequencingBatchFile.objects.create(sequencing_batch=batch)
        created += 1
    return {"created": created, "skipped": skipped, "errors": errors}


def import_sequencing_products(f):
    created, skipped, errors = 0, 0, []
    for i, row in enumerate(_read_csv(f), 2):
        batch_id = _parse_int(row.get("sequencing_batch_id", ""))
        if not batch_id:
            errors.append(f"Row {i}: 'sequencing_batch_id' is required."); skipped += 1; continue
        try:
            batch = SequencingBatch.objects.get(pk=batch_id)
        except SequencingBatch.DoesNotExist:
            errors.append(f"Row {i}: SequencingBatch id={batch_id} not found."); skipped += 1; continue
        SequencingProduct.objects.create(
            sequencing_batch=batch,
            date=row.get("date", "").strip(),
            sequencing_machine=row.get("sequencing_machine", "").strip(),
            flowcell=row.get("flowcell", "").strip(),
            read_length=_parse_int(row.get("read_length", "")),
            read_depth=_parse_int(row.get("read_depth", "")),
            phix_proportion=_parse_float(row.get("phix_proportion", "")),
            custom_recipe=_parse_bool(row.get("custom_recipe", "false")),
            custom_recipe_start=_parse_int(row.get("custom_recipe_start", "")),
            custom_recipe_end=_parse_int(row.get("custom_recipe_end", "")),
        )
        created += 1
    return {"created": created, "skipped": skipped, "errors": errors}


def import_fastq(f):
    created, skipped, errors = 0, 0, []
    for i, row in enumerate(_read_csv(f), 2):
        product_id = _parse_int(row.get("sequencing_product_id", ""))
        if not product_id:
            errors.append(f"Row {i}: 'sequencing_product_id' is required."); skipped += 1; continue
        try:
            product = SequencingProduct.objects.get(pk=product_id)
        except SequencingProduct.DoesNotExist:
            errors.append(f"Row {i}: SequencingProduct id={product_id} not found."); skipped += 1; continue
        ngs_sample = None
        ngs_sample_id = _parse_int(row.get("ngs_sample_id", ""))
        if ngs_sample_id:
            try:
                ngs_sample = NgsSample.objects.get(pk=ngs_sample_id)
            except NgsSample.DoesNotExist:
                errors.append(f"Row {i}: NgsSample id={ngs_sample_id} not found."); skipped += 1; continue
        Fastq.objects.create(sequencing_product=product, ngs_sample=ngs_sample)
        created += 1
    return {"created": created, "skipped": skipped, "errors": errors}


def import_script_parameters(f):
    created, skipped, errors = 0, 0, []
    for i, row in enumerate(_read_csv(f), 2):
        script_id = _parse_int(row.get("script_id", ""))
        name = row.get("name", "").strip()
        if not script_id or not name:
            errors.append(f"Row {i}: 'script_id' and 'name' are required."); skipped += 1; continue
        try:
            script = Script.objects.get(pk=script_id)
        except Script.DoesNotExist:
            errors.append(f"Row {i}: Script id={script_id} not found."); skipped += 1; continue
        ScriptParameter.objects.create(
            script=script, name=name, description=row.get("description", "").strip(),
        )
        created += 1
    return {"created": created, "skipped": skipped, "errors": errors}


def _import_simple(f, model_class, fk_field, fk_model, fk_col):
    created, skipped, errors = 0, 0, []
    for i, row in enumerate(_read_csv(f), 2):
        fk_id = _parse_int(row.get(fk_col, ""))
        if not fk_id:
            errors.append(f"Row {i}: '{fk_col}' is required."); skipped += 1; continue
        try:
            fk_obj = fk_model.objects.get(pk=fk_id)
        except fk_model.DoesNotExist:
            errors.append(f"Row {i}: {fk_model.__name__} id={fk_id} not found."); skipped += 1; continue
        model_class.objects.create(**{fk_field: fk_obj})
        created += 1
    return {"created": created, "skipped": skipped, "errors": errors}


IMPORTERS = {
    "samples":                import_samples,
    "primers":                import_primers,
    "protocols":              import_protocols,
    "ngs_samples":            import_ngs_samples,
    "sequencing_batches":     import_sequencing_batches,
    "sequencing_batch_files": import_sequencing_batch_files,
    "sequencing_products":    import_sequencing_products,
    "fastq":              import_fastq,
    "fastq_files":  lambda f: _import_simple(f, FastqFile,    "fastq",              Fastq,             "fastq_id"),
    "manual_runs":  lambda f: _import_simple(f, ManualRun,    "sequencing_product", SequencingProduct, "sequencing_product_id"),
    "scripts":      lambda f: _import_simple(f, Script,       "manual_run",         ManualRun,         "manual_run_id"),
    "script_parameters":  import_script_parameters,
    "settings":     lambda f: _import_simple(f, Setting,      "script",             Script,            "script_id"),
    "counts":       lambda f: _import_simple(f, Count,        "manual_run",         ManualRun,         "manual_run_id"),
    "analysis":     lambda f: _import_simple(f, Analysis,     "manual_run",         ManualRun,         "manual_run_id"),
}


# ─── Mixin CSV ────────────────────────────────────────────────────────────────

class CsvImportMixin:
    importer_key = None

    def get_urls(self):
        urls = super().get_urls()
        return [
            path(
                "import-csv/",
                self.admin_site.admin_view(self.import_csv_view),
                name=f"{self.model._meta.app_label}_{self.model._meta.model_name}_import_csv",
            ),
        ] + urls

    def import_csv_view(self, request):
        model_name    = self.model._meta.verbose_name_plural
        changelist_url = reverse(
            f"admin:{self.model._meta.app_label}_{self.model._meta.model_name}_changelist"
        )
        if request.method == "POST":
            csv_file = request.FILES.get("csv_file")
            if not csv_file:
                messages.error(request, "No file selected.")
            elif not csv_file.name.endswith(".csv"):
                messages.error(request, "The file must be in .csv format.")
            else:
                importer = IMPORTERS.get(self.importer_key)
                try:
                    result = importer(csv_file)
                    for err in result["errors"]:
                        messages.warning(request, err)
                    messages.success(
                        request,
                        f"{result['created']} row(s) created, {result['skipped']} skipped."
                    )
                except Exception as e:
                    messages.error(request, f"Import error: {e}")

        context = {
            **self.admin_site.each_context(request),
            "title":          f"Import CSV — {model_name}",
            "opts":           self.model._meta,
            "changelist_url": changelist_url,
            "model_name":     model_name,
        }
        return TemplateResponse(request, "admin/api/csv_import.html", context)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["import_csv_url"] = reverse(
            f"admin:{self.model._meta.app_label}_{self.model._meta.model_name}_import_csv"
        )
        return super().changelist_view(request, extra_context=extra_context)


# ─── ModelAdmins ──────────────────────────────────────────────────────────────

@admin.register(Sample)
class SampleAdmin(CsvImportMixin, admin.ModelAdmin):
    importer_key  = "samples"
    list_display  = ('name', 'project_name', 'sample_type', 'organ', 'serotype', 'created_at')
    list_filter   = ('sample_type', 'project_name')
    search_fields = ('name', 'project_name', 'biological_model', 'organ')


@admin.register(Primer)
class PrimerAdmin(CsvImportMixin, admin.ModelAdmin):
    importer_key  = "primers"
    list_display  = ('id', 'name')
    search_fields = ('name',)


@admin.register(Protocol)
class ProtocolAdmin(CsvImportMixin, admin.ModelAdmin):
    importer_key    = "protocols"
    list_display    = ('id', 'name', 'primer_1', 'primer_2', 'sample_list', 'created_at')
    list_filter     = ('created_at',)
    search_fields   = ('name', 'primer_1__name', 'primer_2__name', 'commentary')
    filter_horizontal = ('samples',)

    def sample_list(self, obj):
        return ", ".join(s.name for s in obj.samples.all())
    sample_list.short_description = "Samples"


@admin.register(NgsSample)
class NgsSampleAdmin(CsvImportMixin, admin.ModelAdmin):
    importer_key  = "ngs_samples"
    list_display  = ('id', 'operating_name', 'sample', 'index_1', 'index_2', 'final_concentration', 'protocol', 'sequencing_batch')
    search_fields = ('operating_name', 'index_1', 'index_2')
    raw_id_fields = ('protocol', 'sample', 'sequencing_batch')


class NgsSampleInline(admin.TabularInline):
    model = NgsSample
    fk_name = 'sequencing_batch'
    extra = 0
    fields = ('operating_name', 'index_1', 'index_2', 'final_concentration')
    show_change_link = True


class SequencingBatchFileInline(admin.TabularInline):
    model = SequencingBatchFile
    extra = 1


class SequencingProductInline(admin.TabularInline):
    model = SequencingProduct
    extra = 0
    fields = ('date', 'sequencing_machine', 'flowcell', 'read_length', 'read_depth')


@admin.register(SequencingBatch)
class SequencingBatchAdmin(CsvImportMixin, admin.ModelAdmin):
    importer_key  = "sequencing_batches"
    list_display  = ('id', 'ngs_sample_count', 'created_at')
    inlines       = [NgsSampleInline, SequencingBatchFileInline, SequencingProductInline]

    def ngs_sample_count(self, obj):
        return obj.ngs_samples.count()
    ngs_sample_count.short_description = "NGS samples"


@admin.register(SequencingBatchFile)
class SequencingBatchFileAdmin(CsvImportMixin, admin.ModelAdmin):
    importer_key  = "sequencing_batch_files"
    list_display  = ('id', 'sequencing_batch')
    raw_id_fields = ('sequencing_batch',)


class FastqInline(admin.TabularInline):
    model = Fastq
    extra = 0


class ManualRunInline(admin.StackedInline):
    model = ManualRun
    extra = 0


@admin.register(SequencingProduct)
class SequencingProductAdmin(CsvImportMixin, admin.ModelAdmin):
    importer_key  = "sequencing_products"
    list_display  = ('id', 'date', 'sequencing_machine', 'flowcell', 'read_length', 'read_depth', 'custom_recipe')
    list_filter   = ('sequencing_machine', 'custom_recipe')
    inlines       = [FastqInline, ManualRunInline]
    raw_id_fields = ('sequencing_batch',)


class FastqFileInline(admin.TabularInline):
    model = FastqFile
    extra = 1


@admin.register(Fastq)
class FastqAdmin(CsvImportMixin, admin.ModelAdmin):
    importer_key  = "fastq"
    list_display  = ('id', 'sequencing_product', 'ngs_sample')
    inlines       = [FastqFileInline]
    raw_id_fields = ('sequencing_product', 'ngs_sample')


@admin.register(FastqFile)
class FastqFileAdmin(CsvImportMixin, admin.ModelAdmin):
    importer_key  = "fastq_files"
    list_display  = ('id', 'fastq', 'comment')
    raw_id_fields = ('fastq',)


@admin.register(ChunkedUpload)
class ChunkedUploadAdmin(admin.ModelAdmin):
    list_display    = ('filename', 'fastq', 'progress', 'completed', 'uploaded_by', 'updated_at')
    list_filter     = ('completed',)
    raw_id_fields   = ('fastq',)
    readonly_fields = ('id', 'fastq', 'filename', 'comment', 'total_size', 'offset', 'completed', 'uploaded_by', 'created_at', 'updated_at')

    def progress(self, obj):
        if not obj.total_size:
            return "—"
        return f"{obj.offset / obj.total_size:.0%}"

    def has_add_permission(self, request):
        return False


class ScriptInline(admin.TabularInline):
    model = Script
    extra = 0


class CountInline(admin.TabularInline):
    model = Count
    extra = 0


class AnalysisInline(admin.TabularInline):
    model = Analysis
    extra = 0


@admin.register(ManualRun)
class ManualRunAdmin(CsvImportMixin, admin.ModelAdmin):
    importer_key  = "manual_runs"
    list_display  = ('id', 'sequencing_product')
    inlines       = [ScriptInline, CountInline, AnalysisInline]
    raw_id_fields = ('sequencing_product',)


class SettingInline(admin.TabularInline):
    model = Setting
    extra = 0


class ScriptParameterInline(admin.TabularInline):
    model = ScriptParameter
    extra = 1


@admin.register(Script)
class ScriptAdmin(CsvImportMixin, admin.ModelAdmin):
    importer_key  = "scripts"
    list_display  = ('id', 'name', 'language', 'version', 'manual_run', 'created_at')
    list_filter   = ('language',)
    search_fields = ('name', 'comment')
    inlines       = [ScriptParameterInline, SettingInline]
    raw_id_fields = ('manual_run',)


@admin.register(ScriptParameter)
class ScriptParameterAdmin(CsvImportMixin, admin.ModelAdmin):
    importer_key  = "script_parameters"
    list_display  = ('id', 'script', 'name', 'description')
    raw_id_fields = ('script',)


@admin.register(Setting)
class SettingAdmin(CsvImportMixin, admin.ModelAdmin):
    importer_key  = "settings"
    list_display  = ('id', 'script')
    raw_id_fields = ('script',)


@admin.register(Count)
class CountAdmin(CsvImportMixin, admin.ModelAdmin):
    importer_key  = "counts"
    list_display  = ('id', 'manual_run')
    raw_id_fields = ('manual_run',)


@admin.register(Analysis)
class AnalysisAdmin(CsvImportMixin, admin.ModelAdmin):
    importer_key  = "analysis"
    list_display  = ('id', 'manual_run')
    raw_id_fields = ('manual_run',)


# ─── Pipeline execution engine (DAG of steps in containers) ─────────────────

class PipelineStepInline(admin.StackedInline):
    model = PipelineStep
    extra = 1
    filter_horizontal = ('depends_on',)
    fields = ('name', 'language', 'docker_image', 'script', 'command', 'depends_on', 'timeout_seconds')
    autocomplete_fields = ('script',)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == 'depends_on':
            object_id = request.resolver_match.kwargs.get('object_id')
            if object_id:
                kwargs['queryset'] = PipelineStep.objects.filter(template_id=object_id)
            else:
                kwargs['queryset'] = PipelineStep.objects.none()
        return super().formfield_for_manytomany(db_field, request, **kwargs)


@admin.register(PipelineTemplate)
class PipelineTemplateAdmin(admin.ModelAdmin):
    list_display  = ('name', 'description', 'created_at', 'step_count')
    search_fields = ('name', 'description')
    inlines       = [PipelineStepInline]

    def step_count(self, obj):
        return obj.steps.count()
    step_count.short_description = "Steps"


class StepArtifactInline(admin.TabularInline):
    model = StepArtifact
    extra = 0
    readonly_fields = ('kind', 'label', 'file')
    can_delete = False


@admin.register(StepRun)
class StepRunAdmin(admin.ModelAdmin):
    list_display    = ('id', 'pipeline_run', 'step', 'status', 'started_at', 'finished_at', 'exit_code')
    list_filter     = ('status', 'step__template')
    readonly_fields = ('pipeline_run', 'step', 'status', 'celery_task_id', 'exit_code', 'log', 'started_at', 'finished_at')
    inlines         = [StepArtifactInline]

    def has_add_permission(self, request):
        return False


class StepRunInline(admin.TabularInline):
    model = StepRun
    extra = 0
    fields = ('step', 'status', 'exit_code', 'started_at', 'finished_at')
    readonly_fields = fields
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(PipelineRun)
class PipelineRunAdmin(admin.ModelAdmin):
    list_display    = ('id', 'template', 'fastq', 'status', 'launched_by', 'created_at', 'finished_at')
    list_filter     = ('status', 'template')
    raw_id_fields   = ('fastq',)
    readonly_fields = ('template', 'fastq', 'status', 'launched_by', 'created_at', 'started_at', 'finished_at')
    inlines         = [StepRunInline]

    def has_add_permission(self, request):
        return False