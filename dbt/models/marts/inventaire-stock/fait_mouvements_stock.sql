{{
    config(
        post_hook=[
            "ALTER TABLE {{ this }} ENABLE ROW LEVEL SECURITY",
            "GRANT SELECT ON {{ this }} TO role_stock, role_direction",
            "DROP POLICY IF EXISTS mouvements_direction_complet ON {{ this }}",
            "CREATE POLICY mouvements_direction_complet ON {{ this }} FOR SELECT TO role_stock, role_direction USING (true)",
        ]
    )
}}

select
    mouvement_id,
    article_id,
    type_mouvement,
    quantite,
    date_mouvement,
    source_mouvement

from {{ ref('stg_stock_mouvements') }}
