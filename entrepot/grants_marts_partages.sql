-- A rejouer UNE FOIS apres le tout premier "dbt run" reussi -- pas dans
-- init/ (docker-entrypoint-initdb.d) car le schema marts n'existe pas
-- encore au premier demarrage du conteneur, il est cree par dbt.
--
-- Piege reel decouvert en reconstruisant le pipeline de zero (CI) : les
-- roles partages RH/Finance/Direction (entrepot/init/03_roles_partages.sql)
-- et role_commercial (domaines/ventes-commerce/rls.sql) recoivent bien un
-- GRANT SELECT sur chaque table via les post_hook des modeles marts, mais
-- jamais le GRANT USAGE ON SCHEMA marts qui conditionne l'acces meme a ces
-- tables -- sans lui, SET ROLE + SELECT echoue "permission denied for
-- schema marts" avant meme d'evaluer une policy RLS. Fait manuellement sur
-- le serveur a l'epoque (pas remonte dans un script), invisible tant que
-- personne ne reconstruit le pipeline depuis un entrepot vierge.

GRANT USAGE ON SCHEMA marts TO role_rh, role_finance, role_direction, role_commercial, role_support;
