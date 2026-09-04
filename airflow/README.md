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
- `../dbt/` monté en volume dans les conteneurs — le DAG de production
  (raw → snapshots → staging → marts → tests → slim CI) lira le projet dbt
  directement depuis là, une fois qu'il existera (Phase 2+).

## État actuel

`dags/healthcheck.py` — DAG minimal qui vérifie qu'Airflow tourne et que
`/opt/dbt` est monté. **À remplacer par le vrai DAG dbt dès la Phase 2** —
ce n'est pas un DAG de production, seulement la preuve que l'infra
fonctionne.
