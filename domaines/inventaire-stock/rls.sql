-- Role operationnel specifique au domaine Inventaire/Stock (meme principe
-- que role_commercial/role_support) -- les roles partages RH/Finance/
-- Direction sont crees une fois au niveau entrepot
-- (cf. entrepot/init/03_roles_partages.sql).
--
-- GRANT/ENABLE RLS/CREATE POLICY poses en post_hook des marts concernes
-- (dbt/models/marts/inventaire-stock/dim_stock_articles.sql,
-- fait_mouvements_stock.sql), pas ici -- un modele `table` fait
-- DROP+CREATE a chaque run, ce qui efface tout grant/policy pose a part.

CREATE ROLE role_stock NOLOGIN;
