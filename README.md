# Swirl

Outil interne de suivi de pipeline NGS (séquençage nouvelle génération) pour
l'Institut de la Vision. Swirl trace la chaîne complète d'un échantillon,
de sa réception jusqu'aux résultats d'analyse bio-informatique :

```
Sample → Protocol → NgsSample → SequencingBatch → SequencingBatchFile
                                      │
                                      ├── SequencingProduct → Fastq → FastqFile
                                      │
                                      └── (via Fastq) → Pipeline → Script → Setting
                                                                 → Count
                                                                 → Analysis
```

## Stack technique

- **Backend** : Django 4.2 + Django REST Framework
- **Base de données** : PostgreSQL
- **Tâches asynchrones** : Celery + Redis (`django-celery-beat`)
- **Authentification** : LDAP (Active Directory) via `django-auth-ldap`, avec
  repli sur un backend local restreint aux comptes `staff`/`superuser` si le
  serveur LDAP est injoignable
- **API** : REST Framework + JWT (`djangorestframework-simplejwt`), cookies
  httponly, CORS ouvert pour un frontend externe (`localhost:5173`)
- **Frontend applicatif** : templates Django server-rendered, Bootstrap 5 +
  `django-crispy-forms`, protégés par authentification de session
- **Admin Django** : gestion et import CSV en masse des données du pipeline
- **Déploiement** : Docker Compose (PostgreSQL, Redis, Gunicorn, Celery Beat,
  Nginx)

## Démarrage rapide (Docker)

```bash
cp .env.example .env
# Renseigner les valeurs (base de données, LDAP, SMTP…) avec l'administrateur du projet
docker compose up -d --build
```

Au démarrage, le conteneur `web` applique automatiquement les migrations et
collecte les fichiers statiques (voir `docker/web/entrypoint.sh`).

L'application est ensuite accessible via Nginx sur `http://localhost/`.

### Créer un compte administrateur

```bash
docker compose exec web python manage.py createsuperuser
```

## Démarrage en local (sans Docker)

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # adapter POSTGRES_HOST=localhost, etc.
cd backend
python manage.py migrate
python manage.py runserver
```

Nécessite une instance PostgreSQL et Redis accessibles localement.

## Applications Django

| App | Rôle |
|---|---|
| `api` | Modèles du pipeline NGS, vues frontend (`ngs/*`), admin + import CSV |
| `authentication` | Utilisateur custom (`CustomUser`), synchronisation LDAP, endpoints JWT |
| `core` | Configuration du projet (settings, urls, Celery, middleware JWT) |

## Frontend applicatif (`/`)

Interface de saisie/consultation du pipeline (liste, détail, création,
modification, suppression pour chaque étape), accessible après connexion sur
`/login/`. Le tableau de bord d'accueil (`/`) donne un aperçu des volumes par
étape.

L'accès à ces pages nécessite une session authentifiée (`login_required` sur
l'ensemble des vues `ngs`) ; la connexion passe par les mêmes
`AUTHENTICATION_BACKENDS` que le reste de l'application (LDAP puis repli
staff/superuser).

## Import de données en masse (CSV)

Chaque modèle du pipeline dispose d'un bouton **« Importer CSV »** dans sa
page liste de l'admin Django (`/admin/`). Des modèles de fichiers prêts à
remplir sont fournis dans [`csv_templates/`](csv_templates/) et doivent être
importés **dans l'ordre** (chaque étape référence les identifiants créés par
la précédente) :

1. `01_samples.csv`
2. `01b_primers.csv`
3. `02_protocols.csv`
4. `03_ngs_samples.csv`
5. `04_sequencing_batches.csv`
6. `05_sequencing_batch_files.csv`
7. `06_sequencing_products.csv`
8. `07_fastq.csv`
9. `08_fastq_files.csv`
10. `09_manual_runs.csv`
11. `10_scripts.csv`
12. `10b_script_parameters.csv`
13. `11_settings.csv`
14. `12_counts.csv`
15. `13_analysis.csv`

Les colonnes de type fichier sont ignorées à l'import et doivent être
déposées manuellement ensuite. Un guide détaillé destiné aux utilisateurs non
techniques est disponible : [`guide_import_csv_swirl.docx`](guide_import_csv_swirl.docx).

## Git

Le workflow Git (connexion au dépôt distant, branches, résolution de
conflits) est documenté dans [`README_GIT.md`](README_GIT.md).

## Fichiers et dossiers ignorés par Git

`.env`, `venv/`, `staticfiles/`, `media/`, `data/`, `__pycache__/` — voir
`.gitignore` et `README_GIT.md` pour le détail.
