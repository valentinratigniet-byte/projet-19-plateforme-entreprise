{#
  Regle de nettoyage : statut regroupe par prefixe (francais ET anglais --
  stack marketing typique, melange d'origines des outils) plutot qu'une
  liste exhaustive de correspondances exactes.
#}

with source as (

    select * from {{ source('raw', 'marketing_envois') }}

),

contacts as (

    select contact_id from {{ ref('stg_marketing_contacts') }}

),

nettoye as (

    select
        s.id::int            as envoi_id,
        s.contact_id::int    as contact_id,
        s.campagne_id::int   as campagne_id,
        s.date_envoi::date   as date_envoi,
        case
            when upper(trim(s.statut)) like 'ENVOYE%' or upper(trim(s.statut)) = 'SENT' then 'ENVOYE'
            when upper(trim(s.statut)) like 'OUVERT%' or upper(trim(s.statut)) like 'OPEN%' then 'OUVERT'
            when upper(trim(s.statut)) like 'CLIQUE%' or upper(trim(s.statut)) like 'CLICK%' then 'CLIQUE'
            when upper(trim(s.statut)) like 'DESABONNE%' or upper(trim(s.statut)) like 'UNSUB%' then 'DESABONNE'
            else 'INCONNU'
        end                  as statut

    from source s

),

avec_contact_connu as (

    select
        n.*,
        c.contact_id is not null as contact_connu

    from nettoye n
    left join contacts c on n.contact_id = c.contact_id

)

select * from avec_contact_connu
