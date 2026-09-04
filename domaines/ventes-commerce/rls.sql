-- Role operationnel specifique au domaine Ventes/Commerce (les roles
-- partages RH/Finance/Direction sont crees une fois au niveau entrepot,
-- cf. entrepot/init/03_roles_partages.sql).
--
-- Les GRANT/ENABLE RLS/CREATE POLICY eux-memes ne vivent PAS ici : un
-- `dbt run` sur un modele materialise en `table` fait un DROP+CREATE de
-- la table a chaque execution, ce qui efface policies et grants s'ils
-- sont poses a part. Ils sont donc dans un post_hook des modeles marts
-- concernes (dbt/models/marts/ventes/dim_client.sql, fait_ventes.sql) --
-- reappliques automatiquement a chaque run, pas un script qu'on oublie
-- de rejouer. Piege reel rencontre et documente dans
-- docs/guide-realisation.md.

CREATE ROLE role_commercial NOLOGIN;
