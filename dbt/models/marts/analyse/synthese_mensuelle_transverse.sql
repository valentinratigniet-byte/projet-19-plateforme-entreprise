{#
  Le fil narratif qui a motive le choix des 3 domaines des le depart
  (cadrage, issue #2) rendu concret : campagne marketing -> impact
  ventes -> depenses Finance, sur la MEME grille mensuelle. Pas une
  causalite demontree (correlation temporelle uniquement, honnete sur
  ce point dans decisions.md/analyse-transverse.md), mais une vraie
  mise en regard chiffree des 3 domaines plutot que 3 silos.
#}

{{
    config(
        post_hook=[
            "GRANT SELECT ON {{ this }} TO role_finance, role_direction, role_commercial, role_marketing",
        ]
    )
}}

with marketing as (

    select
        to_char(date_envoi, 'YYYY-MM') as mois,
        count(*) filter (where statut = 'CLIQUE') as clics,
        count(*)                                   as envois

    from {{ ref('fait_envois') }}
    group by 1

),

ventes as (

    select
        to_char(date_commande, 'YYYY-MM') as mois,
        sum(montant_ht_eur)                as ca_ht,
        count(*)                            as nb_commandes

    from {{ ref('fait_ventes') }}
    where statut <> 'ANNULEE'
    group by 1

),

finance as (

    select
        to_char(date_ecriture, 'YYYY-MM') as mois,
        sum(montant_ttc_eur)               as depenses_ttc

    from {{ ref('fait_ecritures') }}
    group by 1

)

select
    coalesce(m.mois, v.mois, f.mois) as mois,
    m.clics,
    m.envois,
    v.ca_ht,
    v.nb_commandes,
    f.depenses_ttc,
    round((v.ca_ht - f.depenses_ttc)::numeric, 2) as marge_brute_approx

from marketing m
full outer join ventes v on m.mois = v.mois
full outer join finance f on coalesce(m.mois, v.mois) = f.mois
order by 1
