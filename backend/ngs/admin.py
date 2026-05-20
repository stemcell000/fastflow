"""
ngs/admin.py — avec import CSV intégré pour chaque modèle.

Chaque modèle admin expose :
  - une action "Importer depuis CSV" dans la liste
  - une vue dédiée /admin/ngs/<model>/import-csv/
  - un template inline (pas de fichier template externe nécessaire)
"""
import os
from django.contrib import admin, messages
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import path, reverse
from django.utils.html import format_html
from django.template.response import TemplateResponse

from .models import (
    Sample, Protocol, NgsSample, SequencingBatch, SequencingBatchFile,
    SequencingProduct, Fastq, FastqFile, Pipeline, Script, Setting, Count, Analysis,
)
from .importers import IMPORTERS


# ─── Mixin générique d'import CSV ─────────────────────────────────────────────

class CsvImportMixin:
    """
    Ajoute une vue /admin/<app>/<model>/import-csv/ et un bouton dans le
    changelist. Hériter de ce mixin dans chaque ModelAdmin.

    Attribut à définir dans la sous-classe :
        importer_key = "samples"  # clé dans IMPORTERS
    """
    importer_key = None

    # ── URLs supplémentaires ──────────────────────────────────────────────────
    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "import-csv/",
                self.admin_site.admin_view(self.import_csv_view),
                name=f"{self.model._meta.app_label}_{self.model._meta.model_name}_import_csv",
            ),
        ]
        return custom + urls

    # ── Vue d'import ──────────────────────────────────────────────────────────
    def import_csv_view(self, request):
        model_name = self.model._meta.verbose_name_plural
        import_url_name = f"admin:{self.model._meta.app_label}_{self.model._meta.model_name}_import_csv"
        changelist_url  = reverse(f"admin:{self.model._meta.app_label}_{self.model._meta.model_name}_changelist")

        result = None
        if request.method == "POST":
            csv_file = request.FILES.get("csv_file")
            if not csv_file:
                messages.error(request, "Aucun fichier sélectionné.")
            elif not csv_file.name.endswith(".csv"):
                messages.error(request, "Le fichier doit être au format .csv")
            else:
                importer = IMPORTERS.get(self.importer_key)
                if importer is None:
                    messages.error(request, f"Importer '{self.importer_key}' non trouvé.")
                else:
                    try:
                        result = importer(csv_file)
                        if result["errors"]:
                            for err in result["errors"]:
                                messages.warning(request, err)
                        messages.success(
                            request,
                            f"{result['created']} ligne(s) créée(s), "
                            f"{result['skipped']} ignorée(s)."
                        )
                    except Exception as e:
                        messages.error(request, f"Erreur lors de l'import : {e}")

        # Template inline pour éviter les dépendances de fichiers externes
        html = f"""
        {{% extends "admin/base_site.html" %}}
        {{% block content %}}
        <h1>Import CSV — {model_name}</h1>

        {{% if messages %}}
        <ul class="messagelist">
          {{% for message in messages %}}
          <li class="{{ message.tags }}">{{ message }}</li>
          {{% endfor %}}
        </ul>
        {{% endif %}}

        <div style="background:#fff;padding:20px;border:1px solid #ddd;border-radius:4px;max-width:600px;">
          <form method="post" enctype="multipart/form-data">
            {{% csrf_token %}}
            <p>
              <label for="csv_file"><strong>Fichier CSV :</strong></label><br>
              <input type="file" name="csv_file" id="csv_file" accept=".csv" style="margin-top:8px;">
            </p>
            <p style="color:#666;font-size:0.9em;">
              Respecter l'ordre d'import : les enregistrements référencés (FK) doivent
              exister en base avant d'importer les lignes qui en dépendent.
            </p>
            <p>
              <input type="submit" value="Importer" class="default">
              &nbsp;
              <a href="{changelist_url}" class="button cancel-link">Annuler</a>
            </p>
          </form>
        </div>
        {{% endblock %}}
        """

        context = {
            **self.admin_site.each_context(request),
            "title": f"Import CSV — {model_name}",
            "opts": self.model._meta,
        }

        from django.template import Template, Context, RequestContext
        from django.template.loader import render_to_string
        from django.shortcuts import render

        # On utilise un template string simple
        template_str = f"""
{{% extends "admin/base_site.html" %}}
{{% load i18n %}}
{{% block content %}}
<h1>Import CSV — {model_name}</h1>

{{% if messages %}}
<ul class="messagelist">
  {{% for message in messages %}}
  <li class="{{{{ message.tags }}}}">{{{{ message }}}}</li>
  {{% endfor %}}
</ul>
{{% endif %}}

<div style="background:#fff;padding:20px;border:1px solid #ddd;border-radius:4px;max-width:600px;">
  <p style="color:#666;">
    <strong>Ordre d'import conseillé :</strong>
    samples → protocols → ngs_samples → sequencing_batches →
    sequencing_batch_files → sequencing_products → fastq →
    fastq_files → pipelines → scripts → settings → counts → analysis
  </p>
  <form method="post" enctype="multipart/form-data">
    {{% csrf_token %}}
    <p>
      <label for="csv_file"><strong>Fichier CSV :</strong></label><br>
      <input type="file" name="csv_file" id="csv_file" accept=".csv"
             style="margin-top:8px;">
    </p>
    <p>
      <input type="submit" value="Importer" class="default">
      &nbsp;
      <a href="{changelist_url}">Annuler</a>
    </p>
  </form>
</div>
{{% endblock %}}
"""
        return TemplateResponse(
            request,
            "admin/ngs/csv_import.html",
            context,
        )

    # ── Bouton dans le changelist ─────────────────────────────────────────────
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        import_url = reverse(
            f"admin:{self.model._meta.app_label}_{self.model._meta.model_name}_import_csv"
        )
        extra_context["import_csv_url"] = import_url
        return super().changelist_view(request, extra_context=extra_context)


