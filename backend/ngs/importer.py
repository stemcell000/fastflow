"""
ngs/importers.py

Logique d'import CSV pour tous les modèles NGS.
Chaque importer retourne un dict :
    {
        "created": int,
        "skipped": int,
        "errors": list[str],
    }
"""
import csv
import io
import logging

from .models import (
    Sample, Protocol, NgsSample, SequencingBatch, SequencingBatchFile,
    SequencingProduct, Fastq, FastqFile, Pipeline, Script, Setting, Count, Analysis,
)

logger = logging.getLogger(__name__)


def _parse_bool(value):
    return str(value).strip().lower() in ("true", "1", "yes", "oui")


def _parse_int(value):
    v = str(value).strip()
    return int(v) if v else None


def _parse_float(value):
    v = str(value).strip()
    return float(v) if v else None


def _read_csv(file_obj):
    """Lit un fichier CSV uploadé (InMemoryUploadedFile ou chemin) et retourne les lignes."""
    if hasattr(file_obj, "read"):
        content = file_obj.read()
        if isinstance(content, bytes):
            content = content.decode("utf-8-sig")  # gère le BOM Excel
        reader = csv.DictReader(io.StringIO(content))
    else:
        with open(file_obj, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
    return list(reader)


# ─── Samples ──────────────────────────────────────────────────────────────────

def import_samples(file_obj):
    rows = _read_csv(file_obj)
    created, skipped, errors = 0, 0, []

    for i, row in enumerate(rows, start=2):
        name = row.get("name", "").strip()
        project_name = row.get("project_name", "").strip()

        if not name or not project_name:
            errors.append(f"Ligne {i} : 'name' et 'project_name' sont obligatoires.")
            skipped += 1
            continue

        _, was_created = Sample.objects.get_or_create(
            name=name,
            project_name=project_name,
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
        if was_created:
            created += 1
        else:
            skipped += 1

    return {"created": created, "skipped": skipped, "errors": errors}


# ─── Protocols ────────────────────────────────────────────────────────────────

def import_protocols(file_obj):
    rows = _read_csv(file_obj)
    created, skipped, errors = 0, 0, []

    for i, row in enumerate(rows, start=2):
        sample_name = row.get("sample_name", "").strip()
        primer_pair = row.get("primer_pair", "").strip()

        if not sample_name:
            errors.append(f"Ligne {i} : 'sample_name' est obligatoire.")
            skipped += 1
            continue

        try:
            sample = Sample.objects.get(name=sample_name)
        except Sample.DoesNotExist:
            errors.append(f"Ligne {i} : Sample '{sample_name}' introuvable.")
            skipped += 1
            continue
        except Sample.MultipleObjectsReturned:
            errors.append(f"Ligne {i} : Plusieurs samples nommés '{sample_name}' — utiliser l'import par id.")
            skipped += 1
            continue

        _, was_created = Protocol.objects.get_or_create(
            sample=sample,
            primer_pair=primer_pair,
            defaults={
                "commentary": row.get("commentary", "").strip(),
            },
        )
        if was_created:
            created += 1
        else:
            skipped += 1

    return {"created": created, "skipped": skipped, "errors": errors}


# ─── NGS Samples ──────────────────────────────────────────────────────────────

def import_ngs_samples(file_obj):
    rows = _read_csv(file_obj)
    created, skipped, errors = 0, 0, []

    for i, row in enumerate(rows, start=2):
        primer_pair  = row.get("protocol_primer_pair", "").strip()
        sample_name  = row.get("protocol_sample_name", "").strip()
        index        = row.get("index", "").strip()

        if not primer_pair or not sample_name:
            errors.append(f"Ligne {i} : 'protocol_primer_pair' et 'protocol_sample_name' sont obligatoires.")
            skipped += 1
            continue

        try:
            protocol = Protocol.objects.get(
                primer_pair=primer_pair,
                sample__name=sample_name,
            )
        except Protocol.DoesNotExist:
            errors.append(f"Ligne {i} : Protocol '{primer_pair}' pour sample '{sample_name}' introuvable.")
            skipped += 1
            continue
        except Protocol.MultipleObjectsReturned:
            errors.append(f"Ligne {i} : Plusieurs protocols correspondent — affiner les critères.")
            skipped += 1
            continue

        _, was_created = NgsSample.objects.get_or_create(
            protocol=protocol,
            index=index,
            defaults={
                "final_concentration": _parse_float(row.get("final_concentration", "")),
            },
        )
        if was_created:
            created += 1
        else:
            skipped += 1

    return {"created": created, "skipped": skipped, "errors": errors}


# ─── Sequencing Batches ───────────────────────────────────────────────────────

def import_sequencing_batches(file_obj):
    rows = _read_csv(file_obj)
    created, skipped, errors = 0, 0, []

    for i, row in enumerate(rows, start=2):
        ngs_index   = row.get("ngs_sample_index", "").strip()
        primer_pair = row.get("ngs_sample_protocol_primer_pair", "").strip()

        if not ngs_index:
            errors.append(f"Ligne {i} : 'ngs_sample_index' est obligatoire.")
            skipped += 1
            continue

        qs = NgsSample.objects.filter(index=ngs_index)
        if primer_pair:
            qs = qs.filter(protocol__primer_pair=primer_pair)

        try:
            ngs_sample = qs.get()
        except NgsSample.DoesNotExist:
            errors.append(f"Ligne {i} : NGS Sample '{ngs_index}' introuvable.")
            skipped += 1
            continue
        except NgsSample.MultipleObjectsReturned:
            errors.append(f"Ligne {i} : Plusieurs NGS Samples correspondent à '{ngs_index}' — préciser 'ngs_sample_protocol_primer_pair'.")
            skipped += 1
            continue

        SequencingBatch.objects.create(ngs_sample=ngs_sample)
        created += 1

    return {"created": created, "skipped": skipped, "errors": errors}


# ─── Sequencing Batch Files ───────────────────────────────────────────────────

def import_sequencing_batch_files(file_obj):
    rows = _read_csv(file_obj)
    created, skipped, errors = 0, 0, []

    for i, row in enumerate(rows, start=2):
        batch_id = _parse_int(row.get("sequencing_batch_id", ""))
        if not batch_id:
            errors.append(f"Ligne {i} : 'sequencing_batch_id' est obligatoire.")
            skipped += 1
            continue

        try:
            batch = SequencingBatch.objects.get(pk=batch_id)
        except SequencingBatch.DoesNotExist:
            errors.append(f"Ligne {i} : SequencingBatch id={batch_id} introuvable.")
            skipped += 1
            continue

        SequencingBatchFile.objects.create(sequencing_batch=batch)
        created += 1

    return {"created": created, "skipped": skipped, "errors": errors}


# ─── Sequencing Products ──────────────────────────────────────────────────────

def import_sequencing_products(file_obj):
    rows = _read_csv(file_obj)
    created, skipped, errors = 0, 0, []

    for i, row in enumerate(rows, start=2):
        batch_id = _parse_int(row.get("sequencing_batch_id", ""))
        if not batch_id:
            errors.append(f"Ligne {i} : 'sequencing_batch_id' est obligatoire.")
            skipped += 1
            continue

        try:
            batch = SequencingBatch.objects.get(pk=batch_id)
        except SequencingBatch.DoesNotExist:
            errors.append(f"Ligne {i} : SequencingBatch id={batch_id} introuvable.")
            skipped += 1
            continue

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


# ─── Helpers génériques pour les tables simples (FK entière uniquement) ───────

def _import_simple(file_obj, model_class, fk_field, fk_model, fk_col):
    rows = _read_csv(file_obj)
    created, skipped, errors = 0, 0, []

    for i, row in enumerate(rows, start=2):
        fk_id = _parse_int(row.get(fk_col, ""))
        if not fk_id:
            errors.append(f"Ligne {i} : '{fk_col}' est obligatoire.")
            skipped += 1
            continue
        try:
            fk_obj = fk_model.objects.get(pk=fk_id)
        except fk_model.DoesNotExist:
            errors.append(f"Ligne {i} : {fk_model.__name__} id={fk_id} introuvable.")
            skipped += 1
            continue

        model_class.objects.create(**{fk_field: fk_obj})
        created += 1

    return {"created": created, "skipped": skipped, "errors": errors}


def import_fastq(file_obj):
    return _import_simple(file_obj, Fastq, "sequencing_product", SequencingProduct, "sequencing_product_id")

def import_fastq_files(file_obj):
    return _import_simple(file_obj, FastqFile, "fastq", Fastq, "fastq_id")

def import_pipelines(file_obj):
    return _import_simple(file_obj, Pipeline, "fastq", Fastq, "fastq_id")

def import_scripts(file_obj):
    return _import_simple(file_obj, Script, "pipeline", Pipeline, "pipeline_id")

def import_settings(file_obj):
    return _import_simple(file_obj, Setting, "script", Script, "script_id")

def import_counts(file_obj):
    return _import_simple(file_obj, Count, "pipeline", Pipeline, "pipeline_id")

def import_analysis(file_obj):
    return _import_simple(file_obj, Analysis, "pipeline", Pipeline, "pipeline_id")


# ─── Registre central ─────────────────────────────────────────────────────────

IMPORTERS = {
    "samples":                  import_samples,
    "protocols":                import_protocols,
    "ngs_samples":              import_ngs_samples,
    "sequencing_batches":       import_sequencing_batches,
    "sequencing_batch_files":   import_sequencing_batch_files,
    "sequencing_products":      import_sequencing_products,
    "fastq":                    import_fastq,
    "fastq_files":              import_fastq_files,
    "pipelines":                import_pipelines,
    "scripts":                  import_scripts,
    "settings":                 import_settings,
    "counts":                   import_counts,
    "analysis":                 import_analysis,
}