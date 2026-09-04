-- Un test dbt echoue si cette requete retourne des lignes.
-- Verifie l'identite montant_ht = quantite x prix_unitaire (a 1 centime pres),
-- garde-fou sur la conversion centimes -> euros faite en staging.
select
    cmdnum,
    qte_commandee,
    prix_unitaire_eur,
    montant_ht_eur
from {{ ref('stg_ventes_commandes') }}
where abs(montant_ht_eur - (qte_commandee * prix_unitaire_eur)) > 0.01
