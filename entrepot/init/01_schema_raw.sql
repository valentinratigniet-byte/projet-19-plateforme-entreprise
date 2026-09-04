-- Execute une seule fois, au premier demarrage du conteneur (docker-entrypoint-initdb.d).
-- Schema brut (bronze) : copie 1:1 des sources, aucune transformation.
CREATE SCHEMA IF NOT EXISTS raw;

-- Role d'ingestion a privilege minimal -- pas de superuser pour n8n/adaptateurs,
-- coherent avec la doctrine "connectique propre" du cadrage (issue #2).
-- __INGESTION_PASSWORD__ / __DBT_PASSWORD__ substitues au deploiement,
-- jamais commites en clair (meme pattern que airflow/.env).
CREATE ROLE ingestion WITH LOGIN PASSWORD '__INGESTION_PASSWORD__';
GRANT USAGE, CREATE ON SCHEMA raw TO ingestion;
ALTER DEFAULT PRIVILEGES IN SCHEMA raw GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO ingestion;

-- Role dbt (transforme raw -> staging/marts) -- separe du role d'ingestion,
-- lecture seule sur raw, ecriture sur les schemas qu'il cree lui-meme.
CREATE ROLE dbt_transform WITH LOGIN PASSWORD '__DBT_PASSWORD__';
GRANT USAGE ON SCHEMA raw TO dbt_transform;
ALTER DEFAULT PRIVILEGES IN SCHEMA raw GRANT SELECT ON TABLES TO dbt_transform;
GRANT CREATE ON DATABASE projet19 TO dbt_transform;
