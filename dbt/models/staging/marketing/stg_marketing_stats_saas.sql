select
    campagne_id::int          as campagne_id,
    nom,
    envoyes::int              as envoyes,
    ouverts::int              as ouverts,
    clics::int                as clics,
    desabonnements::int       as desabonnements,
    taux_ouverture::numeric   as taux_ouverture,
    taux_clic::numeric        as taux_clic

from {{ source('raw', 'marketing_stats_saas') }}
