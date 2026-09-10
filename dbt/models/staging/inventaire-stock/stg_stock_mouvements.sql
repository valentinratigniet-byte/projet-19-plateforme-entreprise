{#
  Doublons de scan EXACTS (meme article/type/quantite/date/source) --
  DEDOUBLONNES ici, meme doctrine que Finance (double-clic comptable) :
  un double-scan physique n'est pas un second mouvement reel, contrairement
  aux commandes Ventes ou chaque ligne brute est conservee.

  DATE_MVT reste TIMESTAMP nu (pas de conversion de fuseau -- l'horodatage
  scanner local est restitue tel quel, cf. simulateur_firebird.py).

  Cast explicite : `postgres_writer.remplacer_table` ecrit tout en TEXT,
  necessaire ici avant le tri du dedoublonnage (un tri texte sur
  mouvement_id/date_mouvement diverge d'un tri numerique/chronologique).
#}

with source as (

    select * from {{ source('raw', 'stock_mouvements') }}

),

renomme as (

    select
        "MVTID"::int             as mouvement_id,
        "ARTCOD"                 as article_id,
        "TYPE_MVT"               as type_mouvement,
        "QUANTITE"::int          as quantite,
        "DATE_MVT"::timestamp    as date_mouvement,
        "SOURCE"                 as source_mouvement

    from source

),

dedoublonne as (

    select distinct on (article_id, type_mouvement, quantite, date_mouvement, source_mouvement)
        *
    from renomme
    order by article_id, type_mouvement, quantite, date_mouvement, source_mouvement, mouvement_id

)

select * from dedoublonne
