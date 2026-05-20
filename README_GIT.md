# Synchronisation avec le dépôt Git distant

Ce document explique comment connecter ta copie locale du projet au dépôt Git
distant et rester synchronisé avec les mises à jour.

---

## Prérequis

- [Git](https://git-scm.com/downloads) installé sur ta machine
- L'URL du dépôt distant : https://github.com/stemcell000/fastflow.git
- Être dans le dossier racine du projet sur ton ordinateur:

```bash
cd /chemin/vers/fastflow
```

---

## 1. Première connexion au dépôt distant

À faire **une seule fois** pour lier ta copie locale au dépôt distant.

### 1.1 Initialiser Git (si ce n'est pas déjà fait)

```bash
git init
```

### 1.2 Vérifier si un remote existe déjà

```bash
git remote -v
```

Si la commande ne retourne rien, passer à l'étape suivante.
Si `origin` est déjà listé, passer directement à la **section 2**.

### 1.3 Ajouter le dépôt distant

```bash
git remote add origin https://github.com/ton-username/fastflow.git
```

> Remplacer l'URL par celle communiquée par l'administrateur.

### 1.4 Récupérer l'historique et se connecter à la branche principale

```bash
git fetch origin
git branch --set-upstream-to=origin/main main
```

### 1.5 Configurer ton identité Git (si ce n'est pas déjà fait)

```bash
git config --global user.name "Ton Nom"
git config --global user.email "ton.email@example.com"
```

---

## 2. Récupérer les mises à jour (usage courant)

À chaque fois que tu veux récupérer les dernières modifications :

```bash
git pull origin main #branche de départ, idem ta première copie/installation
git pull origin csv_import #branche contenant les modifications afin d'importer des données (csv) depuis l'admin django

Dans la suite, les exemples sont données avec la branche main. Adapte en fonction de celles avec laquelles tu veux travailler.

```

---

## 3. Résoudre les conflits

### Cas A — tu n'as pas modifié de fichiers localement

```bash
git pull origin main
```

Aucun conflit attendu.

### Cas B — tu as modifié des fichiers localement

#### Option 1 — Mettre de côté tes modifications, puller, puis les réappliquer

```bash
git stash          # mise en attente de tes modifications
git pull origin main
git stash pop      # réapplication de tes modifications
```

> Si des conflits apparaissent après `git stash pop`, Git les signale
> dans les fichiers concernés avec des marqueurs `<<<<<<`. Ouvrir
> les fichiers, résoudre manuellement, puis :
> ```bash
> git add .
> git stash drop
> ```

#### Option 2 — Écraser tes fichiers locaux par la version distante

> ⚠️ **Attention** : toutes tes modifications locales seront perdues.

```bash
git fetch origin
git reset --hard origin/main
```

---

## 4. Fichiers à ne jamais modifier ni commiter

Ces fichiers sont ignorés par Git (listés dans `.gitignore`) et ne
seront jamais synchronisés :

| Fichier / Dossier | Raison |
|---|---|
| `.env` | Contient des secrets (mots de passe, clés API) |
| `venv/` | Environnement virtuel Python — propre à chaque machine |
| `staticfiles/` | Généré automatiquement par Django |
| `media/` | Fichiers uploadés — propres à chaque instance |
| `data/` | Données locales Celery Beat |
| `__pycache__/` | Cache Python |

### Configurer ton `.env` local

Le fichier `.env` n'est pas synchronisé. Tu dois le créer à partir du
template fourni :

```bash
cp .env.example .env
```

Puis renseigner les valeurs avec l'administrateur du projet.

---

## 5. Vérifier l'état de ta copie locale

```bash
# Voir les fichiers modifiés localement
git status

# Voir les différences entre ta version et le distant
git fetch origin
git diff HEAD origin/main

# Voir l'historique des commits
git log --oneline -10
```

---

## 6. Commandes de référence rapide

| Commande | Description |
|---|---|
| `git pull origin main` | Récupérer les dernières mises à jour |
| `git status` | État des fichiers locaux |
| `git stash` | Mettre de côté les modifications locales |
| `git stash pop` | Réappliquer les modifications mises de côté |
| `git fetch origin` | Récupérer les infos du distant sans merger |
| `git reset --hard origin/main` | ⚠️ Écraser le local par le distant |
| `git log --oneline -10` | Voir les 10 derniers commits |
| `git remote -v` | Vérifier le dépôt distant configuré |

---

## 7. En cas de problème

Contacter l'administrateur du projet en fournissant le résultat de :

```bash
git status
git remote -v
git log --oneline -5
```
