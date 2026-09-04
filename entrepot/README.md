# Entrepôt

Postgres auto-hébergé sur le VPS existant (`docker compose`, hors
catalogue Coolify — pas de Supabase séparé, décision coût 0€, cf.
[issue #2](https://github.com/valentinratigniet-byte/valentinratigniet-byte/issues/2)).

## État actuel

- Base `projet19`, schéma `raw` créé (copie 1:1 des sources — vide pour
  l'instant, se remplit domaine par domaine).
- Deux rôles à privilège minimal, pas de superuser côté applicatif :
  `ingestion` (écrit dans `raw`, utilisé par les adaptateurs n8n),
  `dbt_transform` (lit `raw`, crée `staging`/`marts`).
- Réseau Docker `entrepot_default` — Airflow et n8n y sont connectés pour
  atteindre `projet19-postgres:5432` par nom de conteneur.
- Port `127.0.0.1:5440` ouvert sur le VPS pour un accès admin ponctuel
  (tunnel SSH), pas exposé publiquement.

## Déploiement

```bash
cp .env.example .env   # remplir avec de vraies valeurs, jamais commit
docker compose up -d
```

`init/01_schema_raw.sql` s'exécute automatiquement au premier démarrage
(mécanisme `docker-entrypoint-initdb.d` de l'image Postgres) — les
placeholders `__INGESTION_PASSWORD__`/`__DBT_PASSWORD__` doivent être
substitués avant le premier lancement (jamais commités en clair).

## À venir

Schémas `staging`/`marts` créés automatiquement par dbt aux prochaines
phases. RLS multi-rôles (RH/Finance/Direction/métier) ajoutée une fois les
premières tables réelles en place (pas de sens à sécuriser des tables
vides).

Deux couches, cf. [README principal](../README.md) : `raw` (brut, copie
1:1) et constellation (net, marts dbt).
