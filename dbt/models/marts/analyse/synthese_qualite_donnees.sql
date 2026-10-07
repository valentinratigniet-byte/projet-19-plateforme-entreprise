{#
  Consolidation des flags de qualite deja poses dans 4 marts separes
  (jamais recalcules ici, juste agreges) -- sert le rapport Power BI 7
  (Gouvernance qualite), identifie dans pistes-power-bi.md comme le seul
  rapport necessitant un modele dedie plutot qu'un export direct de mart.

  Volontairement une ligne par (domaine, flag) -- PAS par mois comme
  esquisse dans le plan initial : dim_client et dim_fournisseur n'ont
  aucune colonne de date (photo de l'etat courant, pas une serie
  temporelle), inventer un mois de rattachement aurait ete fabrique, pas
  mesure. fait_ecritures et dim_contact ont bien une date mais le mix
  serait alors incoherent (2 flags avec tendance, 2 sans) -- mieux vaut
  une photo honnete et uniforme sur les 4 que 2 vraies tendances et 2
  fausses.

  severite : "structurel" = bloque une jointure ou un calcul aval
  (siren_valide, fournisseur_connu) ; "informatif" = visible mais sans
  impact aval (est_doublon_probable, contact_doublon_probable), cf.
  doctrine deja posee dans pistes-power-bi.md.
#}

{{
    config(
        post_hook=[
            "GRANT SELECT ON {{ this }} TO role_finance, role_direction, role_commercial, role_marketing",
        ]
    )
}}

with ventes as (

    select
        'Ventes'                                                   as domaine,
        'est_doublon_probable'                                     as flag,
        'Client dont le nom est similaire a un autre (pg_trgm), jamais fusionne automatiquement' as description,
        'informatif'                                                as severite,
        count(*)                                                    as lignes_totales,
        count(*) filter (where est_doublon_probable)                as lignes_flaguees

    from {{ ref('dim_client') }}

),

finance_siren as (

    select
        'Finance'                                                  as domaine,
        'siren_valide'                                              as flag,
        'SIREN qui ne respecte pas le format attendu (9 chiffres)' as description,
        'structurel'                                                as severite,
        count(*)                                                    as lignes_totales,
        -- siren_valide peut etre NULL (SIREN absent, pas juste mal
        -- forme) -- "is not true" capture FALSE et NULL, contrairement
        -- a "not siren_valide" qui exclut silencieusement les NULL
        -- (logique ternaire SQL). Piege trouve en verifiant ce mart
        -- contre le rapport 2 Power BI (1,25% mesure la, 0% ici avant
        -- correction).
        count(*) filter (where siren_valide is not true)            as lignes_flaguees

    from {{ ref('dim_fournisseur') }}

),

finance_fournisseur_connu as (

    select
        'Finance'                                                  as domaine,
        'fournisseur_connu'                                         as flag,
        'Ecriture qui reference un fournisseur absent du referentiel' as description,
        'structurel'                                                as severite,
        count(*)                                                    as lignes_totales,
        count(*) filter (where not fournisseur_connu)               as lignes_flaguees

    from {{ ref('fait_ecritures') }}

),

marketing as (

    select
        'Marketing'                                                as domaine,
        'contact_doublon_probable'                                  as flag,
        'Contact dont l''email est identique a un autre, jamais fusionne automatiquement' as description,
        'informatif'                                                as severite,
        count(*)                                                    as lignes_totales,
        count(*) filter (where contact_doublon_probable)            as lignes_flaguees

    from {{ ref('dim_contact') }}

),

tout as (

    select * from ventes
    union all select * from finance_siren
    union all select * from finance_fournisseur_connu
    union all select * from marketing

)

select
    domaine || '.' || flag                                         as flag_id,
    domaine,
    flag,
    description,
    severite,
    lignes_totales,
    lignes_flaguees,
    round(100.0 * lignes_flaguees / nullif(lignes_totales, 0), 2)   as pct_flague

from tout
