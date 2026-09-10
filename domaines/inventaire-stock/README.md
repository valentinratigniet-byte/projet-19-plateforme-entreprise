# Domaine Inventaire/Stock

**✅ 5ᵉ domaine, ajouté après Support Client** — deuxième source hétérogène
non-SQL-Server/MySQL, mais différemment de MongoDB : pas un document
store, un **SGBD relationnel embarqué**. Firebird est réellement déployé
sur des scanners d'entrepôt et postes de caisse, conçu pour tourner
**sans administrateur dédié** — ça a des conséquences directes sur les
défauts qu'on y trouve réellement (pas de validation temps réel, horodatage
sans fuseau).

Source : Firebird (articles + mouvements de stock). Références les mêmes
codes article que Ventes/Commerce (`ART001`-`ART040`) — format partagé,
pas une clé étrangère garantie entre domaines (même principe que le reste
du projet, chaque domaine reste généré indépendamment).

## Ce qui est construit et vérifié

- **`source/`** — `simulateur_firebird.py` génère ~2 ans de mouvements de
  stock (entrées/sorties/inventaires) pour 40 articles, avec des défauts
  réels de ce type de système :
  - **`TIMESTAMP` sans fuseau** — l'horodatage scanner est stocké tel
    quel, sans conversion (contrairement à `TIMESTAMPTZ` Postgres) ;
  - **~2 % de doublons de scan** (double-scan physique, mesuré à 105
    lignes exactement dupliquées sur 7 807 mouvements) ;
  - **stock négatif possible** (~50 % des articles) — aucune validation
    temps réel côté scanner, une SORTIE peut dépasser le stock connu.
- **Ingestion** → `raw.stock_articles` / `raw.stock_mouvements`
  (`remplacer_table`, état courant complet à chaque run — comme l'AS/400,
  pas de CDC : Firebird n'expose aucun mécanisme de capture de changement
  comparable à SQL Server, et le volume ne le justifie pas). Adaptateur
  Python (`firebird-driver`) : contrairement à pymssql/PyMySQL/
  psycopg2-binary, autonomes, `firebird-driver` s'appuie sur la
  bibliothèque cliente **native** `libfbclient2`, absente d'une image
  Python standard — ajoutée explicitement dans `ingestion/Dockerfile`
  (et dans le runner CI).
- **dbt** — 2 modèles staging (`stg_stock_articles`, `stg_stock_mouvements`
  dédoublonné), 2 marts (`dim_stock_articles` avec flags stock
  négatif/sous seuil, `fait_mouvements_stock`).
- **RLS** — `role_stock` (opérationnel) + `role_direction` (supervision)
  uniquement ; RH/Finance/Commercial n'ont aucun usage métier sur du stock
  physique, vérifié par `SET ROLE` réel dans `test_rls.py`.
- **Ressources contenues** — `mem_limit: 256m` sur le conteneur Firebird,
  même discipline que MongoDB (`support-client`) sur ce VPS déjà chargé.

## 🗂️ Structure

```
domaines/inventaire-stock/
├── README.md
├── ingestion.py              ← orchestration (Firebird -> raw.stock_*)
├── rls.sql                   ← role_stock (opérationnel)
├── test_rls.py               ← preuve RLS : SET ROLE, dim + fait
├── run_ingestion.sh.example  ← wrapper appelé par n8n (secret hors du JSON)
└── source/
    ├── docker-compose.yml    ← Firebird, mem_limit 256m
    ├── .env.example
    └── simulateur_firebird.py ← 40 articles, ~7800 mouvements
```

## 🚀 Reproduire

```bash
cd source && docker compose up -d --wait
export FIREBIRD_HOST=localhost FIREBIRD_PORT=3050 FIREBIRD_ROOT_PASSWORD=<mot de passe>
python simulateur_firebird.py
cd ..
export PYTHONPATH=../../ingestion PGHOST=localhost PGPORT=5440 PGUSER=ingestion PGPASSWORD=<mot de passe>
python ingestion.py
cd ../../dbt && dbt run --select path:models/staging/inventaire-stock path:models/marts/inventaire-stock
dbt test --select path:models/staging/inventaire-stock path:models/marts/inventaire-stock
```

---

*Domaine du [Projet 19](https://github.com/valentinratigniet-byte/projet-19-plateforme-entreprise).
Détail technique complet (bug driver Firebird, TIMESTAMP sans fuseau) dans
[`docs/construction-etl-erp-dbt.md`](../../docs/construction-etl-erp-dbt.md).*
