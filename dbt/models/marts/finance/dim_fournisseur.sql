{#
  RLS + securite colonne en post_hook (meme raison que le domaine
  Ventes : un modele `table` fait DROP+CREATE a chaque `dbt run`, ce qui
  efface policies/grants poses a part).

  Nouveaute par rapport a Ventes : restriction AU NIVEAU COLONNE en plus
  de la RLS ligne -- `role_direction` n'a pas besoin de voir l'IBAN brut
  des fournisseurs pour piloter (donnee bancaire sensible), seul
  `role_finance` en a l'usage operationnel (rapprochement paiements).
  RLS filtre les LIGNES, pas les colonnes (cf. Projet 18) : ici les deux
  techniques sont combinees sciemment.
#}

{{
    config(
        post_hook=[
            "ALTER TABLE {{ this }} ENABLE ROW LEVEL SECURITY",
            "GRANT SELECT ON {{ this }} TO role_rh, role_finance, role_direction",
            "REVOKE SELECT (iban) ON {{ this }} FROM role_direction",
            "DROP POLICY IF EXISTS rh_aucun_acces ON {{ this }}",
            "CREATE POLICY rh_aucun_acces ON {{ this }} FOR SELECT TO role_rh USING (false)",
            "DROP POLICY IF EXISTS finance_direction_complet ON {{ this }}",
            "CREATE POLICY finance_direction_complet ON {{ this }} FOR SELECT TO role_finance, role_direction USING (true)",
        ]
    )
}}

select * from {{ ref('stg_finance_fournisseurs') }}
