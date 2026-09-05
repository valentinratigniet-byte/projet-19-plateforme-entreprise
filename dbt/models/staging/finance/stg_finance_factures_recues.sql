{#
  Regles de nettoyage :
  - montant_ttc : deja numerique cote Factur-X (canal fiable), texte cote
    non structure (peut etre NULL si l'OCR a echoue -- conserve NULL,
    pas invente).
  - SIREN normalise (meme regle que stg_finance_fournisseurs).
  - `numero_facture` PAS rapproche du `NumeroFacture` interne SQL Server
    ici : les deux ne suivent pas la meme numerotation (le fournisseur
    numerote ses factures a sa maniere, l'ERP assigne sa propre reference
    interne a la saisie) -- rapprochement fait en mart par
    fournisseur+montant+date, pas par numero. Limite assumee, documentee
    dans decisions.md.
#}

with source as (

    select * from {{ source('raw', 'finance_factures_recues') }}

),

nettoye as (

    select
        numero_facture,
        date_facture::date                                              as date_facture,
        trim(fournisseur_nom)                                           as fournisseur_nom,
        nullif(regexp_replace(coalesce(fournisseur_siren, ''), '\s', '', 'g'), '') as siren_normalise,
        nullif(montant_ht, '')::numeric                                 as montant_ht_eur,
        nullif(montant_tva, '')::numeric                                as montant_tva_eur,
        nullif(montant_ttc, '')::numeric                                as montant_ttc_eur,
        canal,
        _source_file,
        _ingested_at

    from source

)

select * from nettoye
