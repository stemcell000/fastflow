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
            "project_name",         # optional
            "sample_type",          # choices: cell_line, primary_culture, tissue, organoid, aav, plasmid, other
            "sample_type_other",    # free text, used only when sample_type = other
            "plasmid_number",       # integer, optional, used only when sample_type = plasmid
            "production_number",    # integer, optional, used only when sample_type = aav
            "biological_model",     # choices: human, macaca_mulatta, chlorocebus, mouse, pig, other
            "organ",                # choices: retina, brain_cortex, brain_lgn, muscle, cochlea, other
            "organ_other",          # free text, used only when organ = other
            "serotype",             # choices: aav2, aav5, aav9, other
            "serotype_other",       # free text, used only when serotype = other
            "condition",            # choices: ex_vivo, in_vivo, in_vitro
            "injection_type",       # choices: sub_retinal, intra_vitreal, other
            "injection_type_other", # free text, used only when injection_type = other
            "description",          # optional, texte long
        ],
        "example": [
            "Sample_A",
            "Project_Vision_2024",
            "aav",
            "",
            "",
            "7",
            "mouse",
            "retina",
            "",
            "aav9",
            "",
            "in_vivo",
            "sub_retinal",
            "",
            "Primary retinal cells treated with AAV9",
        ],
    },
    "01b_primers.csv": {
        "headers": [
            "name",              # unique primer name/identifier
        ],
        "example": [
            "Primer_F1",
        ],
    },
    "02_protocols.csv": {
        "headers": [
            "sample_name",       # FK → samples.name (doit exister en base)
            "name",              # optionnel, nom libre du protocole
            "primer_1",          # optionnel, FK → primers.name (créé automatiquement si absent)
            "primer_2",          # optionnel, FK → primers.name (créé automatiquement si absent)
            "commentary",        # optionnel
        ],
        "example": [
            "Sample_A",
            "Standard PCR",
            "Primer_F1",
            "Primer_R1",
            "Standard PCR protocol",
        ],
    },
    "03_ngs_samples.csv": {
        "headers": [
            "protocol_primer_1",       # FK → protocols.primer_1.name (au moins un des deux primers requis)
            "protocol_primer_2",       # FK → protocols.primer_2.name
            "protocol_sample_name",    # FK → one of protocols.samples.name (disambiguates which protocol usage)
            "operating_name",          # optional, defaults to protocol_sample_name if blank
            "index_1",                 # optional
            "index_2",                 # optional
            "final_concentration",     # float, optional
        ],
        "example": [
            "Primer_F1",
            "Primer_R1",
            "Sample_A",
            "Sample_A_seq1",
            "IDT_i7_101",
            "IDT_i5_101",
            "2.5",
        ],
    },
    "04_sequencing_batches.csv": {
        "headers": [
            "batch_key",                         # groups rows into the same batch (blank = one batch per row)
            "ngs_sample_index_1",                # FK → ngs_samples.index_1 (must be non-empty)
            "ngs_sample_protocol_primer_1",       # optional, disambiguates when index_1 isn't unique
            "ngs_sample_protocol_primer_2",       # optional, disambiguates when index_1 isn't unique
        ],
        "example": [
            "1",
            "IDT_i7_101",
            "Primer_F1",
            "Primer_R1",
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
            "ngs_sample_id",           # optional, FK → ngs_samples.id (NGS sample this FASTQ was demultiplexed for)
        ],
        "example": [
            "1",
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
    "09_manual_runs.csv": {
        "headers": [
            "sequencing_product_id",   # FK → sequencing_products.id (one manual run per product)
        ],
        "example": [
            "1",
        ],
    },
    "10_scripts.csv": {
        "headers": [
            "manual_run_id",           # FK → manual_runs.id
        ],
        "example": [
            "1",
        ],
    },
    "10b_script_parameters.csv": {
        "headers": [
            "script_id",               # FK → scripts.id
            "name",                    # e.g. --input
            "description",             # what to enter for this parameter
        ],
        "example": [
            "1",
            "--threshold",
            "Numeric cutoff applied during filtering",
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
            "manual_run_id",           # FK → manual_runs.id
        ],
        "example": [
            "1",
        ],
    },
    "13_analysis.csv": {
        "headers": [
            "manual_run_id",           # FK → manual_runs.id
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