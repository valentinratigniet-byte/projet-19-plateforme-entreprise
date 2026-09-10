{#
  RLS en post_hook (meme raison que les autres domaines : un modele
  `table` fait DROP+CREATE a chaque `dbt run`). role_stock (operationnel
  entrepot) + role_direction (supervision) peuvent lire ; RH/Finance/
  Commercial n'ont pas d'usage metier sur du stock physique.
#}

{{
    config(
        post_hook=[
            "ALTER TABLE {{ this }} ENABLE ROW LEVEL SECURITY",
            "GRANT SELECT ON {{ this }} TO role_stock, role_direction",
            "DROP POLICY IF EXISTS stock_direction_complet ON {{ this }}",
            "CREATE POLICY stock_direction_complet ON {{ this }} FOR SELECT TO role_stock, role_direction USING (true)",
        ]
    )
}}

select
    article_id,
    libelle,
    emplacement,
    seuil_reappro,
    quantite_stock,
    quantite_stock < 0            as stock_negatif,
    quantite_stock < seuil_reappro as sous_seuil_reappro

from {{ ref('stg_stock_articles') }}
