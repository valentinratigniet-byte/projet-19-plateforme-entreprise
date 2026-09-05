# Finance/Compta — règles de transformation (brut → net)

## Fournisseurs (`raw.finance_fournisseurs` → `staging.stg_finance_fournisseurs`)

| Colonne brute | Colonne nette | Règle appliquée | decisions.md |
|---|---|---|---|
| `SIREN` | `siren_normalise` | Espaces supprimés | Nettoyage |
| — | `siren_valide` | Flag (pas de suppression) : `true` si 9 chiffres après normalisation | Nettoyage |
| `IBAN` | `iban` | Trim, accès restreint par colonne (`role_direction` exclu) | Entreposage |

## Écritures comptables (`raw.finance_ecritures` → `staging.stg_finance_ecritures`)

| Colonne brute | Colonne nette | Règle appliquée | decisions.md |
|---|---|---|---|
| `MontantHT`/`MontantTTC` (texte FR ou US) | `montant_ht_eur`/`montant_ttc_eur` | Espaces supprimés, virgule → point, cast numeric | Traitement |
| `FournisseurID` | `fournisseur_id` + `fournisseur_connu` | Rapproché à `stg_finance_fournisseurs` ; conservé avec flag si absent | Nettoyage |
| (ligne entière) | — | Doublons **exacts** (même fournisseur/facture/montant/date) **supprimés** — contrairement aux commandes Ventes | Nettoyage |

## Relevé bancaire (`raw.finance_releve_bancaire` → `staging.stg_finance_releve_bancaire`)

| Colonne brute | Colonne nette | Règle appliquée | decisions.md |
|---|---|---|---|
| `Montant` (texte FR) | `montant_eur` | Espaces supprimés, virgule → point, cast numeric | Traitement |
| `Date operation` (DD/MM/YYYY) | `date_operation` | Parsée en date | Traitement |
| `Libelle` | `libelle_normalise` | Préfixe VIR/PRLV supprimé, majuscule, ponctuation supprimée — exposé pour un rapprochement flou ultérieur, **pas fait** | Entreposage |
| (ligne entière) | — | Doublons exacts (rejeu d'export bancaire) supprimés | Nettoyage |

## Factures reçues (`raw.finance_factures_recues` → `staging.stg_finance_factures_recues` → `marts.fait_rapprochement_factures`)

| Colonne brute | Colonne nette | Règle appliquée | decisions.md |
|---|---|---|---|
| `fournisseur_siren` | `siren_normalise` | Même règle que les fournisseurs | Nettoyage |
| `montant_ttc` (texte, parfois illisible) | `montant_ttc_eur` | Cast numeric ; `NULL` si non conforme (jamais deviné) | Nettoyage |
| `siren_normalise` + `montant_ttc_eur` | `fait_rapprochement_factures.rapprochee` | Jointure par SIREN vers `dim_fournisseur`, puis appariement à l'écriture du même fournisseur au montant le plus proche (< 0,01 €) | Entreposage |

**`numero_facture` volontairement NON utilisé pour le rapprochement** :
l'ERP et le fournisseur ne partagent pas la même numérotation (constat
fait dès `avant.md`) — un rapprochement par numéro aurait été un artefact,
pas une vraie correspondance.

**Résultat du rapprochement** : 91 % des factures Factur-X rattachées
avec confiance à une écriture, contre 44 % pour le canal non structuré.
