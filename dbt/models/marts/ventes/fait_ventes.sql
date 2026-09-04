{#
  Grain : une ligne = une commande (stg_ventes_commandes). Remise
  appliquee quand un rapprochement client fiable existe (dim_client,
  score >= 0.4) -- sinon montant net = montant HT, pas de remise inventee.
#}

with commandes as (

    select * from {{ ref('stg_ventes_commandes') }}

),

clients as (

    select * from {{ ref('dim_client') }}

)

select
    cmd.cmdnum,
    cmd.clicod,
    cmd.date_commande,
    cmd.artcod,
    cmd.qte_commandee,
    cmd.prix_unitaire_eur,
    cmd.montant_ht_eur,
    cl.remise_pct,
    round(cmd.montant_ht_eur * (1 - coalesce(cl.remise_pct, 0) / 100.0), 2) as montant_net_eur,
    cmd.statut,
    cmd.client_connu,
    cmd._source_file,
    cmd._ingested_at

from commandes cmd
left join clients cl on cmd.clicod = cl.clicod
