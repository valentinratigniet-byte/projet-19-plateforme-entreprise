# Ops — automatisation transverse

Scripts et workflows n8n qui ne rattachent à aucun domaine précis
(housekeeping, sauvegarde, RGPD, alerting, digest transverse) —
distincts de `domaines/*` (ETL par domaine) et `dbt/` (transformation).
Même pattern que les domaines : script Python (ou SQL, ou script existant
réutilisé tel quel) + wrapper `run_*.sh.example` (secret réel hors du
JSON du workflow n8n, un seul fichier `.sh` non commité à mettre à jour
sur le serveur) + workflow n8n qui appelle `bash run_*.sh` via un nœud
SSH.

**Pas de canal de notification externe (email/Slack) configuré dans ce
projet.** Les workflows "alerte" écrivent dans un journal consultable
(`ops/logs/*.log` sur le VPS) plutôt que de simuler un envoi vers un
canal qui n'existe pas — honnête sur la limite plutôt que de prétendre
notifier quelqu'un.

| Script | Rôle | Workflow n8n |
|---|---|---|
| `run_housekeeping.sh.example` | Relance `docs/housekeeping/script_maison.py`, historise le résultat | Housekeeping hebdomadaire |
| `run_reverse_etl.sh.example` | Relance `domaines/marketing-activite/reverse_etl.py` | Reverse ETL planifié |
| `run_backup_entrepot.sh.example` | `pg_dump` de l'entrepôt, rotation 7 jours | Sauvegarde entrepôt |
| `run_verifier_rls.sh.example` | Relance les 3 `test_rls.py` de domaine existants (pas de script neuf), journalise | Vérification RLS post-déploiement (déclenché par un appel webhook ajouté à la fin du DAG dbt, après `dbt_test`) |
| `digest_transverse.py` + `.sh` | Agrège CA Ventes/rapprochement Factur-X/cohérence campagnes | Digest hebdomadaire transverse |
| `verifier_derive_qualite.py` + `.sh` | Compare les taux mesurés (doublons, SIREN invalide) à la référence documentée dans `avant.md` de chaque domaine | Alerte dérive qualité |
| `refresh_filiation.sh.example` | Scan additif Filiation (`scan_database.py --merge`) + push git | Refresh Filiation automatisé |
| `domaines/marketing-activite/run_rgpd_anonymiser.sh.example` + `rgpd_anonymiser.py` | Anonymise un contact sur demande (email en paramètre) | Traitement demande RGPD (webhook) |

Le webhook d'alerte échec DAG (déclenché par `on_failure_callback` sur
le DAG Airflow) et le webhook Factur-X entrant vivent uniquement côté
n8n (pas de script dédié, juste un nœud SSH qui journalise le
payload/rappelle `run_ingestion.sh`) — voir `n8n/*.json`.

## Refresh Filiation — deploy key GitHub

`refresh_filiation.sh` a besoin d'écrire sur
[projet-14-filiation](https://github.com/valentinratigniet-byte/projet-14-filiation)
depuis le VPS. Choix : **deploy key SSH dédiée** (`gh repo deploy-key add
--allow-write`, accès en écriture scopé à **ce seul repo**) plutôt qu'un
PAT compte entier — même si un PAT à grain fin scopé sur un repo aurait
aussi convenu, la deploy key ne demande aucune validation navigateur et
se révoque en un clic sur le repo concerné
(`gh repo deploy-key delete`). Clé privée déposée sur
`/opt/projet19/ops/filiation_deploy_key` (jamais commitée, jamais dans
le JSON du workflow), utilisée via `GIT_SSH_COMMAND` et un remote SSH
(`git@github.com:...`) plutôt qu'HTTPS+token.

**Vérifié en conditions réelles** : premier lancement du script a produit
un vrai commit sur `projet-14-filiation`
([`d7a07b1`](https://github.com/valentinratigniet-byte/projet-14-filiation/commit/d7a07b1))
— 137 nœuds confirmés après fusion, cohérent avec le dernier scan manuel
de la Phase 7 (rien n'avait changé entre-temps, donc pas de nouveau
nœud — c'est le comportement attendu, pas un échec silencieux).

**Bug trouvé et corrigé en testant** : `scripts/scan_database.py`
importe `extract_filiation.py`, qui importe `sqlglot` — absent de
l'image `projet19-ingestion` au premier essai (`ModuleNotFoundError`).
Ajouté à `ingestion/requirements.txt` (avec `sqlalchemy`/`pyyaml`,
nécessaires pour `scan_database.py` lui-même), image reconstruite,
re-testé avec succès.
