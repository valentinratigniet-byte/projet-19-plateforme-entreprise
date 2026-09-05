{#
  Regles de nettoyage :
  - email_normalise : minuscule -- l'email brut a une casse incoherente
    selon la source de saisie.
  - nom_encodage_suspect : flag (PAS de reparation automatique) sur les
    noms qui portent la signature d'un bug de charset MySQL reel
    (colonne mal configuree en latin1 au lieu d'utf8mb4, sequences 'Ã...'
    caracteristiques) -- reparer a l'aveugle en SQL risquerait de
    fabriquer un texte faux ; le signalement est la decision assumee,
    la correction reelle releve d'un correctif cote source (documentee
    dans decisions.md), pas d'un rattrapage silencieux ici.
  - contact_doublon_probable : flag sur email_normalise identique entre
    plusieurs ID -- pas fusionne (meme discipline que Ventes/Commerce).
#}

with source as (

    select * from {{ source('raw', 'marketing_contacts') }}

),

nettoye as (

    select
        id::int                         as contact_id,
        lower(trim(email))              as email_normalise,
        prenom,
        nom,
        nom like '%Ã%'                  as nom_encodage_suspect,
        date_creation::date             as date_creation

    from source

),

avec_doublons as (

    select
        *,
        count(*) over (partition by email_normalise) > 1 as contact_doublon_probable

    from nettoye

)

select * from avec_doublons
