{#
  Rapprochement factures recues (Factur-X + non structure) <-> ecritures
  comptables SQL Server. PAS par numero de facture (les deux sources ne
  partagent pas la meme numerotation -- le fournisseur numerote a sa
  facon, l'ERP assigne sa propre reference interne, constat reel du
  brut) : rapprochement par SIREN (cle fiable quand presente des deux
  cotes) puis montant TTC exact (a 1 centime pres), le plus proche en
  date. Une facture sans SIREN valide ou sans ecriture au meme montant
  reste explicitement NON rapprochee -- pas de correspondance devinee.

  RLS en post_hook, meme raison que les autres marts du domaine.
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

with factures as (

    select * from {{ ref('stg_finance_factures_recues') }}

),

fournisseurs as (

    select * from {{ ref('stg_finance_fournisseurs') }}
    where siren_valide

),

ecritures as (

    select * from {{ ref('stg_finance_ecritures') }}

),

factures_avec_fournisseur as (

    select
        f.*,
        four.fournisseur_id
    from factures f
    left join fournisseurs four on f.siren_normalise = four.siren_normalise

),

rapprochement as (

    select
        fa.numero_facture,
        fa.fournisseur_nom,
        fa.fournisseur_id,
        fa.date_facture,
        fa.montant_ttc_eur,
        fa.canal,
        e.ecriture_id                                    as ecriture_rapprochee_id,
        e.date_ecriture,
        abs(fa.date_facture - e.date_ecriture)           as ecart_jours
    from factures_avec_fournisseur fa
    left join lateral (
        select *
        from ecritures e
        where e.fournisseur_id = fa.fournisseur_id
          and abs(e.montant_ttc_eur - fa.montant_ttc_eur) < 0.01
        order by abs(fa.date_facture - e.date_ecriture)
        limit 1
    ) e on true

)

select
    *,
    ecriture_rapprochee_id is not null as rapprochee

from rapprochement
