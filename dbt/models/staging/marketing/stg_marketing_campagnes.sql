select
    id::int          as campagne_id,
    trim(nom)        as nom,
    trim(type)       as type,
    date_envoi::date as date_envoi,
    trim(utm_campaign) as utm_campaign

from {{ source('raw', 'marketing_campagnes') }}
