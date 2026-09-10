# Outils — quoi, pour quelle tâche, pourquoi ce choix, comment

Inventaire complet des outils réellement utilisés dans le projet (vérifié
contre `ingestion/requirements.txt`, les `docker-compose.yml` de chaque
domaine, `airflow/Dockerfile` et `.github/workflows/ci.yml` — rien listé
ici n'est aspirationnel). Pour chaque outil : à quoi il sert dans *ce*
projet, pourquoi il a été choisi plutôt qu'une alternative, et comment il
est concrètement déclenché.

Les **règles transverses** qui s'appliquent quel que soit l'outil sont en
fin de document.

## Sources — bases "de production" simulées

| Outil | Tâche | Pourquoi ce choix | Comment |
|---|---|---|---|
| [SQL Server](https://www.microsoft.com/sql-server) — édition Developer, `mcr.microsoft.com/mssql/server:2022-latest` | ERP comptable du domaine Finance/Compta — fournisseurs et écritures y sont peuplés *directement*, ce n'est pas un export à ingérer. | Techno standard des ERP compta réels (Sage, Cegid, SAP Business One) — reproduire un vrai ERP veut dire reproduire sa techno, pas un mock Postgres déguisé. Édition **Developer** forcée (`MSSQL_PID=Developer`) : gratuite et sans expiration, contrairement à l'édition Evaluation par défaut qui expire à 180 jours. | `domaines/finance-compta/source/docker-compose.yml` ; lu en lecture seule par `ingestion/adaptateurs/sqlserver.py` (`pymssql`). |
| [MySQL 8](https://www.mysql.com/) | Base du domaine Marketing/Activité (contacts, campagnes, envois). | Techno standard des stacks web/CRM — cohérent avec le choix AS/400↔ERP commercial et SQL Server↔ERP compta : une vraie techno par domaine, pas 3× la même base. | `domaines/marketing-activite/source/docker-compose.yml` ; lu par `ingestion/adaptateurs/mysql.py` (`PyMySQL`). |
| AS/400 (IBM i / [Db2 for i](https://www.ibm.com/products/db2-for-i)) | Système de gestion commerciale du domaine Ventes/Commerce. | Très répandu en ERP/gestion commerciale industrie-distribution françaises. Pas de connexion live (licence IBM i, coût) — et ce n'est de toute façon pas ainsi qu'un atelier AS/400 réel partage sa donnée : un job batch nocturne dépose un export à largeur fixe, simulé honnêtement plutôt qu'une connexion inventée. | `domaines/ventes-commerce/source/simulateur_as400.py` génère l'export ; lu par `ingestion/adaptateurs/fichier_plat.py`. |
| [PostgreSQL 16](https://www.postgresql.org/) (`postgres:16-alpine`) | L'entrepôt cible — schémas `raw` → `raw_historise` → `staging`/`marts`. | Le volume du projet ne justifie pas un entrepôt columnar cloud payant ; réutilise l'infra VPS déjà en place. Support natif de la RLS ligne **et** colonne, directement exploité pour la gouvernance. | `entrepot/docker-compose.yml`, rôles `ingestion`/`dbt_transform` à privilège minimal. |

## Ingestion / ETL

| Outil | Tâche | Pourquoi ce choix | Comment |
|---|---|---|---|
| [Python 3.12](https://www.python.org/) | Langage de tous les adaptateurs d'ingestion et simulateurs. | Écosystème de drivers pour les 3 sources (SQL Server, MySQL, fichiers) dans un seul langage, pas 3 stacks différentes. | `ingestion/`, `domaines/*/source/`. |
| [psycopg2](https://www.psycopg.org/) | Driver Postgres — écriture dans l'entrepôt. | Driver de référence, synchrone, suffisant au volume (pas besoin d'async). | `ingestion/adaptateurs/postgres_writer.py`. |
| [pymssql](https://pymssql.org/) | Driver SQL Server. | Plus simple à containeriser que le driver ODBC officiel Microsoft (pas de dépendance système `unixODBC` à gérer dans l'image). | `ingestion/adaptateurs/sqlserver.py`, un seul lecteur générique. |
| [PyMySQL](https://pymysql.readthedocs.io/) | Driver MySQL. | Pur Python, aucune dépendance de compilation — cohérent avec une image d'ingestion légère (216 Mo). | `ingestion/adaptateurs/mysql.py`. |
| [openpyxl](https://openpyxl.readthedocs.io/) | Lecture des fichiers Excel de remises (Ventes). | Standard de fait pour lire du `.xlsx` en Python sans dépendance externe (pas de LibreOffice/Excel installé sur le VPS). | `ingestion/adaptateurs/excel.py`. |
| [Faker](https://faker.readthedocs.io/) | Génération de données synthétiques réalistes (noms, adresses, SIREN...) dans les simulateurs. | Locale `fr_FR`, seed fixe (`Faker.seed(19)`) — déterministe et reproductible, pas de données aléatoires différentes à chaque run. | `domaines/*/source/generer_evenements.py` et simulateurs. |
| [SQLAlchemy](https://www.sqlalchemy.org/) | Introspection générique de base (utilisée par `scan_database.py`, côté Filiation). | Un seul code d'introspection pour Postgres/MySQL/SQL Server plutôt qu'un par dialecte. | `ingestion/requirements.txt` (dépendance de l'intégration Filiation). |
| [sqlglot](https://sqlglot.com/) | Parsing du SQL compilé dbt pour le lignage colonne-à-colonne (Filiation). | Parseur SQL pur Python, pas de dépendance à un vrai moteur de base pour analyser une requête. | Utilisé par `extract_filiation.py`, importé dans l'image d'ingestion. |
| [PyYAML](https://pyyaml.org/) | Lecture des fichiers de config YAML (connexions Filiation). | Standard de fait pour le YAML en Python. | `ingestion/requirements.txt`. |
| [cryptography](https://cryptography.io/) | Dépendance de chiffrement (requise par `pymssql`/`paramiko`). | Bibliothèque de référence, maintenue, auditée. | Dépendance transitive, `ingestion/requirements.txt`. |
| [Paramiko](https://www.paramiko.org/) | Tunnel SSH éphémère pour connecter Filiation à l'entrepôt (jamais exposé publiquement). | Évite d'ouvrir le port Postgres sur Internet pour un scan ponctuel — cohérent avec la doctrine d'accès minimal. | Script jetable, supprimé immédiatement après usage (pas versionné). |

## Transformation — dbt

| Outil | Tâche | Pourquoi ce choix | Comment |
|---|---|---|---|
| [dbt-core](https://www.getdbt.com/) 1.12 + `dbt-postgres` 1.11 | Snapshot (SCD2) → staging → marts, tests, contracts, freshness, exposures, unit tests, documentation. | Standard du marché pour le ELT géré en SQL versionné ; `dbt-postgres` car l'entrepôt cible est Postgres — le SQL migre quasiment sans changement vers un autre adaptateur si le volume l'impose un jour. | `dbt/`, exécuté via l'image officielle `ghcr.io/dbt-labs/dbt-postgres:1.8.latest` en local, ou installé dans l'image Airflow en production (pas `_PIP_ADDITIONAL_REQUIREMENTS`, qui réinstallerait à chaque démarrage). |
| [pg_trgm](https://www.postgresql.org/docs/current/pgtrgm.html) (extension Postgres) | Rapprochement flou nom Excel → client AS/400, nom SaaS → contact MySQL. | Similarité de trigrammes native à Postgres, pas de service externe de fuzzy-matching à héberger. | Activée une fois par superuser (`entrepot/init/02_extensions.sql`), utilisée dans `dim_client.sql`. |

## Orchestration

| Outil | Tâche | Pourquoi ce choix | Comment |
|---|---|---|---|
| [Apache Airflow](https://airflow.apache.org/) 2.10 | Orchestration du pipeline de transformation (`dbt seed → snapshot → run → test → docs generate`), quotidien à 5h UTC. | Retries fins, sensors, et le **backfill** natif que n8n gère mal — le pairing dbt+Airflow est le plus reconnu du marché data engineering. `LocalExecutor` (pas Celery/Redis) car le VPS n'a que 2 vCPU, inutile à ce volume. | `airflow/dags/dbt_pipeline.py`, déployé en Docker Compose sur le VPS, déclenché par `airflow dags trigger` ou le scheduler. |
| [n8n](https://n8n.io/) | Orchestration de l'**ingestion** (3 workflows, 1 par domaine) + 7 workflows transverses (housekeeping, sauvegarde, RGPD, reverse-ETL planifié...). | Low-code, event-driven, déjà en place depuis le Projet 18 — pas de raison de dupliquer un deuxième orchestrateur pour l'ingestion alors qu'Airflow gère la transformation. | Import JSON sur le canvas, déclenchement Schedule Trigger + nœud SSH qui appelle le script sur le VPS ; activation réelle via `POST /rest/workflows/{id}/activate`. |

## Infrastructure & déploiement

| Outil | Tâche | Pourquoi ce choix | Comment |
|---|---|---|---|
| [Docker](https://www.docker.com/) / Docker Compose | Conteneurise toutes les sources, l'entrepôt, l'ingestion, Airflow, pgHero. | Isolation par service, reproductible d'un poste à l'autre et sur le VPS ; le VPS n'a nativement ni `psycopg2` ni `openpyxl`. | Un `docker-compose.yml` par service/domaine. |
| [Coolify](https://coolify.io/) | PaaS auto-hébergé qui gère le routage HTTPS des services managés (n8n, Metabase) sur le VPS. | Déjà en place depuis le Projet 18 — réutilise l'infra existante plutôt que d'ouvrir un nouveau compte cloud. | Airflow, déployé hors du catalogue Coolify (pas de template disponible), a dû reproduire son routage Traefik manuellement. |
| [Traefik](https://traefik.io/) | Reverse proxy HTTPS devant les services exposés publiquement. | Le proxy que Coolify pilote nativement — cohérence avec l'infra existante. | Labels Traefik ajoutés à la main sur `airflow-webserver` (pattern copié depuis les labels réels de n8n via `docker inspect`) car Airflow n'est pas géré par Coolify. |
| [Let's Encrypt](https://letsencrypt.org/) | Certificats TLS des services exposés. | Gratuit, automatisé via Traefik (`certresolver`). | Vérifié en vérification **stricte** du certificat (sans `-k`), pas juste "servi en HTTPS". |

## Mock API (Marketing)

| Outil | Tâche | Pourquoi ce choix | Comment |
|---|---|---|---|
| [Flask](https://flask.palletsprojects.com/) | Mock de l'API SaaS Marketing (OAuth2, polling paginé, webhook push, reverse-ETL). | Framework minimal suffisant pour simuler 4 mécanismes réels sans le poids d'un framework plus lourd. | `domaines/marketing-activite/saas-mock/`, conteneurisé, jetons OAuth2 courts (30 s) pour forcer un vrai cycle de refresh vérifiable. |

## Qualité, gouvernance, monitoring

| Outil | Tâche | Pourquoi ce choix | Comment |
|---|---|---|---|
| [pgHero](https://github.com/ankane/pghero) | Tableau de bord de monitoring Postgres (requêtes lentes, index, espace). | Léger, auto-hébergeable, gratuit — face à pganalyze (payant, comparé sur documentation seulement, jamais souscrit). | `docs/housekeeping/docker-compose.yml`, connecté via le rôle `dbt_transform`. A détecté lui-même que `pg_stat_statements` n'est pas activé — une vraie limite constatée, pas supposée. |
| Script maison (`docs/housekeeping/script_maison.py`) | Détection d'index inutilisés et de fragmentation sur les 3 bases réelles (Postgres, SQL Server, MySQL). | Aucun outil du marché ne couvre à lui seul les 3 technologies du projet — pgHero et pganalyze sont Postgres-only. | Requêtes système par moteur (`pg_stat_user_indexes`, `sys.dm_db_index_usage_stats`, `information_schema`), filtrées pour exclure les objets système et les clés primaires (2 faux positifs réels corrigés avant publication). |
| [Filiation](https://github.com/valentinratigniet-byte/projet-14-filiation) (outil maison, Projet 14) | Lignage inter-systèmes navigable, jusqu'à la donnée brute. | Le lignage dbt seul est exact mais lu par des data engineers — Filiation répond à "d'où vient ce chiffre ?" pour un public plus large. | `scan_database.py --merge` (additif, lecture seule) via tunnel SSH éphémère — jamais `extract_filiation.py --target` (destructif pour un système tiers). |
| [Factur-X](https://fnfe-mpe.org/factur-x/) (norme, pas un outil) | Format des factures fournisseurs structurées (Finance/Compta). | Norme française de facturation électronique (EN 16931/UBL/CII) — anticipe la réforme B2B PDP/PPF plutôt qu'un CSV inventé. | Simulée en XML structuré pour les fournisseurs migrés + texte OCR-like dégradé pour les non-migrés, taux de migration croissant 20 %→65 % sur 8 mois. |

## BI

| Outil | Tâche | Pourquoi ce choix | Comment |
|---|---|---|---|
| [Power BI](https://powerbi.microsoft.com/) | Restitution décisionnelle, modèles connectés à `marts`. | Déjà l'outil BI standard des autres projets du portfolio (09, 13) — cohérence de compétence démontrée. | Connexion directe sur le schéma `marts`, RLS déjà appliquée côté entrepôt. |
| [Metabase](https://www.metabase.com/) | Deuxième outil de restitution, léger, auto-hébergé. | Gratuit, auto-hébergeable sur le VPS déjà en place (Projet 18) — donne un second point de vue BI sans licence. | Connecté au même schéma `marts` via Coolify. |

## CI/CD

| Outil | Tâche | Pourquoi ce choix | Comment |
|---|---|---|---|
| [GitHub Actions](https://github.com/features/actions) | Rejoue en CI le pipeline réellement déployé : entrepôt + 3 sources réelles + génération des données synthétiques + dbt. | Intégré au dépôt, gratuit pour un repo public — pas de simulation partielle : les mêmes conteneurs qu'en production. | `.github/workflows/ci.yml`, mots de passe placeholders valables uniquement le temps du run. |
| [gh CLI](https://cli.github.com/) | Création de la deploy key scopée pour le refresh automatisé de Filiation. | `gh repo deploy-key add --allow-write` scope l'accès en écriture au seul repo `projet-14-filiation`, jamais un token compte entier. | Utilisé une fois pour provisionner la clé, jamais dans le pipeline lui-même. |

## Règles transverses (s'appliquent quel que soit l'outil)

Ces règles ne sont pas propres à un outil — elles ont toutes été *découvertes* en construisant (un bug réel les a motivées), pas décidées à l'avance par principe.

1. **Un adaptateur par type de source, jamais par domaine.** `fichier_plat.py`, `sqlserver.py`, `mysql.py`... sont réutilisés tels quels sur les 3 domaines. Ajouter un domaine ne réécrit jamais un adaptateur existant.
2. **Lecture seule sur toute source externe, sans exception.** AS/400, SQL Server (l'ERP), MySQL, l'API SaaS : jamais un `INSERT`/`UPDATE` depuis le pipeline. Toute correction repart vers le système source lui-même, jamais en douce depuis l'entrepôt.
3. **Une donnée douteuse est flaguée, jamais corrigée ou fusionnée en silence.** Doublons clients, mojibake MySQL, SIREN invalide, dérive de format de date : une colonne booléenne rend le problème visible, la décision de correction reste humaine.
4. **Idempotence vérifiée en relançant, pas supposée.** Tout script d'ingestion est testé une 2ᵉ fois avant d'être considéré fini — la plupart des bugs d'ETL ne se voient qu'au deuxième passage.
5. **Historiser avant de nettoyer.** Le snapshot SCD2 tourne sur la donnée la plus brute possible, jamais après le staging — sinon l'historique capture une donnée déjà corrigée, pas la réalité de la source.
6. **RLS posée en `post_hook` du modèle dbt, jamais dans un script séparé.** Un modèle `table` fait DROP+CREATE à chaque `dbt run` ; un grant/policy posé à part est silencieusement effacé au run suivant.
7. **RLS vérifiée par `SET ROLE` + lecture réelle, jamais par simple lecture des policies déclarées.** Une policy mal écrite peut exister sans filtrer quoi que ce soit.
8. **Moindre privilège partout.** Rôles applicatifs scopés (`ingestion` ne peut pas créer de schéma, `dbt_transform` ne peut pas lire les tables d'un autre rôle sans `FOR ROLE` explicite), jamais de superuser/`Owner` par défaut.
9. **Secrets jamais commités.** Écrits directement sur le serveur (VPS) ou en variables d'environnement CI, `.env.example` documente seulement la forme attendue.
10. **Un chiffre publié est un chiffre remesuré, pas recopié.** Deux erreurs de mesure historiques (taux de mojibake, taux SIREN invalide) ont été trouvées en revérifiant contre la vraie donnée plutôt qu'en faisant confiance à une doc précédente — désormais systématique avant toute publication de résultat.
