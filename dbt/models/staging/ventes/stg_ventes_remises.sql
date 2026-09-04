{#
  Regles de nettoyage documentees ici (detail metier dans
  regles-transformation.md) :
  - remise_valide : une ligne du brut contient une formule Excel cassee
    ("=Grille2026!B99", #REF! a l'ouverture) au lieu d'un nombre --
    detectee et exclue du calcul plutot que de planter le modele.
  - reconciliation v3/v4 : les 2 fichiers sont ingeres tels quels en brut
    (raw.ventes_remises) ; ici, on retient la ligne du fichier le plus
    recent par client (v4_FINAL > v3) quand les deux existent -- rendu
    explicite, pas une fusion silencieuse. Rapprochement nom saisi ->
    CLICOD AS/400 : PAS FAIT ici (raisonnement du choix dans decisions.md)
    -- champ `client_nom_saisi` expose tel quel pour un rapprochement flou
    ulterieur (meme famille d'outillage que le Projet 12).
#}

with source as (

    select * from {{ source('raw', 'ventes_remises') }}

),

nettoye as (

    select
        trim("Client")                                    as client_nom_saisi,
        "Remise" ~ '^-?[0-9]+\.?[0-9]*$'                   as remise_valide,
        case
            when "Remise" ~ '^-?[0-9]+\.?[0-9]*$'
                then "Remise"::numeric
        end                                                 as remise_pct,
        nullif(trim("Commentaire"), '')                     as commentaire,
        nullif(trim("Valable_jusqu_au"), '')                as valable_jusquau,
        _source_file,
        case when _source_file like '%v4%' then 2 else 1 end as rang_version,
        _ingested_at

    from source

),

le_plus_recent_par_client as (

    select
        *,
        row_number() over (
            partition by client_nom_saisi
            order by rang_version desc, _ingested_at desc
        ) as rn

    from nettoye

)

select
    client_nom_saisi,
    remise_valide,
    remise_pct,
    commentaire,
    valable_jusquau,
    _source_file as source_retenue,
    _ingested_at

from le_plus_recent_par_client
where rn = 1
