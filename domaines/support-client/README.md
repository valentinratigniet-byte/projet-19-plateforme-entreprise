# Domaine Support Client

**✅ 4ᵉ domaine, ajouté après les 3 premiers** — premier domaine sur un
document store, pas une base relationnelle. Sert un objectif précis :
prouver que l'architecture (raw → staging → marts, RLS, dbt) tient face
à une source réellement hétérogène, pas seulement "un 4ᵉ SGBD SQL de plus".

Source : MongoDB (tickets SAV, JSON imbriqué). Aucun export batch, aucune
table à colonnes fixes — un document par ticket, avec un tableau de
messages imbriqué et un schéma qui **dérive dans le temps** (comportement
propre à un document store, absent des 3 domaines relationnels).

## Ce qui est construit et vérifié

- **`source/`** — `simulateur_mongodb.py` génère 25 mois de tickets SAV
  vécus, avec 3 défauts réels injectés :
  - **dérive de schéma** — les tickets les plus anciens utilisent
    `customer_ref`, les récents `client_id` (migration jamais
    rétro-appliquée aux documents déjà créés — MongoDB ne force aucun
    schéma, rien n'empêche les deux formes de coexister indéfiniment) ;
  - **référence de commande parfois orpheline** (~8 % des tickets, client
    qui se trompe de numéro) ;
  - **couverture d'enquête de satisfaction partielle** (~35 % des tickets
    résolus seulement — un vrai taux de réponse, pas 100 %).
- **Ingestion** → `raw.support_tickets` — chaque document transporté **tel
  quel** dans une colonne JSON (`remplacer_table`, aucun aplatissement à
  l'ingestion : un document store ne garantit pas de schéma fixe à
  aplatir). Frontière réelle ETL/dbt : dbt n'a pas d'adaptateur MongoDB
  officiel (SQL-only, confirmé) — l'aplatissement JSON (`::jsonb`, `->>`)
  se fait donc en **staging dbt**, pas avant.
- **dbt** — 1 modèle staging (`stg_support_tickets`, coalesce
  `client_id`/`customer_ref`), 1 mart (`fait_tickets`, délai de
  résolution calculé) — **7/7 tests passent**.
- **RLS** — `role_support` (opérationnel) + `role_direction`
  (supervision) uniquement ; `role_rh`/`role_finance`/`role_commercial`
  n'ont aucun usage métier sur des tickets SAV, pas de `GRANT SELECT` —
  **5/5 cas vérifiés** par `SET ROLE` réel (accès refusé = erreur
  `permission denied`, pas une policy RLS qui renvoie 0 ligne : aucun
  grant posé pour ces rôles, pas de raison d'en accorder un pour ensuite
  le retirer par policy).
- **Ressources contenues** — `mem_limit: 512m` sur le conteneur MongoDB,
  cache WiredTiger plafonné à 0,25 Go (`--wiredTigerCacheSizeGB`) : sans
  ce plafond explicite, MongoDB dimensionne son cache à 50 % de la RAM
  *de l'hôte* par défaut, un calcul faux sur un VPS qui héberge déjà
  SQL Server/MySQL/Postgres/Airflow/n8n.

## 🗂️ Structure

```
domaines/support-client/
├── README.md
├── ingestion.py              ← orchestration (MongoDB -> raw.support_tickets)
├── rls.sql                   ← role_support (opérationnel)
├── test_rls.py               ← preuve RLS : SET ROLE, 5 cas vérifiés
├── run_ingestion.sh.example  ← wrapper appelé par n8n (secret hors du JSON)
└── source/
    ├── docker-compose.yml    ← MongoDB, mem_limit 512m
    ├── .env.example
    └── simulateur_mongodb.py ← 25 mois de tickets, dérive de schéma incluse
```

## 🚀 Reproduire

```bash
cd source && docker compose up -d --wait
export MONGO_HOST=localhost MONGO_PORT=27017 MONGO_ROOT_PASSWORD=<mot de passe>
python simulateur_mongodb.py
cd ..
export PYTHONPATH=../../ingestion PGHOST=localhost PGPORT=5440 PGUSER=ingestion PGPASSWORD=<mot de passe>
python ingestion.py
cd ../../dbt && dbt run --select path:models/staging/support-client path:models/marts/support-client
dbt test --select path:models/staging/support-client path:models/marts/support-client
```

---

*Domaine du [Projet 19](https://github.com/valentinratigniet-byte/projet-19-plateforme-entreprise).
Détail technique complet (aplatissement JSON, dérive de schéma) dans
[`docs/construction-etl-erp-dbt.md`](../../docs/construction-etl-erp-dbt.md).*
