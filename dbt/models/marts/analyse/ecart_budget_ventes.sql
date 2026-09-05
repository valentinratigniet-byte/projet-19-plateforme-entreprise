{#
  Decomposition Prix/Volume, meme methode que le Projet 15
  (reporting-ecarts-cg), appliquee ici sur les VRAIES donnees Ventes de
  ce projet (marts.fait_ventes) plutot que refaite de zero.

  Budget = hypothese clairement labellisee (dbt seed
  `budget_ventes_2026.csv`, +8%/mois depuis une base de 3500 unites,
  prix cible fixe 255 EUR) -- pas une vraie negociation budgetaire,
  documentee comme telle (meme discipline "mesure pas invente" que le
  Projet 15 : la donnee REELLE compare au budget est mesuree, le budget
  lui-meme est une hypothese assumee, pas fabriquee pour coller au
  resultat).

  Formule (identique Projet 15) :
    ecart_volume = (qte_reelle - qte_budget) * prix_budget
    ecart_prix   = (prix_reel - prix_budget) * qte_reelle
    ecart_total  = ca_reel - ca_budget = ecart_volume + ecart_prix
#}

{{
    config(
        post_hook=[
            "GRANT SELECT ON {{ this }} TO role_finance, role_direction, role_commercial",
        ]
    )
}}

with reel as (

    select
        to_char(date_commande, 'YYYY-MM') as mois,
        sum(qte_commandee)                as qte_reelle,
        sum(montant_ht_eur)               as ca_reel,
        sum(montant_ht_eur) / nullif(sum(qte_commandee), 0) as prix_reel_moyen

    from {{ ref('fait_ventes') }}
    where statut <> 'ANNULEE'
    group by 1

),

budget as (

    select * from {{ ref('budget_ventes_2026') }}

),

rapproche as (

    select
        r.mois,
        r.qte_reelle,
        b.budget_qte,
        round(r.prix_reel_moyen::numeric, 2)     as prix_reel_moyen,
        b.budget_prix_moyen,
        round(r.ca_reel::numeric, 2)              as ca_reel,
        round((b.budget_qte * b.budget_prix_moyen)::numeric, 2) as ca_budget,
        round(((r.qte_reelle - b.budget_qte) * b.budget_prix_moyen)::numeric, 2) as ecart_volume,
        round(((r.prix_reel_moyen - b.budget_prix_moyen) * r.qte_reelle)::numeric, 2) as ecart_prix

    from reel r
    join budget b on r.mois = b.mois

)

select
    *,
    ecart_volume + ecart_prix as ecart_total

from rapproche
order by mois
