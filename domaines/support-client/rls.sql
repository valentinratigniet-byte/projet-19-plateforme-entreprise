-- Role operationnel specifique au domaine Support Client (meme principe
-- que role_commercial/role_marketing) -- les roles partages RH/Finance/
-- Direction sont crees une fois au niveau entrepot
-- (cf. entrepot/init/03_roles_partages.sql).
--
-- GRANT/ENABLE RLS/CREATE POLICY posés en post_hook du mart concerné
-- (dbt/models/marts/support-client/fait_tickets.sql), pas ici -- un
-- modèle `table` fait DROP+CREATE à chaque run, ce qui efface tout
-- grant/policy pose a part (piège déjà rencontré sur Ventes/Finance).

CREATE ROLE role_support NOLOGIN;
