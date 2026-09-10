{#
  Aplatissement JSON -- pas de dbt-mongodb (aucun adaptateur officiel,
  dbt reste SQL-only), donc le document JSON est traite ici comme du
  JSON Postgres ordinaire (`::jsonb`, `->>`), une fois la donnee deja
  posee dans `raw` par l'adaptateur Python. C'est la frontiere reelle
  entre "ingestion" et "dbt" pour une source document store : dbt ne
  lit jamais Mongo directement, seulement le JSON deja atterri.

  Derive de schema geree ici, pas corrigee a la source : les tickets
  anciens portent "customer_ref", les recents "client_id" -- coalesce
  plutot que de pretendre qu'un seul format a toujours existe.
#}

with source as (

    select * from {{ source('raw', 'support_tickets') }}

),

parse as (

    select
        id as ticket_id,
        document::jsonb as doc

    from source

),

nettoye as (

    select
        ticket_id,
        coalesce(doc->>'client_id', doc->>'customer_ref')          as client_id,
        (doc ? 'customer_ref' and not (doc ? 'client_id'))          as schema_ancien,
        nullif(doc->>'numero_commande', '')                        as numero_commande,
        doc->>'sujet'                                               as sujet,
        doc->>'categorie'                                           as categorie,
        doc->>'priorite'                                            as priorite,
        doc->>'statut'                                              as statut,
        (doc->>'date_creation')::timestamp                          as date_creation,
        nullif(doc->>'date_derniere_maj', '')::timestamp            as date_derniere_maj,
        nullif(doc->>'satisfaction', '')::int                       as satisfaction,
        jsonb_array_length(coalesce(doc->'messages', '[]'::jsonb))  as nb_messages

    from parse

)

select * from nettoye
