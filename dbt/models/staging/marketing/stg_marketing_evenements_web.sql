{#
  Regles de nettoyage :
  - utm_source_normalise : minuscule, et la typo connue "emial" corrigee
    explicitement (constatee dans le brut, pas une supposition generale) --
    toute autre variante non reconnue reste telle quelle plutot que d'etre
    devinee.
  - horodatage : cast timestamp.
  - contact_connu : evenement dont le contact_id n'existe pas (trafic
    anonyme volontaire, cf. avant.md) -- flag informatif, pas une anomalie.
#}

with source as (

    select * from {{ source('raw', 'marketing_evenements_web') }}

),

contacts as (

    select contact_id from {{ ref('stg_marketing_contacts') }}

),

nettoye as (

    select
        s.session_id::int                                   as session_id,
        nullif(s.contact_id, '')::int                        as contact_id,
        s.type                                                as type_evenement,
        s.horodatage::timestamp                               as horodatage,
        case
            when lower(trim(s.contexte_utm_source)) = 'emial' then 'email'
            else lower(trim(s.contexte_utm_source))
        end                                                    as utm_source_normalise,
        lower(trim(s.contexte_utm_medium))                    as utm_medium_normalise,
        s.contexte_utm_campaign                               as utm_campaign,
        s.contexte_page                                       as page

    from source s

),

avec_contact_connu as (

    select
        n.*,
        (n.contact_id is null) or (c.contact_id is not null) as contact_connu

    from nettoye n
    left join contacts c on n.contact_id = c.contact_id

)

select * from avec_contact_connu
