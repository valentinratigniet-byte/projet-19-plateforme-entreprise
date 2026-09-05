{#
  Regles de nettoyage :
  - MontantHT/MontantTTC : deux formats coexistent dans le brut (texte
    US "1234.56" ou FR "1 234,56", import legacy incoherent) -- espaces
    supprimes, virgule remplacee par un point, cast en numeric.
  - fournisseur_connu : ecriture dont le FournisseurID n'existe pas dans
    stg_finance_fournisseurs -- gardee et flaguee, pas supprimee (meme
    doctrine que le domaine Ventes).
  - Doublons de saisie EXACTS (meme fournisseur/facture/montant/date) --
    ici DEDOUBLONNES (contrairement aux commandes Ventes) : ce sont des
    doublons de SAISIE comptable reels (double-clic), pas des
    enregistrements distincts a conserver -- decision documentee dans
    decisions.md.
#}

with source as (

    select * from {{ source('raw', 'finance_ecritures') }}

),

fournisseurs as (

    select fournisseur_id from {{ ref('stg_finance_fournisseurs') }}

),

nettoye as (

    select
        "EcritureID"::int                                                          as ecriture_id,
        "FournisseurID"::int                                                       as fournisseur_id,
        trim("NumeroFacture")                                                      as numero_facture,
        "DateEcriture"::date                                                       as date_ecriture,
        replace(replace(trim("MontantHT"), ' ', ''), ',', '.')::numeric            as montant_ht_eur,
        replace(trim("TauxTVA"), ',', '.')::numeric                                as taux_tva,
        replace(replace(trim("MontantTTC"), ' ', ''), ',', '.')::numeric           as montant_ttc_eur,
        trim("CompteComptable")                                                    as compte_comptable,
        trim("StatutPaiement")                                                     as statut_paiement

    from source

),

dedoublonne as (

    select distinct on (fournisseur_id, numero_facture, montant_ttc_eur, date_ecriture)
        *
    from nettoye
    order by fournisseur_id, numero_facture, montant_ttc_eur, date_ecriture, ecriture_id

),

avec_fournisseur_connu as (

    select
        d.*,
        f.fournisseur_id is not null as fournisseur_connu
    from dedoublonne d
    left join fournisseurs f on d.fournisseur_id = f.fournisseur_id

)

select * from avec_fournisseur_connu
