{#
  Nettoyage : normalisation du nom pour reperer les doublons probables
  (variantes de saisie -- meme discipline que le Projet 12) sans les
  supprimer silencieusement. La resolution definitive (quel enregistrement
  garder) est une decision documentee dans decisions.md, pas prise ici.
#}

with source as (

    select * from {{ source('raw', 'ventes_clients') }}

),

normalise as (

    select
        trim(upper("CLICOD"))                                          as clicod,
        trim("CLINOM")                                                 as clinom,
        upper(regexp_replace(trim("CLINOM"), '[^A-Za-z0-9]', '', 'g'))  as clinom_normalise,
        trim("CLIVIL")                                                 as clivil,
        trim("CLICP")                                                  as clicp,
        _source_file,
        _ingested_at

    from source

),

avec_doublons as (

    select
        *,
        count(*) over (partition by clinom_normalise, clivil) > 1 as est_doublon_probable

    from normalise

)

select * from avec_doublons
