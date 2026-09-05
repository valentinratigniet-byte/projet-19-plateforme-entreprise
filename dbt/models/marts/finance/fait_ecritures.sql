{#
  Grain : une ligne = une ecriture comptable (deja dedoublonnee en
  staging). RLS en post_hook, meme raison que dim_fournisseur.sql.
#}

{{
    config(
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
