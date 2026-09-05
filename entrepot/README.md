# Entrepôt

**✅ Constellation opérationnelle** — Postgres auto-hébergé sur le VPS
(`docker compose`, hors catalogue Coolify — pas de Supabase séparé,
décision coût 0€, cf. [issue #2](https://github.com/valentinratigniet-byte/valentinratigniet-byte/issues/2)).

## État actuel

- Base `projet19`, 5 schémas : `raw` (brut, copie 1:1, owner `ingestion`),
  `raw_historise` (snapshots dbt SCD2), `staging` (nettoyage documenté),
  `marts` (business-ready, owner `dbt_transform`), `public` (par défaut,
  inutilisé).
- **Modèle constellation réel** : `marts.dim_date` partagée entre les 3
  domaines (`fait_ventes`, `fait_ecritures`, `fait_envois` s'y rattachent
  tous par valeur de date) — pas 3 étoiles isolées.
- **Marts transverses** (`marts.ecart_budget_ventes`,
  `marts.synthese_mensuelle_transverse`) — cf.
  [`docs/analyse-transverse.md`](../docs/analyse-transverse.md).
- Rôles à privilège minimal, pas de superuser côté applicatif :
  `ingestion` (écrit `raw`), `dbt_transform` (lit `raw`, possède
  `staging`/`marts`/`raw_historise`), + rôles RLS
  `role_rh`/`role_finance`/`role_direction`/`role_commercial`/
  `role_marketing` (NOLOGIN, cf. `entrepot/init/03_roles_partages.sql`
  et `domaines/*/rls.sql`).
- Réseau Docker `entrepot_default` — Airflow, n8n, SQL Server, MySQL et le
  mock SaaS y sont tous connectés (atteignables par nom de conteneur).
- Port `127.0.0.1:5440` ouvert sur le VPS pour un accès admin ponctuel
  (tunnel SSH), pas exposé publiquement.

## Dictionnaire de données

Généré via `dbt docs generate` — catalogue complet (24 modèles, 3
snapshots, 51 tests, 12 sources) + graphe de lineage. Vérifié
fonctionnel, alimente cette section (pas de duplication manuelle du
dictionnaire).

## Déploiement

```bash
cp .env.example .env   # remplir avec de vraies valeurs, jamais commit
docker compose up -d
```

`init/01_schema_raw.sql` + `init/02_extensions.sql` (pg_trgm) +
`init/03_roles_partages.sql` s'exécutent au premier démarrage — les
placeholders de mot de passe doivent être substitués avant le premier
lancement (jamais commités en clair).

Deux couches, cf. [README principal](../README.md) : `raw` (brut, copie
1:1) et constellation (net, marts dbt).
