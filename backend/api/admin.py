import logging
from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.template.response import TemplateResponse
from django.contrib import messages

from .models import (
    Sample, Protocol, NgsSample, SequencingBatch, SequencingBatchFile,
    SequencingProduct, Fastq, FastqFile, Pipeline, Script, Setting, Count, Analysis
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
        if not name or not project_name:
            errors.append(f"Ligne {i} : 'name' et 'project_name' obligatoires.")
            skipped += 1; continue
        _, was_created = Sample.objects.get_or_create(
            name=name, project_name=project_name,
            defaults={
                "sample_type":       row.get("sample_type", "").strip(),
                "plasmid_number":    _parse_int(row.get("plasmid_number", "")),
                "production_number": _parse_int(row.get("production_number", "")),
                "biological_model":  row.get("biological_model", "").strip(),
                "organ":             row.get("organ", "").strip(),
                "serotype":          row.get("serotype", "").strip(),
                "condition":         row.get("condition", "").strip(),
                "description":       row.get("description", "").strip(),
            },
        )
        created += 1 if was_created else 0
        skipped += 0 if was_created else 1
    return {"created": created, "skipped": skipped, "errors": errors}


def import_protocols(f):
    created, skipped, errors = 0, 0, []
    for i, row in enumerate(_read_csv(f), 2):
        sample_name = row.get("sample_name", "").strip()
        if not sample_name:
            errors.append(f"Ligne {i} : 'sample_name' obligatoire."); skipped += 1; continue
        try:
            sample = Sample.objects.get(name=sample_name)
        except Sample.DoesNotExist:
            errors.append(f"Ligne {i} : Sample '{sample_name}' introuvable."); skipped += 1; continue
        except Sample.MultipleObjectsReturned:
            errors.append(f"Ligne {i} : Plusieurs samples '{sample_name}'."); skipped += 1; continue
        _, was_created = Protocol.objects.get_or_create(
            sample=sample, primer_pair=row.get("primer_pair", "").strip(),
            defaults={"commentary": row.get("commentary", "").strip()},
        )
        created += 1 if was_created else 0
        skipped += 0 if was_created else 1
    return {"created": created, "skipped": skipped, "errors": errors}


def import_ngs_samples(f):
    created, skipped, errors = 0, 0, []
    for i, row in enumerate(_read_csv(f), 2):
        primer_pair = row.get("protocol_primer_pair", "").strip()
        sample_name = row.get("protocol_sample_name", "").strip()
        if not primer_pair or not sample_name:
            errors.append(f"Ligne {i} : 'protocol_primer_pair' et 'protocol_sample_name' obligatoires.")
            skipped += 1; continue
        try:
            protocol = Protocol.objects.get(primer_pair=primer_pair, sample__name=sample_name)
        except Protocol.DoesNotExist:
            errors.append(f"Ligne {i} : Protocol '{primer_pair}' / '{sample_name}' introuvable.")
            skipped += 1; continue
        except Protocol.MultipleObjectsReturned:
            errors.append(f"Ligne {i} : Plusieurs protocols correspondent."); skipped += 1; continue
        _, was_created = NgsSample.objects.get_or_create(
            protocol=protocol, index=row.get("index", "").strip(),
            defaults={"final_concentration": _parse_float(row.get("final_concentration", ""))},
        )
        created += 1 if was_created else 0
        skipped += 0 if was_created else 1
    return {"created": created, "skipped": skipped, "errors": errors}


def import_sequencing_batches(f):
    created, skipped, errors = 0, 0, []
    for i, row in enumerate(_read_csv(f), 2):
        ngs_index   = row.get("ngs_sample_index", "").strip()
        primer_pair = row.get("ngs_sample_protocol_primer_pair", "").strip()
        if not ngs_index:
            errors.append(f"Ligne {i} : 'ngs_sample_index' obligatoire."); skipped += 1; continue
        qs = NgsSample.objects.filter(index=ngs_index)
        if primer_pair:
            qs = qs.filter(protocol__primer_pair=primer_pair)
        try:
            ngs_sample = qs.get()
        except NgsSample.DoesNotExist:
            errors.append(f"Ligne {i} : NGS Sample '{ngs_index}' introuvable."); skipped += 1; continue
        except NgsSample.MultipleObjectsReturned:
            errors.append(f"Ligne {i} : Ambiguïté sur '{ngs_index}' — préciser primer_pair."); skipped += 1; continue
        SequencingBatch.objects.create(ngs_sample=ngs_sample)
        created += 1
    return {"created": created, "skipped": skipped, "errors": errors}


def import_sequencing_batch_files(f):
    created, skipped, errors = 0, 0, []
    for i, row in enumerate(_read_csv(f), 2):
        batch_id = _parse_int(row.get("sequencing_batch_id", ""))
        if not batch_id:
            errors.append(f"Ligne {i} : 'sequencing_batch_id' obligatoire."); skipped += 1; continue
        try:
            batch = SequencingBatch.objects.get(pk=batch_id)
        except SequencingBatch.DoesNotExist:
            errors.append(f"Ligne {i} : SequencingBatch id={batch_id} introuvable."); skipped += 1; continue
        SequencingBatchFile.objects.create(sequencing_batch=batch)
        created += 1
    return {"created": created, "skipped": skipped, "errors": errors}


def import_sequencing_products(f):
    created, skipped, errors = 0, 0, []
    for i, row in enumerate(_read_csv(f), 2):
        batch_id = _parse_int(row.get("sequencing_batch_id", ""))
        if not batch_id:
            errors.append(f"Ligne {i} : 'sequencing_batch_id' obligatoire."); skipped += 1; continue
        try:
            batch = SequencingBatch.objects.get(pk=batch_id)
        except SequencingBatch.DoesNotExist:
            errors.append(f"Ligne {i} : SequencingBatch id={batch_id} introuvable."); skipped += 1; continue
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


def _import_simple(f, model_class, fk_field, fk_model, fk_col):
    created, skipped, errors = 0, 0, []
    for i, row in enumerate(_read_csv(f), 2):
        fk_id = _parse_int(row.get(fk_col, ""))
        if not fk_id:
            errors.append(f"Ligne {i} : '{fk_col}' obligatoire."); skipped += 1; continue
        try:
            fk_obj = fk_model.objects.get(pk=fk_id)
        except fk_model.DoesNotExist:
            errors.append(f"Ligne {i} : {fk_model.__name__} id={fk_id} introuvable."); skipped += 1; continue
        model_class.objects.create(**{fk_field: fk_obj})
        created += 1
    return {"created": created, "skipped": skipped, "errors": errors}


IMPORTERS = {
    "samples":                import_samples,
    "protocols":              import_protocols,
    "ngs_samples":            import_ngs_samples,
    "sequencing_batches":     import_sequencing_batches,
    "sequencing_batch_files": import_sequencing_batch_files,
    "sequencing_products":    import_sequencing_products,
    "fastq":        lambda f: _import_simple(f, Fastq,        "sequencing_product", SequencingProduct, "sequencing_product_id"),
    "fastq_files":  lambda f: _import_simple(f, FastqFile,    "fastq",              Fastq,             "fastq_id"),
    "pipelines":    lambda f: _import_simple(f, Pipeline,     "fastq",              Fastq,             "fastq_id"),
    "scripts":      lambda f: _import_simple(f, Script,       "pipeline",           Pipeline,          "pipeline_id"),
    "settings":     lambda f: _import_simple(f, Setting,      "script",             Script,            "script_id"),
    "counts":       lambda f: _import_simple(f, Count,        "pipeline",           Pipeline,          "pipeline_id"),
    "analysis":     lambda f: _import_simple(f, Analysis,     "pipeline",           Pipeline,          "pipeline_id"),
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
                messages.error(request, "Aucun fichier sélectionné.")
            elif not csv_file.name.endswith(".csv"):
                messages.error(request, "Le fichier doit être au format .csv")
            else:
                importer = IMPORTERS.get(self.importer_key)
                try:
                    result = importer(csv_file)
                    for err in result["errors"]:
                        messages.warning(request, err)
                    messages.success(
                        request,
                        f"{result['created']} ligne(s) créée(s), {result['skipped']} ignorée(s)."
                    )
                except Exception as e:
                    messages.error(request, f"Erreur lors de l'import : {e}")

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


@admin.register(Protocol)
class ProtocolAdmin(CsvImportMixin, admin.ModelAdmin):
    importer_key  = "protocols"
    list_display  = ('id', 'primer_pair', 'sample', 'created_at')
    list_filter   = ('created_at',)
    search_fields = ('primer_pair', 'commentary')
    raw_id_fields = ('sample',)


@admin.register(NgsSample)
class NgsSampleAdmin(CsvImportMixin, admin.ModelAdmin):
    importer_key  = "ngs_samples"
    list_display  = ('id', 'index', 'final_concentration', 'protocol')
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
class SequencingBatchAdmin(CsvImportMixin, admin.ModelAdmin):
    importer_key  = "sequencing_batches"
    list_display  = ('id', 'ngs_sample')
    inlines       = [SequencingBatchFileInline, SequencingProductInline]
    raw_id_fields = ('ngs_sample',)


@admin.register(SequencingBatchFile)
class SequencingBatchFileAdmin(CsvImportMixin, admin.ModelAdmin):
    importer_key  = "sequencing_batch_files"
    list_display  = ('id', 'sequencing_batch')
    raw_id_fields = ('sequencing_batch',)


class FastqInline(admin.TabularInline):
    model = Fastq
    extra = 0


@admin.register(SequencingProduct)
class SequencingProductAdmin(CsvImportMixin, admin.ModelAdmin):
    importer_key  = "sequencing_products"
    list_display  = ('id', 'date', 'sequencing_machine', 'flowcell', 'read_length', 'read_depth', 'custom_recipe')
    list_filter   = ('sequencing_machine', 'custom_recipe')
    inlines       = [FastqInline]
    raw_id_fields = ('sequencing_batch',)


class FastqFileInline(admin.TabularInline):
    model = FastqFile
    extra = 1


class PipelineInline(admin.TabularInline):
    model = Pipeline
    extra = 0


@admin.register(Fastq)
class FastqAdmin(CsvImportMixin, admin.ModelAdmin):
    importer_key  = "fastq"
    list_display  = ('id', 'sequencing_product')
    inlines       = [FastqFileInline, PipelineInline]
    raw_id_fields = ('sequencing_product',)


@admin.register(FastqFile)
class FastqFileAdmin(CsvImportMixin, admin.ModelAdmin):
    importer_key  = "fastq_files"
    list_display  = ('id', 'fastq')
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
class PipelineAdmin(CsvImportMixin, admin.ModelAdmin):
    importer_key  = "pipelines"
    list_display  = ('id', 'fastq')
    inlines       = [ScriptInline, CountInline, AnalysisInline]
    raw_id_fields = ('fastq',)


class SettingInline(admin.TabularInline):
    model = Setting
    extra = 0


@admin.register(Script)
class ScriptAdmin(CsvImportMixin, admin.ModelAdmin):
    importer_key  = "scripts"
    list_display  = ('id', 'pipeline')
    inlines       = [SettingInline]
    raw_id_fields = ('pipeline',)


@admin.register(Setting)
class SettingAdmin(CsvImportMixin, admin.ModelAdmin):
    importer_key  = "settings"
    list_display  = ('id', 'script')
    raw_id_fields = ('script',)


@admin.register(Count)
class CountAdmin(CsvImportMixin, admin.ModelAdmin):
    importer_key  = "counts"
    list_display  = ('id', 'pipeline')
    raw_id_fields = ('pipeline',)


@admin.register(Analysis)
class AnalysisAdmin(CsvImportMixin, admin.ModelAdmin):
    importer_key  = "analysis"
    list_display  = ('id', 'pipeline')
    raw_id_fields = ('pipeline',)