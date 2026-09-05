-- Un test dbt echoue si cette requete retourne des lignes.
-- Verifie que le nombre d'envois rapporte par l'API SaaS correspond au
-- comptage independant depuis MySQL -- deux sources, meme evenements
-- reels, doivent converger.
select campagne_id, envoyes, envoyes_calcules
from {{ ref('fait_performance_campagnes') }}
where not coherent_avec_mysql
