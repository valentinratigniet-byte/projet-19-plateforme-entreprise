{#
  Dimension partagee entre les 3 domaines -- le coeur du modele
  constellation (dimensions communes, plusieurs faits), pas une dimension
  de plus par domaine. `fait_ventes.date_commande`,
  `fait_ecritures.date_ecriture`, `fait_envois.date_envoi` s'y
  rattachent tous par la valeur de date (cle naturelle, pas de surrogate
  key ajoutee aux faits deja verifies -- eviterait de retoucher des
  modeles stables pour un gain marginal).
#}

{{
    config(
        post_hook=[
            "GRANT SELECT ON {{ this }} TO role_rh, role_finance, role_direction, role_commercial, role_marketing",
        ]
    )
}}

with jours as (

    select generate_series('2025-12-01'::date, '2026-09-30'::date, interval '1 day')::date as date_jour

)

select
    date_jour,
    extract(year from date_jour)::int          as annee,
    extract(month from date_jour)::int          as mois,
    to_char(date_jour, 'Month')                 as nom_mois,
    extract(quarter from date_jour)::int        as trimestre,
    extract(isodow from date_jour)::int         as jour_semaine,
    extract(isodow from date_jour) in (6, 7)    as est_weekend

from jours
