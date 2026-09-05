{#
  Mart agrege (pas de contact individuel) -- accessible a role_direction,
  contrairement a dim_contact/fait_envois/fait_evenements_web. Recoupe
  les stats API SaaS (systeme de reference pour l'engagement) avec un
  calcul interne independant depuis MySQL -- verifie la coherence entre
  les deux sources plutot que de faire confiance a une seule.
#}

{{
    config(
        post_hook=[
            "ALTER TABLE {{ this }} ENABLE ROW LEVEL SECURITY",
            "GRANT SELECT ON {{ this }} TO role_rh, role_marketing, role_direction",
            "DROP POLICY IF EXISTS rh_aucun_acces ON {{ this }}",
            "CREATE POLICY rh_aucun_acces ON {{ this }} FOR SELECT TO role_rh USING (false)",
            "DROP POLICY IF EXISTS marketing_direction_complet ON {{ this }}",
            "CREATE POLICY marketing_direction_complet ON {{ this }} FOR SELECT TO role_marketing, role_direction USING (true)",
        ]
    )
}}

with saas as (

    select * from {{ ref('stg_marketing_stats_saas') }}

),

calcul_interne as (

    select
        campagne_id,
        count(*)                                                    as envoyes_calcules,
        count(*) filter (where statut in ('OUVERT', 'CLIQUE'))       as ouverts_calcules,
        count(*) filter (where statut = 'CLIQUE')                    as clics_calcules

    from {{ ref('stg_marketing_envois') }}
    group by campagne_id

)

select
    s.campagne_id,
    s.nom,
    s.envoyes,
    s.ouverts,
    s.clics,
    s.desabonnements,
    s.taux_ouverture,
    s.taux_clic,
    c.envoyes_calcules,
    c.ouverts_calcules,
    c.clics_calcules,
    (s.envoyes = c.envoyes_calcules) as coherent_avec_mysql

from saas s
left join calcul_interne c on s.campagne_id = c.campagne_id
