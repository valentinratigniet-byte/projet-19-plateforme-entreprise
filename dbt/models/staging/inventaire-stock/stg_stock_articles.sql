{#
  Colonnes source en MAJUSCULES entre guillemets : Firebird met en
  majuscules tout identifiant non guillemete a la creation (cf.
  simulateur_firebird.py), l'adaptateur Python restitue les noms tels
  quels -- pas une convention choisie ici, un comportement du SGBD source.

  Cast explicite : `postgres_writer.remplacer_table` ecrit tout en TEXT
  (le typage arrive en staging, pas a l'ingestion -- meme convention que
  les autres domaines), les colonnes numeriques doivent donc etre
  castees ici avant tout calcul/comparaison en aval.
#}

with source as (

    select * from {{ source('raw', 'stock_articles') }}

),

nettoye as (

    select
        "ARTCOD"                    as article_id,
        "LIBELLE"                   as libelle,
        "EMPLACEMENT"               as emplacement,
        "SEUIL_REAPPRO"::int        as seuil_reappro,
        "QUANTITE_STOCK"::int       as quantite_stock

    from source

)

select * from nettoye
