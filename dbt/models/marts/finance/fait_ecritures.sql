{#
  Grain : une ligne = une ecriture comptable (deja dedoublonnee en
  staging). RLS en post_hook, meme raison que dim_fournisseur.sql.

  Incremental sur ecriture_id, pas sur _ingested_at : la colonne existe
  bien au niveau raw (writer commun, cf. postgres_writer.py), mais elle
  horodate le dernier TRUNCATE+RELOAD complet de finance_ecritures ("etat
  courant complet", cf. _finance__sources.yml), pas l'ajout d'une ecriture
  precise -- inutilisable comme curseur d'incrementalite ici. ecriture_id
  est le bon curseur : hypothese assumee qu'une ecriture postee n'est
  jamais modifiee retroactivement (semantique comptable normale, une
  correction se fait par contre-passation = nouvel EcritureID). Limite
  connue : si un fournisseur est cree APRES l'ecriture qui le referencait,
  `fournisseur_connu` reste figue a `false` pour les lignes deja
  materialisees (un full-refresh le recalculerait).
#}

{{
    config(
        materialized='incremental',
        unique_key='ecriture_id',
        incremental_strategy='delete+insert',
        on_schema_change='fail',
        post_hook=[
            "ALTER TABLE {{ this }} ENABLE ROW LEVEL SECURITY",
            "GRANT SELECT ON {{ this }} TO role_rh, role_finance, role_direction",
            "DROP POLICY IF EXISTS rh_aucun_acces ON {{ this }}",
            "CREATE POLICY rh_aucun_acces ON {{ this }} FOR SELECT TO role_rh USING (false)",
            "DROP POLICY IF EXISTS finance_direction_complet ON {{ this }}",
            "CREATE POLICY finance_direction_complet ON {{ this }} FOR SELECT TO role_finance, role_direction USING (true)",
        ]
    )
}}

select
    ecriture_id,
    fournisseur_id,
    fournisseur_connu,
    numero_facture,
    date_ecriture,
    montant_ht_eur,
    taux_tva,
    montant_ttc_eur,
    compte_comptable,
    statut_paiement

from {{ ref('stg_finance_ecritures') }}

{% if is_incremental() %}
where ecriture_id > (select coalesce(max(ecriture_id), 0) from {{ this }})
{% endif %}
