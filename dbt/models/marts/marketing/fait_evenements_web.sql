{# Meme restriction d'acces que dim_contact/fait_envois (contact_id lie). #}

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

select * from {{ ref('stg_marketing_evenements_web') }}
