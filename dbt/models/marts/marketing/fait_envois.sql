{#
  Grain : un envoi = une ligne. Meme restriction d'acces que dim_contact
  (donnee liee a un contact individuel, role_direction non habilite).
#}

{{
    config(
        post_hook=[
            "ALTER TABLE {{ this }} ENABLE ROW LEVEL SECURITY",
            "GRANT SELECT ON {{ this }} TO role_rh, role_marketing",
            "DROP POLICY IF EXISTS rh_aucun_acces ON {{ this }}",
            "CREATE POLICY rh_aucun_acces ON {{ this }} FOR SELECT TO role_rh USING (false)",
            "DROP POLICY IF EXISTS marketing_complet ON {{ this }}",
            "CREATE POLICY marketing_complet ON {{ this }} FOR SELECT TO role_marketing USING (true)",
        ]
    )
}}

select
    e.envoi_id,
    e.contact_id,
    e.contact_connu,
    e.campagne_id,
    c.nom as campagne_nom,
    e.date_envoi,
    e.statut

from {{ ref('stg_marketing_envois') }} e
left join {{ ref('stg_marketing_campagnes') }} c on e.campagne_id = c.campagne_id
