# Ventes/Commerce — règles de transformation (brut → net)

Ce que fait l'ETL entre `raw` et `staging`/`marts`, colonne par colonne —
`decisions.md` explique le *pourquoi*, ce fichier montre le *quoi
exactement a changé*.

## Clients (`raw.ventes_clients` → `staging.stg_ventes_clients`)

| Colonne brute | Colonne nette | Règle appliquée | decisions.md |
|---|---|---|---|
| `CLICOD` | `clicod` | Trim + uppercase | Entreposage |
| `CLINOM` | `clinom` | Trim (valeur conservée telle quelle) | — |
| `CLINOM` | `clinom_normalise` | Uppercase, ponctuation supprimée — sert au repérage de doublons et au rapprochement flou avec l'Excel | Nettoyage |
| `CLIVIL`, `CLICP` | `clivil`, `clicp` | Trim | — |
| — | `est_doublon_probable` | Flag (pas de suppression) : `true` si `clinom_normalise` + `clivil` identiques à un autre `clicod` | Nettoyage |

## Commandes (`raw.ventes_commandes` → `staging.stg_ventes_commandes`)

| Colonne brute | Colonne nette | Règle appliquée | decisions.md |
|---|---|---|---|
| `CMDDAT` (texte 8 car.) | `date_commande` | YYYYMMDD tenté en premier ; si mois/année implausible, repli sur DDMMYYYY | Traitement |
| — | `date_format_derive` | Flag : `true` si le repli DDMMYYYY a été nécessaire | Traitement |
| `STCMD` (variantes libres) | `statut` | Regroupé par préfixe (`VAL%`→VALIDEE, `LIV%`→LIVREE, `ANN%`→ANNULEE), sinon `INCONNU` | Nettoyage |
| `PRIXUN`, `MTTHT` (centimes, texte) | `prix_unitaire_eur`, `montant_ht_eur` | `::numeric / 100` | Traitement |
| `CLICOD` | `clicod` + `client_connu` | Rapproché à `stg_ventes_clients` ; conservé avec flag si absent (pas supprimé) | Nettoyage |

## Remises (`raw.ventes_remises` → `staging.stg_ventes_remises` → `marts.dim_client`)

| Colonne brute | Colonne nette | Règle appliquée | decisions.md |
|---|---|---|---|
| `Remise` (parfois une formule cassée) | `remise_valide`, `remise_pct` | Regex numérique ; si non conforme (ex. `=Grille2026!B99`), `remise_pct` = NULL, `remise_valide` = false | Nettoyage |
| `Client` (v3 ET v4) | 1 ligne par client | La ligne du fichier le plus récent gagne (`v4_FINAL` > `v3`, puis date d'ingestion) | Nettoyage |
| `Client` (nom saisi) | `dim_client.remise_source_nom` | Rapprochement flou vers `CLINOM` AS/400 par similarité de trigrammes (`pg_trgm`), retenu seulement si score ≥ 0,5 | Entreposage |

**Résultat du rapprochement flou** : seulement 3 des 16 clients avec
remise sont rattachés avec confiance à un `CLICOD` AS/400 — le reste
reste avec une remise non appliquée dans `fait_ventes` (`montant_net_eur`
= `montant_ht_eur`), pas une valeur devinée.
