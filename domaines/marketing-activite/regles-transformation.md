# Marketing/Activité — règles de transformation (brut → net)

## Contacts (`raw.marketing_contacts` → `staging.stg_marketing_contacts`)

| Colonne brute | Colonne nette | Règle appliquée | decisions.md |
|---|---|---|---|
| `email` | `email_normalise` | Minuscule, trim | Nettoyage |
| `nom` | `nom` + `nom_encodage_suspect` | Conservé tel quel + flag si signature de mojibake détectée (séquences `Ã...`) — **pas de réparation automatique** | Nettoyage |
| — | `contact_doublon_probable` | Flag (pas de fusion) si `email_normalise` identique entre plusieurs `id` | Nettoyage |

## Envois (`raw.marketing_envois` → `staging.stg_marketing_envois`)

| Colonne brute | Colonne nette | Règle appliquée | decisions.md |
|---|---|---|---|
| `statut` (FR/EN, casse libre) | `statut` | Regroupé par préfixe (`ENVOYE%`/`SENT`, `OUVERT%`/`OPEN%`, `CLIQUE%`/`CLICK%`, `DESABONNE%`/`UNSUB%`) | Nettoyage |
| `contact_id` | `contact_connu` | Flag si absent de `stg_marketing_contacts` | Nettoyage |

## Événements web (`raw.marketing_evenements_web` → `staging.stg_marketing_evenements_web`)

| Colonne brute | Colonne nette | Règle appliquée | decisions.md |
|---|---|---|---|
| `contexte_utm_source` | `utm_source_normalise` | Minuscule + correction de la typo constatée `"emial"` → `"email"` (correction ciblée, pas une normalisation floue générale) | Nettoyage |
| `horodatage` (texte) | `horodatage` | Cast timestamp | Traitement |
| `contact_id` | `contact_connu` | `true` si absent (trafic anonyme volontaire) ou si présent dans les contacts connus | Nettoyage |
| (objet imbriqué `contexte`) | colonnes plates | Aplatissement structurel à l'ingestion (`ingestion/adaptateurs/json_file.py`) — pas une règle de nettoyage, une nécessité de stockage relationnel | Extraction |

## Stats SaaS (`raw.marketing_stats_saas` → `staging.stg_marketing_stats_saas` → `marts.fait_performance_campagnes`)

| Colonne brute | Colonne nette | Règle appliquée | decisions.md |
|---|---|---|---|
| `envoyes`, `ouverts`, `clics`, `desabonnements` | (idem, typés) | Cast entier | Traitement |
| — | `coherent_avec_mysql` | Comparaison au comptage indépendant calculé depuis `stg_marketing_envois` — **8/8 campagnes cohérentes**, testé par `assert_stats_saas_coherentes_mysql` | Entreposage |

## Reverse ETL (`marts.fait_envois` → API SaaS)

Segment "contacts engagés non désabonnés" (au moins un clic, jamais
désabonnés) calculé directement en SQL sur `marts.fait_envois`, poussé via
`POST /api/segments` — **124 contacts** dans le run vérifié. Aucune
transformation de la définition du segment côté SaaS : le calcul fait foi
côté entrepôt, le SaaS ne fait que le recevoir.
