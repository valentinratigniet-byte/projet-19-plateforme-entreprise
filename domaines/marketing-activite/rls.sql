-- Role operationnel specifique au domaine Marketing/Activite (roles
-- partages RH/Finance/Direction crees au niveau entrepot, cf.
-- entrepot/init/03_roles_partages.sql).
--
-- Grants/policies eux-memes dans les post_hook des modeles marts
-- concernes (meme raison qu'aux autres domaines : DROP+CREATE a chaque
-- dbt run sur un modele `table`).
CREATE ROLE role_marketing NOLOGIN;
GRANT USAGE ON SCHEMA marts TO role_marketing;
