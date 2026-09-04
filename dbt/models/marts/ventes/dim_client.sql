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

  RLS en post_hook, pas en script a part : un modele materialise en
  `table` fait DROP+CREATE a chaque `dbt run`, ce qui efface policies et
  grants poses separement -- piege reel rencontre, cf.
  docs/guide-realisation.md. Roles crees ailleurs (entrepot/init/,
  domaines/ventes-commerce/rls.sql), ce post_hook ne fait que
  grant/policy, idempotent (DROP POLICY IF EXISTS avant CREATE).
#}

{{
    config(
        post_hook=[
            "ALTER TABLE {{ this }} ENABLE ROW LEVEL SECURITY",
            "GRANT SELECT ON {{ this }} TO role_rh, role_finance, role_direction, role_commercial",
            "DROP POLICY IF EXISTS rh_aucun_acces ON {{ this }}",
            "CREATE POLICY rh_aucun_acces ON {{ this }} FOR SELECT TO role_rh USING (false)",
            "DROP POLICY IF EXISTS finance_direction_complet ON {{ this }}",
            "CREATE POLICY finance_direction_complet ON {{ this }} FOR SELECT TO role_finance, role_direction USING (true)",
            "DROP POLICY IF EXISTS commercial_tout ON {{ this }}",
            "CREATE POLICY commercial_tout ON {{ this }} FOR SELECT TO role_commercial USING (true)",
        ]
    )
}}

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
