#!/usr/bin/env python3
"""
Génère les fichiers CSV template pour l'import batch.
Placer ce script à la racine du projet et l'exécuter une seule fois :
    python generate_csv_templates.py
"""
import csv
import os

TEMPLATES_DIR = "csv_templates"
os.makedirs(TEMPLATES_DIR, exist_ok=True)

TEMPLATES = {
    "01_samples.csv": {
        "headers": [
            "name",
            "project_name",
            "sample_type",       # choices: cell_line, primary_culture, tissue, organoid, other
            "plasmid_number",    # integer, optionnel
            "production_number", # integer, optionnel
            "biological_model",  # optionnel
            "organ",             # optionnel
            "serotype",          # optionnel
            "condition",         # optionnel
            "description",       # optionnel
        ],
        "example": [
            "Sample_A",
            "Project_Vision_2024",
            "cell_line",
            "42",
            "7",
            "Mouse retina",
            "Retina",
            "AAV9",
            "Treated",
            "Primary retinal cells treated with AAV9",
        ],
    },
    "02_protocols.csv": {
        "headers": [
            "sample_name",       # FK → samples.name (doit exister en base)
            "primer_pair",       # optionnel
            "commentary",        # optionnel
        ],
        "example": [
            "Sample_A",
            "Primer_F1/R1",
            "Standard PCR protocol",
        ],
    },
    "03_ngs_samples.csv": {
        "headers": [
            "protocol_primer_pair",    # FK → protocols.primer_pair
            "protocol_sample_name",    # FK → protocols.sample.name (pour lever l'ambiguïté)
            "index",                   # optionnel
            "final_concentration",     # float, optionnel
        ],
        "example": [
            "Primer_F1/R1",
            "Sample_A",
            "IDT_i7_101",
            "2.5",
        ],
    },
    "04_sequencing_batches.csv": {
        "headers": [
            "ngs_sample_index",        # FK → ngs_samples.index
            "ngs_sample_protocol_primer_pair",  # pour lever l'ambiguïté
        ],
        "example": [
            "IDT_i7_101",
            "Primer_F1/R1",
        ],
    },
    "05_sequencing_batch_files.csv": {
        "headers": [
            "sequencing_batch_id",     # FK → sequencing_batches.id (entier)
        ],
        "example": [
            "1",
        ],
    },
    "06_sequencing_products.csv": {
        "headers": [
            "sequencing_batch_id",     # FK → sequencing_batches.id
            "date",                    # format libre, ex. 2024-01-15
            "sequencing_machine",      # optionnel
            "flowcell",                # optionnel
            "read_length",             # integer, optionnel
            "read_depth",              # integer, optionnel
            "phix_proportion",         # float, optionnel
            "custom_recipe",           # true/false
            "custom_recipe_start",     # integer, optionnel
            "custom_recipe_end",       # integer, optionnel
        ],
        "example": [
            "1",
            "2024-01-15",
            "NextSeq 500",
            "H7YNLBGXN",
            "150",
            "30000000",
            "1.5",
            "false",
            "",
            "",
        ],
    },
    "07_fastq.csv": {
        "headers": [
            "sequencing_product_id",   # FK → sequencing_products.id
        ],
        "example": [
            "1",
        ],
    },
    "08_fastq_files.csv": {
        "headers": [
            "fastq_id",                # FK → fastq.id
        ],
        "example": [
            "1",
        ],
    },
    "09_pipelines.csv": {
        "headers": [
            "fastq_id",                # FK → fastq.id
        ],
        "example": [
            "1",
        ],
    },
    "10_scripts.csv": {
        "headers": [
            "pipeline_id",             # FK → pipelines.id
        ],
        "example": [
            "1",
        ],
    },
    "11_settings.csv": {
        "headers": [
            "script_id",               # FK → scripts.id
        ],
        "example": [
            "1",
        ],
    },
    "12_counts.csv": {
        "headers": [
            "pipeline_id",             # FK → pipelines.id
        ],
        "example": [
            "1",
        ],
    },
    "13_analysis.csv": {
        "headers": [
            "pipeline_id",             # FK → pipelines.id
        ],
        "example": [
            "1",
        ],
    },
}

for filename, config in TEMPLATES.items():
    filepath = os.path.join(TEMPLATES_DIR, filename)
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(config["headers"])
        writer.writerow(config["example"])
    print(f"✔ {filepath}")

print(f"\n{len(TEMPLATES)} templates générés dans ./{TEMPLATES_DIR}/")