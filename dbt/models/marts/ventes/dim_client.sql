{#
  Rapprochement flou nom Excel (saisi a la main) -> CLICOD AS/400, promis
  en staging (stg_ventes_remises) et fait ici via pg_trgm (similarite de
  trigrammes) -- extension activee une fois par superuser, cf.
  entrepot/init/02_extensions.sql.

  Seuil 0.5, pas 0.4 : a 0.4, deux faux positifs reels observes
  ("Legendre SARL" et "Lesage S.A.R.L." matches tous les deux sur
  "Lefevre Sarl", scores 0.40-0.41) -- le suffixe juridique commun
  ("Sarl") gonfle artificiellement la similarite entre societes
  differentes sur des noms courts. Remonte a 0.5 pour les exclure ;
  documente dans decisions.md (compromis precision/rappel assume : mieux
  vaut une remise manquante qu'une remise fausse attribuee au mauvais
  client).
#}

with clients as (

    select * from {{ ref('stg_ventes_clients') }}

),

remises as (

    select * from {{ ref('stg_ventes_remises') }}
    where remise_valide

),

rapprochement as (

    select
        c.*,
        r.client_nom_saisi as remise_source_nom,
        r.remise_pct,
        similarity(c.clinom_normalise, r.client_nom_normalise) as remise_score_confiance
    from clients c
    left join lateral (
        select *
        from remises r
        order by similarity(c.clinom_normalise, r.client_nom_normalise) desc
        limit 1
    ) r on true

)

select
    clicod,
    clinom,
    clivil,
    clicp,
    est_doublon_probable,
    case when remise_score_confiance >= 0.5 then remise_pct end            as remise_pct,
    case when remise_score_confiance >= 0.5 then remise_source_nom end     as remise_source_nom,
    remise_score_confiance

from rapprochement
