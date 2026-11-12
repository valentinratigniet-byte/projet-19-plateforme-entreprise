-- Role de connexion de l'agent IA n8n : lecture seule, herite des droits
-- (et des policies RLS) de role_direction, limite au schema marts.
-- A executer en superuser : docker exec -i projet19-postgres psql -U <superuser> -d projet19 < role_agent_ia.sql
CREATE ROLE agent_ia WITH LOGIN PASSWORD '__AGENT_IA_PASSWORD__' IN ROLE role_direction;
ALTER ROLE agent_ia SET default_transaction_read_only = on;
ALTER ROLE agent_ia SET statement_timeout = '15s';
ALTER ROLE agent_ia SET search_path = marts;
