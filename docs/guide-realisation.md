# Guide de réalisation

Écrit au fil de la construction réelle — chaque section correspond à ce
qui a été fait, vérifié, et fonctionne. Pas un plan à l'avance (ça, c'est
l'[issue #2](https://github.com/valentinratigniet-byte/valentinratigniet-byte/issues/2)).

## Phase 1 — Infra partagée : Airflow

**Objectif** : orchestrer le futur pipeline dbt (raw → snapshots → staging
→ marts → tests → slim CI) sans ajouter de charge inutile sur un VPS à
2 vCPU.

**Ce qui a été fait** :
1. Stack Airflow minimale — `LocalExecutor`, pas de Celery/Redis/workers
   (inutile pour ce volume, et le VPS n'a que 2 vCPU). Metadata DB dédiée
   (Postgres léger, séparée de l'entrepôt).
2. Déployée sur le VPS existant (`/opt/projet19/airflow/`), pas via le
   catalogue "1-clic" de Coolify (pas de template Airflow disponible) —
   `docker compose` direct, secrets réels écrits directement sur le
   serveur via SFTP (jamais commités, `.env.example` documente juste la
   forme attendue).
3. Webserver exposé uniquement sur `127.0.0.1:8090` pour l'instant — pas
   encore de routage public HTTPS via Traefik/Coolify. Volontairement
   séparé : vérifier que le service tourne avant de l'exposer.

**Vérifié, pas juste "up"** :
- `docker ps` → `airflow-webserver` et `airflow-postgres` healthy,
  `airflow-scheduler` opérationnel.
- `curl http://127.0.0.1:8090/health` → `HTTP 200`.
- `airflow dags list` → le DAG `healthcheck` détecté.
- DAG `healthcheck` déclenché manuellement → **state: success** — confirme
  que le conteneur peut bien lire `/opt/dbt` (volume monté), pas juste que
  le webserver répond.

**Routage HTTPS public — fait juste après, même session** :

Airflow n'a pas été déployé via le catalogue Coolify (pas de template
disponible), donc `coolify-proxy` (Traefik) ne rejoint pas automatiquement
son réseau comme il le fait pour les ressources gérées par Coolify
(n8n, Metabase). Reproduit le même schéma manuellement :
1. Labels Traefik ajoutés sur `airflow-webserver` dans le
   `docker-compose.yml` (routers http→https redirect + https avec
   `certresolver: letsencrypt`), en copiant exactement le pattern déjà
   utilisé par le n8n du Projet 18 (`docker inspect` sur le conteneur n8n
   pour lire ses labels réels plutôt que deviner).
2. `docker network connect airflow_default coolify-proxy` — attache
   manuellement le proxy au réseau d'Airflow (Coolify le fait
   automatiquement pour ses propres ressources, pas pour celle-ci).
3. `docker compose up -d airflow-webserver` pour recréer le conteneur avec
   les nouveaux labels.

**Vérifié** : `http://airflow-projet19.76.13.43.130.sslip.io/health` →
`302` (redirection vers HTTPS) ; `https://.../health` → `200`, avec
vérification **stricte** du certificat (pas de `-k`) qui passe — donc un
vrai certificat Let's Encrypt valide, pas juste servi en HTTPS auto-signé.
Fonctionné du premier coup, contrairement au Projet 18 où l'équivalent
avait demandé un contournement via la base Coolify — différence : ici
c'est une ressource neuve avec labels corrects dès le départ, pas une
ressource existante mal configurée à corriger après coup.

**Pas encore fait à l'issue de la Phase 1** : le vrai DAG de production
(remplace `healthcheck.py`).

## Phase 2 — Domaine Ventes/Commerce (en cours)

**Simulateurs d'usage** — deux sources écrites et vérifiées :
- `domaines/ventes-commerce/source/simulateur_as400.py` : 8 mois de
  fichiers plats à largeur fixe (clients + commandes), conventions AS/400.
  Défauts confirmés dans le contenu généré (pas juste documentés) :
  dérive de format de date sur 2 mois, doublons clients, statuts de
  commande orthographiés de façon incohérente, ~3% de commandes avec
  `CLICOD` orphelin. Auto-check : largeur de ligne fixe respectée sur tous
  les fichiers.
- `domaines/ventes-commerce/source/simulateur_excel_remises.py` : 2
  fichiers Excel concurrents (`v3`, `v4_FINAL`), remises qui divergent
  réellement entre les deux pour les mêmes clients, une formule cassée
  (`#REF!`).
- Fichiers générés non commités (`.gitignore`) — déterministes (seed
  fixe), régénérés à la demande par les scripts.

