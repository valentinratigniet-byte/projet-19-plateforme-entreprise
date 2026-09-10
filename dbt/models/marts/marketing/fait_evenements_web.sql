{#
  Meme restriction d'acces que dim_contact/fait_envois (contact_id lie).

  Incremental sur horodatage : le flux evenementiel est un append pur
  (cf. _marketing__sources.yml), pas de unique_key -- session_id n'est
  teste que not_null (pas unique), un merge dessus serait risque. Strategie
  par defaut sans unique_key = insert des seules lignes filtrees.
#}

{{
    config(
        materialized='incremental',
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

{% if is_incremental() %}
where horodatage > (select coalesce(max(horodatage), '1900-01-01'::timestamp) from {{ this }})
{% endif %}