# ─── ModelAdmins ──────────────────────────────────────────────────────────────

@admin.register(Sample)
class SampleAdmin(CsvImportMixin, admin.ModelAdmin):
    importer_key = "samples"
    list_display  = ("name", "project_name", "sample_type", "organ", "serotype", "created_at")
    list_filter   = ("sample_type", "project_name")
    search_fields = ("name", "project_name", "biological_model", "organ")


@admin.register(Protocol)
class ProtocolAdmin(CsvImportMixin, admin.ModelAdmin):
    importer_key = "protocols"
    list_display  = ("id", "primer_pair", "sample", "created_at")
    list_filter   = ("created_at",)
    search_fields = ("primer_pair", "commentary")
    raw_id_fields = ("sample",)


@admin.register(NgsSample)
class NgsSampleAdmin(CsvImportMixin, admin.ModelAdmin):
    importer_key = "ngs_samples"
    list_display  = ("id", "index", "final_concentration", "protocol")
    search_fields = ("index",)
    raw_id_fields = ("protocol",)


class SequencingBatchFileInline(admin.TabularInline):
    model  = SequencingBatchFile
    extra  = 1


class SequencingProductInline(admin.TabularInline):
    model  = SequencingProduct
    extra  = 0
    fields = ("date", "sequencing_machine", "flowcell", "read_length", "read_depth")


@admin.register(SequencingBatch)
class SequencingBatchAdmin(CsvImportMixin, admin.ModelAdmin):
    importer_key = "sequencing_batches"
    list_display  = ("id", "ngs_sample")
    inlines       = [SequencingBatchFileInline, SequencingProductInline]
    raw_id_fields = ("ngs_sample",)


@admin.register(SequencingBatchFile)
class SequencingBatchFileAdmin(CsvImportMixin, admin.ModelAdmin):
    importer_key = "sequencing_batch_files"
    list_display  = ("id", "sequencing_batch")
    raw_id_fields = ("sequencing_batch",)


class FastqInline(admin.TabularInline):
    model = Fastq
    extra = 0


@admin.register(SequencingProduct)
class SequencingProductAdmin(CsvImportMixin, admin.ModelAdmin):
    importer_key = "sequencing_products"
    list_display = (
        "id", "date", "sequencing_machine", "flowcell",
        "read_length", "read_depth", "custom_recipe",
    )
    list_filter   = ("sequencing_machine", "custom_recipe")
    inlines       = [FastqInline]
    raw_id_fields = ("sequencing_batch",)


class FastqFileInline(admin.TabularInline):
    model = FastqFile
    extra = 1


class PipelineInline(admin.TabularInline):
    model = Pipeline
    extra = 0


@admin.register(Fastq)
class FastqAdmin(CsvImportMixin, admin.ModelAdmin):
    importer_key  = "fastq"
    list_display  = ("id", "sequencing_product")
    inlines       = [FastqFileInline, PipelineInline]
    raw_id_fields = ("sequencing_product",)


@admin.register(FastqFile)
class FastqFileAdmin(CsvImportMixin, admin.ModelAdmin):
    importer_key  = "fastq_files"
    list_display  = ("id", "fastq")
    raw_id_fields = ("fastq",)


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
    list_display  = ("id", "fastq")
    inlines       = [ScriptInline, CountInline, AnalysisInline]
    raw_id_fields = ("fastq",)


class SettingInline(admin.TabularInline):
    model = Setting
    extra = 0


@admin.register(Script)
class ScriptAdmin(CsvImportMixin, admin.ModelAdmin):
    importer_key  = "scripts"
    list_display  = ("id", "pipeline")
    inlines       = [SettingInline]
    raw_id_fields = ("pipeline",)


@admin.register(Setting)
class SettingAdmin(CsvImportMixin, admin.ModelAdmin):
    importer_key  = "settings"
    list_display  = ("id", "script")
    raw_id_fields = ("script",)


@admin.register(Count)
class CountAdmin(CsvImportMixin, admin.ModelAdmin):
    importer_key  = "counts"
    list_display  = ("id", "pipeline")
    raw_id_fields = ("pipeline",)


@admin.register(Analysis)
class AnalysisAdmin(CsvImportMixin, admin.ModelAdmin):
    importer_key  = "analysis"
    list_display  = ("id", "pipeline")
    raw_id_fields = ("pipeline",)