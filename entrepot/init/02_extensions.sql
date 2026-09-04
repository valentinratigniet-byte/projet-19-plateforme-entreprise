-- Necessite superuser -- pg_trgm : similarite de trigrammes, utilisee
-- pour le rapprochement flou nom Excel -> CLINOM AS/400 (dim_client).
CREATE EXTENSION IF NOT EXISTS pg_trgm;