**Entrepôt Postgres déployé et vérifié** :
- `entrepot/docker-compose.yml` — Postgres auto-hébergé sur le VPS
  (`/opt/projet19/entrepot/`), même schéma que le déploiement Airflow
  (secrets écrits directement sur le serveur, jamais commités).
- Vérifié : schéma `raw` créé (`\dn`), rôles `ingestion` et
  `dbt_transform` créés sans privilège superuser (`\du`), réseau
  `entrepot_default` connecté à Airflow (scheduler + webserver) et à n8n
  pour un accès par nom de conteneur.

**Adaptateurs d'ingestion écrits, conteneurisés et vérifiés** :
- `ingestion/adaptateurs/` — fichier plat (largeur fixe), Excel, écriture
  Postgres générique. Un par TYPE de source, réutilisables par les autres
  domaines (doctrine du cadrage), pas réécrits par domaine.
- `domaines/ventes-commerce/ingestion.py` — orchestration spécifique au
  domaine (quel spec, quelle table `raw`, remplacement vs ajout).
- Host du VPS sans psycopg2/openpyxl → conteneurisé (`ingestion/Dockerfile`,
  image `projet19-ingestion`, 216 Mo), pas d'installation système.
- 2 bugs réels rencontrés et corrigés pendant le build (pas anticipés à
  l'avance) : (1) le rôle `ingestion` n'a pas le droit de `CREATE SCHEMA`
  (seulement des tables dans un schéma existant) — corrigé en retirant
  cette instruction, le schéma `raw` est déjà créé par l'entrepôt ;
  (2) un en-tête Excel saisi à la main (`"Remise (%)"`) contient un `%`
  qui casse le parsing SQL de `psycopg2.extras.execute_values` — corrigé
  en sanitisant les noms de colonnes (pas les valeurs) avant de les
  utiliser comme identifiants SQL.
- **Vérifié réellement** (pas juste "exit 0") : `raw.ventes_clients`
  314 lignes, `raw.ventes_commandes` 2320 lignes (= somme exacte des 8
  mois simulés), `raw.ventes_remises` 25 lignes (9 de v3 + 16 de v4,
  cohérent) — et un `SELECT` direct confirme les doublons clients
  (`CL9xxxxx`, 14 lignes) et le `_source_file` bien tracé par ligne.

**dbt — snapshots + staging écrits et vérifiés** (exécuté via l'image
officielle `ghcr.io/dbt-labs/dbt-postgres:1.8.latest`, pas d'image maison) :
- `snapshots/ventes_clients_snapshot.sql` — SCD type 2 (stratégie `check`,
  pas `timestamp` : l'AS/400 ne fournit pas de colonne de dernière
  modification fiable) sur `raw.ventes_clients`.
- `models/staging/ventes/` — 3 modèles avec de vraies règles de nettoyage,
  pas des exemples pédagogiques : `stg_ventes_clients` (doublons probables
  flagués via nom normalisé, pas supprimés), `stg_ventes_commandes`
  (détection du format de date YYYYMMDD vs DDMMYYYY, statuts regroupés
  par préfixe, centimes→euros, FK partielle flaguée via `client_connu`),
  `stg_ventes_remises` (réconciliation v3/v4 par version + date
  d'ingestion, formule Excel cassée détectée et exclue sans planter).
- **9/9 tests dbt passent**, dont un test singulier
  (`assert_montant_ht_coherent`, vérifie `montant = qté × prix`).

**3 vrais bugs rencontrés et corrigés** (pas anticipés à l'avance) :
1. Colonnes brutes créées avec identifiants cités en majuscules
  (`"CLICOD"`) — le snapshot dbt les référençait sans guillemets, Postgres
  les cherchait en minuscules → `column does not exist`. Corrigé en
  citant les colonnes dans la config du snapshot.
2. `ALTER DEFAULT PRIVILEGES` ne s'applique qu'aux objets créés PAR le
  rôle qui exécute la commande — les tables `raw` sont créées par
  `ingestion`, pas par `postgres` → `dbt_transform` ne pouvait pas les
  lire. Corrigé avec la variante `FOR ROLE ingestion`.
3. Le snapshot tentait d'écrire dans le schéma `raw` (possédé par
  `ingestion`, lecture seule pour `dbt_transform`) → `permission denied`.
  Corrigé en déplaçant `target_schema` vers `raw_historise`, un schéma
  que `dbt_transform` possède — garde la séparation des privilèges
  ingestion/transformation plutôt que d'élargir les droits.

**Idempotence vérifiée** : un 2e `dbt snapshot` sans changement de donnée
→ `INSERT 0 0` (aucune ligne dupliquée), confirme que le mécanisme SCD2
fonctionne réellement, pas juste "la commande s'exécute sans erreur".

**Marts écrits et vérifiés — `dim_client` + `fait_ventes`** :
- Rapprochement flou nom Excel (saisi à la main) → CLINOM AS/400 via
  `pg_trgm` (similarité de trigrammes) plutôt qu'un simple `=` — les noms
  ne matchent jamais exactement entre les deux sources.
- **Vrai problème de qualité trouvé et corrigé** : au seuil 0.4, deux faux
  positifs réels (`Legendre SARL` et `Lesage S.A.R.L.` matchaient tous les
  deux sur `Lefèvre Sarl`, le suffixe juridique commun gonflant le score)
  — remonté à 0.5 pour les exclure. **Résultat final : seulement 3 des 16
  remises Excel se rattachent avec confiance à un client AS/400** — la
  majorité des remises négociées ne peut pas être automatiquement
  réconciliée sans revue humaine. Un vrai résultat, pas la conclusion
  espérée, gardé tel quel.
- `fait_ventes` : grain = une commande, `montant_net_eur` calculé avec la
  remise rapprochée quand elle existe, sinon = montant HT (pas de remise
  inventée). 2320 lignes, cohérent avec le staging.
- Schémas dbt renommés `staging`/`marts` (au lieu de `raw_staging`/
  `raw_marts`, comportement par défaut de dbt qui concatène le schéma du
  profil) via un override `generate_schema_name` — cohérent avec la
  terminologie du cadrage.
- **14/14 tests dbt passent** (5 nouveaux sur les marts).

**RLS multi-rôles écrite et VÉRIFIÉE par `SET ROLE`** (`domaines/ventes-commerce/rls.sql` + `test_rls.py`, même discipline que le Projet 18) :
- `role_rh` — aucun accès (0 ligne sur les 2 tables, pas de justification
  métier à voir la donnée commerciale).
- `role_finance` / `role_direction` — accès complet (2320/314 lignes,
  y compris les commandes annulées, nécessaires pour la réconciliation
  budgétaire et le pilotage).
- `role_commercial` — commandes actives uniquement, `statut <> 'ANNULEE'`
  (2052/2320 lignes) — vue opérationnelle, les annulations ne relèvent
  pas du quotidien commercial.
- **8/8 cas vérifiés réellement** par `SET ROLE` + comptage, pas
  seulement policies déclarées.

**2 vrais pièges supplémentaires rencontrés et corrigés en finissant la Phase 2** :

1. **Idempotence de l'ingestion** — en testant le script qui sera appelé
   par n8n, je l'ai relancé une 2e fois : `raw.ventes_commandes` a
   doublé (4640 lignes au lieu de 2320), parce que `ajouter_lignes`
   réinjectait tous les fichiers à chaque exécution, pas seulement les
   nouveaux. Corrigé avec une table manifeste `raw._fichiers_ingeres`
   (table cible + nom de fichier) — un fichier déjà ingéré est sauté,
   pas ré-ajouté. Vérifié : 2 exécutions consécutives → 2320 lignes les
   deux fois (la 2e n'ajoute rien, correctement).
2. **RLS qui disparaît à chaque `dbt run`** — un modèle dbt matérialisé
   en `table` fait un `DROP` + `CREATE` à chaque exécution : les
   `GRANT`/policies RLS posés à part (script séparé) étaient donc
   effacés au run suivant. Découvert en relançant `dbt run` après avoir
   vérifié la RLS une première fois — le 2e test échouait
   (`permission denied`). Corrigé en déplaçant grants + policies dans un
   `post_hook` du modèle dbt lui-même (`config(post_hook=[...])`,
   idempotent via `DROP POLICY IF EXISTS` avant chaque `CREATE POLICY`)
   — réappliqué automatiquement à chaque run, pas un script qu'on oublie
   de rejouer. **Vérifié sur 2 runs consécutifs, 8/8 cas RLS OK les deux
   fois.**

**Workflow n8n** — export JSON prêt (`n8n/ventes-commerce-ingestion-workflow.json`,
Schedule Trigger quotidien 2h + noeud SSH qui appelle
`run_ingestion.sh` sur le VPS, secret hors du JSON). **Import dans n8n et
configuration de la credential SSH restent une étape manuelle** — comme
pour le déploiement initial de n8n au Projet 18, pas automatisable sans
clé API n8n déjà en main.

**Reste réellement ouvert** : `decisions.md`/`regles-transformation.md`/
`avant.md`/`apres.md` (documentation à écrire), import manuel du workflow
n8n.
