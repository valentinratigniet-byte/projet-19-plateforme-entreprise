{#
  Regles de nettoyage :
  - Montant (texte FR "1 234,56", parfois negatif) -> numeric.
  - Date operation (DD/MM/YYYY) -> date.
  - Libelle : le nom du fournisseur n'est jamais donne tel quel (extrait
    tronque, prefixe VIR/PRLV) -- `libelle_normalise` expose pour un
    rapprochement flou ulterieur avec les fournisseurs, PAS fait ici
    (meme raisonnement que les remises Excel du domaine Ventes :
    documente comme limite assumee, pas invente).
  - Lignes strictement dupliquees (rejeu d'export bancaire) dedoublonnees.
#}

with source as (

    select * from {{ source('raw', 'finance_releve_bancaire') }}

),

nettoye as (

    select
        to_date("Date_operation", 'DD/MM/YYYY')                                    as date_operation,
        trim("Libelle")                                                            as libelle,
        upper(regexp_replace(
            regexp_replace(trim("Libelle"), '^(VIR|PRLV)\s+', ''),
            '[^A-Za-z0-9]', '', 'g'
        ))                                                                          as libelle_normalise,
        replace(replace(trim("Montant"), ' ', ''), ',', '.')::numeric               as montant_eur,
        trim("Devise")                                                              as devise,
        _source_file,
        _ingested_at

    from source

),

dedoublonne as (

    select distinct on (date_operation, libelle, montant_eur)
        *
    from nettoye
    order by date_operation, libelle, montant_eur, _ingested_at

)

select * from dedoublonne
