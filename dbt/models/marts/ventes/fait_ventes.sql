{#
  Grain : une ligne = une commande (stg_ventes_commandes). Remise
  appliquee quand un rapprochement client fiable existe (dim_client,
  score >= 0.5) -- sinon montant net = montant HT, pas de remise inventee.

  RLS en post_hook (meme raison que dim_client.sql) : role_commercial ne
  voit pas les commandes ANNULEE (vue operationnelle), role_rh aucun
  acces, role_finance/role_direction tout (reconciliation budgetaire).
#}

{{
    config(
        post_hook=[
            "ALTER TABLE {{ this }} ENABLE ROW LEVEL SECURITY",
            "GRANT SELECT ON {{ this }} TO role_rh, role_finance, role_direction, role_commercial",
            "DROP POLICY IF EXISTS rh_aucun_acces ON {{ this }}",
            "CREATE POLICY rh_aucun_acces ON {{ this }} FOR SELECT TO role_rh USING (false)",
            "DROP POLICY IF EXISTS finance_direction_complet ON {{ this }}",
            "CREATE POLICY finance_direction_complet ON {{ this }} FOR SELECT TO role_finance, role_direction USING (true)",
            "DROP POLICY IF EXISTS commercial_actives ON {{ this }}",
            "CREATE POLICY commercial_actives ON {{ this }} FOR SELECT TO role_commercial USING (statut <> 'ANNULEE')",
        ]
    )
}}

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
