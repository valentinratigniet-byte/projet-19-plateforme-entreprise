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

  Piege reel rencontre : un `GRANT SELECT` global sur la table rend
  inoperant un `REVOKE SELECT (colonne)` pose ensuite -- le grant table
  prime sur le revoke colonne en Postgres (verifie via
  `has_column_privilege`, le revoke n'avait aucun effet). Corrige en
  n'accordant JAMAIS le SELECT global a `role_direction` : uniquement les
  colonnes explicitement listees, `iban` absente de la liste.
#}

{{
    config(
        post_hook=[
            "ALTER TABLE {{ this }} ENABLE ROW LEVEL SECURITY",
            "GRANT SELECT ON {{ this }} TO role_rh, role_finance",
            "GRANT SELECT (fournisseur_id, raison_sociale, siren_normalise, siren_valide) ON {{ this }} TO role_direction",
            "DROP POLICY IF EXISTS rh_aucun_acces ON {{ this }}",
            "CREATE POLICY rh_aucun_acces ON {{ this }} FOR SELECT TO role_rh USING (false)",
            "DROP POLICY IF EXISTS finance_direction_complet ON {{ this }}",
            "CREATE POLICY finance_direction_complet ON {{ this }} FOR SELECT TO role_finance, role_direction USING (true)",
        ]
    )
}}

select * from {{ ref('stg_finance_fournisseurs') }}
