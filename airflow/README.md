# Airflow — orchestration du pipeline dbt

Stack minimale : `LocalExecutor`, pas de Celery/Redis/workers — le VPS n'a
que 2 vCPU (vérifié le 2026-09-04), pas de quoi justifier une stack
distribuée pour ce volume. Metadata DB dédiée (Postgres léger, séparée de
l'entrepôt).

## Déploiement (VPS)

```bash
cp .env.example .env   # remplir avec de vraies valeurs, jamais commit
docker compose up -d
```

- Webserver exposé uniquement sur `127.0.0.1:8090` pour l'instant (pas
  encore de routage public via Traefik/Coolify — étape suivante,
  volontairement séparée pour vérifier que le service tourne d'abord).
- `../dbt/` monté en volume dans les conteneurs (`/opt/dbt`) — le DAG lit le
  projet dbt directement depuis là.
- Image custom (`Dockerfile`, `apache/airflow:2.10.3-python3.12` +
  `dbt-core`/`dbt-postgres`) plutôt que `_PIP_ADDITIONAL_REQUIREMENTS`
  (réinstallerait à chaque démarrage de conteneur) — même discipline que
  l'image dédiée `projet19-ingestion`.
- Conteneurs connectés au réseau `entrepot_default` (créé par
  `entrepot/docker-compose.yml`) pour joindre `projet19-postgres` par nom
  de service — même pattern que pgHero (`docs/housekeeping/`).

## État actuel

`dags/dbt_pipeline.py` — DAG de production : `dbt seed` → `dbt snapshot`
→ `dbt run` → `dbt test` → `dbt docs generate`, quotidien à 5h UTC (après
les 3 ingestions n8n de 2h/3h/4h). Rôle `dbt_transform` (même mot de passe
que `docs/housekeeping/.env`, `DBT_PASSWORD`) — lecture sur `raw`, écriture
sur les schémas `staging`/`marts` qu'il a lui-même créés.

Remplace le placeholder `healthcheck.py` de la Phase 1 (vérifiait
seulement qu'Airflow tournait et que `/opt/dbt` était monté — supprimé,
son rôle est repris par le vrai DAG).
