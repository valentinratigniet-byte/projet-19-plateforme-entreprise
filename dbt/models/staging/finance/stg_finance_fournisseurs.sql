{#
  Nettoyage : SIREN normalise (espaces supprimes) et valide (9 chiffres),
  invalide/absent flague plutot que rejete -- une facture reste
  rattachable au fournisseur meme si son SIREN est mal renseigne.
#}

with source as (

    select * from {{ source('raw', 'finance_fournisseurs') }}

),

nettoye as (

    select
        "FournisseurID"::int                                        as fournisseur_id,
        trim("RaisonSociale")                                       as raison_sociale,
        nullif(regexp_replace("SIREN", '\s', '', 'g'), '')          as siren_normalise,
        trim("IBAN")                                                as iban

    from source

),

avec_validite as (

    select
        *,
        siren_normalise ~ '^\d{9}$' as siren_valide

    from nettoye

)

select * from avec_validite
