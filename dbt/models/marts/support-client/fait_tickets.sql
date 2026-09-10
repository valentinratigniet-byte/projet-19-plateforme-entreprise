{#
  RLS en post_hook -- meme raison que les autres domaines : un modele
  `table` fait DROP+CREATE a chaque `dbt run`, poser policies/grants a
  part les ferait disparaitre au run suivant. role_support (operationnel)
  + role_direction (supervision) peuvent lire ; role_rh/role_finance
  n'ont pas d'usage metier sur des tickets SAV, pas de GRANT pour eux.
#}

{{
    config(
        post_hook=[
            "ALTER TABLE {{ this }} ENABLE ROW LEVEL SECURITY",
            "GRANT SELECT ON {{ this }} TO role_support, role_direction",
            "DROP POLICY IF EXISTS support_direction_complet ON {{ this }}",
            "CREATE POLICY support_direction_complet ON {{ this }} FOR SELECT TO role_support, role_direction USING (true)",
        ]
    )
}}

select
    ticket_id,
    client_id,
    schema_ancien,
    numero_commande,
    categorie,
    priorite,
    statut,
    date_creation,
    date_derniere_maj,
    nb_messages,
    satisfaction,
    case
        when date_derniere_maj is not null
            then extract(day from date_derniere_maj - date_creation)::int
    end as delai_resolution_jours

from {{ ref('stg_support_tickets') }}
