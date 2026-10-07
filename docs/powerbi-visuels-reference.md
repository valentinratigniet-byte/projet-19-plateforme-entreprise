# Power BI — référence visuels par rapport

Schéma plaintext de chaque page + mapping exact champ/mesure → zone de
visuel, pour les 8 rapports. Chiffres réels, mesurés le 2026-09-19/24
(détail et vérifications dans `docs/guide-realisation.md`). Les modèles
(tables, relations, mesures, RLS) sont déjà construits dans les 8
`.pbix` — il ne reste que la couche visuelle (pages/visuels) à poser
dans Power BI Desktop, en suivant ce document.

Fichiers `.pbix` : `dashboard-ventes-commerce.pbix`,
`dashboard-finance-compta.pbix`, `dashboard-marketing-activite.pbix`
(nommé "DASH 3" côté fichier), `dashboard-support-client.pbix`,
`dashboard-inventaire-stock.pbix`, `dashboard-transverse-direction.pbix`,
`dashboard-gouvernance-qualite.pbix`, `dashboard-pnl-simplifie.pbix`.

---

## Rapport 1 — Ventes & Commerce : Pilotage commercial

### Page 1 — Vue d'ensemble

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Ventes / Commerce — Vue d'ensemble                          page 1 / 4  │
├─────────────────────────────────────────────────────────────────────────┤
│ [Calendrier ▾ dim_date]                                                  │
│ ┌─────────┐┌─────────┐┌─────────┐┌─────────┐                            │
│ │ 15,09M €││  2 052  ││ 7 349 € ││   0 %   │                            │
│ │  CA HT  ││Commandes││ Panier  ││ Statut  │                            │
│ │         ││ actives ││ moyen   ││ INCONNU │                            │
│ └─────────┘└─────────┘└─────────┘└─────────┘                            │
│ ┌────────────────────────────────┐ ┌────────────────────────────────┐  │
│ │ WATERFALL — Écart budget        │ │ MATRICE — Top clients           │  │
│ │ Prix/Volume (vue synthèse)      │ │ (drill-through → page 2)        │  │
│ └────────────────────────────────┘ └────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

| Visuel | Type | Zone → Champ |
|---|---|---|
| CA HT | Carte | `fait_ventes[CA HT]` |
| Commandes actives | Carte | `fait_ventes[Commandes Actives]` |
| Panier moyen | Carte | `fait_ventes[Panier Moyen]` |
| % Statut Inconnu | Carte | `fait_ventes[% Statut Inconnu]` |
| Waterfall écart budget | Cascade | Catégorie : `ecart_budget_ventes[mois]` · Valeur : `ecart_budget_ventes[Ecart Total]` |
| Matrice top clients | Matrice | Lignes : `dim_client[clinom]` · Valeurs : `fait_ventes[CA HT]`, `fait_ventes[Commandes Actives]` · Top N (10) trié sur CA HT |

Drill-through page 2 : champ `dim_client[clicod]`.

### Page 2 — Détail commandes (drill-through)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Ventes / Commerce — Détail commandes            page 2 / 4 — drill-through│
├─────────────────────────────────────────────────────────────────────────┤
│ [Client (contexte) ▾]                                                   │
│ ┌─────────────┐  Client sélectionné                                     │
│ │ CLICOD 0142 │                                                         │
│ └─────────────┘                                                         │
│ ┌───────────────────────────────────────────────────────────────────┐  │
│ │ MATRICE — Détail commandes du client                               │  │
│ └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

| Visuel | Type | Zone → Champ |
|---|---|---|
| Client sélectionné | Carte | `dim_client[clicod]` |
| Matrice détail | Table | `fait_ventes[cmdnum]`, `[date_commande]`, `[statut]`, `[montant_ht_eur]`, `[montant_net_eur]` |

⚠️ `date_format_derive` (mentionné dans le plan initial) n'existe **pas** dans `fait_ventes` — présent seulement en staging (`stg_ventes_commandes`), jamais sélectionné dans le mart. Ne pas chercher ce champ.

### Page 3 — Clients et remises

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Ventes / Commerce — Clients et remises                      page 3 / 4  │
├─────────────────────────────────────────────────────────────────────────┤
│ [Calendrier ▾]                                                           │
│ ┌─────────┐┌─────────┐┌─────────────────┐                               │
│ │  314    ││   28    ││  3/16 (19 %)     │                               │
│ │ Clients ││ Doublons││ Remises Excel    │                               │
│ │         ││ prob.   ││ rapprochées      │                               │
│ └─────────┘└─────────┘└─────────────────┘                               │
│ ┌────────────────────────────────┐ ┌────────────────────────────────┐  │
│ │ MATRICE — Clients (doublon      │ │ RAPPROCHEMENT remise→client      │  │
│ │ probable flagué)                 │ │ (pg_trgm) — texte statique       │  │
│ └────────────────────────────────┘ └────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

| Visuel | Type | Zone → Champ |
|---|---|---|
| Clients | Carte | `dim_client[Nb Clients]` |
| Doublons probables | Carte | `dim_client[Nb Clients Doublon Probable]` |
| Remises Excel rapprochées | Carte | `stg_ventes_remises[% Remises Excel Rapprochées]` |
| Matrice clients | Table | `dim_client[clicod]`, `[clinom]`, `[est_doublon_probable]`, `[remise_pct]`, `[remise_score_confiance]` — mise en forme conditionnelle sur `est_doublon_probable` (voir note méthode plus bas) |
| Panneau rapprochement | Zone de texte | Statique : seuil 0,5, pourquoi pas 0,4, "remise non rattachée = montant net = montant HT" |

⚠️ Note : `% Remises Rapprochées` (sur `dim_client`, base 314 clients = 0,96 %) et `% Remises Excel Rapprochées` (sur `stg_ventes_remises`, base 16 remises = 18,75 %) sont **deux mesures différentes qui répondent à des questions différentes** — ne pas les confondre.

### Page 4 — Écart budgétaire

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Ventes / Commerce — Écart budgétaire                        page 4 / 4  │
├─────────────────────────────────────────────────────────────────────────┤
│ [Mois ▾]                                                                 │
│ ┌───────────────────────────────────────────────────────────────────┐  │
│ │ MATRICE — Écart volume/prix/total par mois                         │  │
│ └───────────────────────────────────────────────────────────────────┘  │
│ ┌───────────────────────────────────────────────────────────────────┐  │
│ │ WATERFALL détaillé — Décomposition Prix × Volume, mois sélectionné │  │
│ └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

| Visuel | Type | Zone → Champ |
|---|---|---|
| Matrice écart par mois | Matrice | Lignes : `ecart_budget_ventes[mois]` · Valeurs : `[qte_reelle]`, `[CA Reel (Budget)]`, `[CA Budget]`, `[Ecart Volume]`, `[Ecart Prix]`, `[Ecart Total]` |
| Waterfall détaillé | Cascade | ⚠️ le vrai pont Budget→Volume→Prix→Réel a besoin d'une table dépivotée (pas construite). **Solution simple sans remodelage** : histogramme groupé, Axe = `mois`, Valeurs = `[Ecart Volume]` + `[Ecart Prix]` |

---

## Rapport 2 — Finance & Compta : Rapprochement factures et trésorerie

### Page 1 — Vue d'ensemble AP

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Finance / Compta — Vue d'ensemble AP                         page 1 / 3 │
├─────────────────────────────────────────────────────────────────────────┤
│ [Calendrier ▾]                                                           │
│ ┌─────────┐┌─────────┐┌─────────┐┌─────────┐                            │
│ │ 7,24M € ││ 90,8 %  ││ 44,4 %  ││ 1,64 %  │                            │
│ │Mt TTC   ││Rappr.   ││Rappr.   ││Écrit.   │                            │
│ │         ││Factur-X ││non str. ││fourn.inc│                            │
│ └─────────┘└─────────┘└─────────┘└─────────┘                            │
│ ┌────────────────────────────────┐ ┌────────────────────────────────┐  │
│ │ ⚠️BARRES — répartition par       │ │ MATRICE — Écritures par statut  │  │
│ │ compte comptable (remplace       │ │ de paiement                     │  │
│ │ l'aging, données absentes)       │ │                                  │  │
│ └────────────────────────────────┘ └────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

| Visuel | Type | Zone → Champ |
|---|---|---|
| Montant TTC | Carte | `fait_ecritures[Montant TTC Total]` |
| Rapproché Factur-X | Carte | `fait_rapprochement_factures[Taux Rapprochement Facturx]` |
| Rapproché non structuré | Carte | `fait_rapprochement_factures[Taux Rapprochement Non Structure]` |
| Écritures fourn. inconnu | Carte | `fait_ecritures[% Ecritures Fournisseur Inconnu]` |
| Répartition par compte | Histogramme empilé | Axe : `fait_ecritures[compte_comptable]` · Légende : `[statut_paiement]` · Valeurs : `[Montant TTC Total]` |
| Écritures par statut | Matrice | Lignes : `fait_ecritures[statut_paiement]` · Valeurs : `[Montant TTC Total]`, compte de `[ecriture_id]` |

⚠️ L'aging 0-30/30-60/60-90/90+ du wireframe original n'est pas construisible (aucune date d'échéance dans les données) — remplacé par la répartition par compte comptable ci-dessus.

### Page 2 — Détail rapprochement (drill-through)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Finance / Compta — Détail rapprochement       page 2 / 3 — drill-through│
├─────────────────────────────────────────────────────────────────────────┤
│ [Fournisseur (contexte) ▾]                                              │
│ ┌─────────────┐  Fournisseur sélectionné                                │
│ │ F. Besnard  │                                                         │
│ └─────────────┘                                                         │
│ ┌───────────────────────────────────────────────────────────────────┐  │
│ │ MATRICE — Factures ↔ écritures (SIREN+montant, jamais par numéro)  │  │
│ └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

| Visuel | Type | Zone → Champ |
|---|---|---|
| Fournisseur sélectionné | Carte | `dim_fournisseur[raison_sociale]` |
| Matrice rapprochement | Table | `fait_rapprochement_factures[numero_facture]`, `[fournisseur_nom]`, `[date_facture]`, `[montant_ttc_eur]`, `[canal]`, `[date_ecriture]`, `[ecart_jours]`, `[rapprochee]` |

Drill-through : champ `dim_fournisseur[fournisseur_id]`.

⚠️ `Ecart Jours Moyen` = 0 partout (vérifié, `MAX(ecart_jours)`=0 sur toute la table) — le simulateur donne toujours la même date à la facture et à l'écriture (`generer_evenements.py`), pas un bug.

### Page 3 — Fournisseurs et SIREN

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Finance / Compta — Fournisseurs et SIREN                     page 3 / 3 │
├─────────────────────────────────────────────────────────────────────────┤
│ [Calendrier ▾]                                                           │
│ ┌─────────┐┌─────────┐┌─────────────────┐                               │
│ │   80    ││1 (1,3 %)││     1,6 %        │                               │
│ │Fournis. ││SIREN inv││Écritures fourn.  │                               │
│ │         ││         ││inconnu           │                               │
│ └─────────┘└─────────┘└─────────────────┘                               │
│ ┌───────────────────────────────────────────────────────────────────┐  │
│ │ MATRICE — Fournisseurs, SIREN normalisé + flag validité             │  │
│ └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

| Visuel | Type | Zone → Champ |
|---|---|---|
| Fournisseurs | Carte | `dim_fournisseur[Nb Fournisseurs]` |
| SIREN invalides | Carte | `dim_fournisseur[% SIREN Invalides]` |
| Écritures fourn. inconnu | Carte | `fait_ecritures[% Ecritures Fournisseur Inconnu]` |
| Matrice fournisseurs | Table | `dim_fournisseur[fournisseur_id]`, `[raison_sociale]`, `[siren_normalise]`, `[siren_valide]` |

⚠️ **`iban` n'est importée dans aucun rapport** (ni ici ni ailleurs) — exclue dès la requête M source (`Table.RemoveColumns`), pas juste cachée. Sécurité réelle = côté Postgres (`role_finance` seul, déjà vérifié).

---

## Rapport 3 — Marketing & Activité : Performance campagnes

### Page 1 — Vue d'ensemble

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Marketing / Activité — Vue d'ensemble                        page 1 / 3 │
├─────────────────────────────────────────────────────────────────────────┤
│ [Calendrier ▾]                                                           │
│ ┌─────────┐┌─────────┐┌─────────┐┌─────────┐                            │
│ │  755    ││ 61,1 %  ││ 32,1 %  ││  8 / 8  │                            │
│ │ Envois  ││Tx ouv.  ││Tx clic  ││Cohérence│                            │
│ └─────────┘└─────────┘└─────────┘└─────────┘                            │
│ ┌──────────────┐ ┌──────────────────────────────────────────────────┐  │
│ │ FUNNEL        │ │ MATRICE — Envois par statut normalisé            │  │
│ └──────────────┘ └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

| Visuel | Type | Zone → Champ |
|---|---|---|
| Envois | Carte | `fait_performance_campagnes[Envois Total]` |
| Taux ouverture | Carte | `fait_performance_campagnes[Taux Ouverture]` |
| Taux clic | Carte | `fait_performance_campagnes[Taux Clic]` |
| Cohérence SaaS/MySQL | Carte | `fait_performance_campagnes[% Coherent avec MySQL]` |
| Funnel | Entonnoir | Étapes : Envoyés/Ouverts/Clics · Valeurs : `SUM(envoyes)`, `SUM(ouverts)`, `SUM(clics)` de `fait_performance_campagnes` |
| Matrice statuts | Matrice | Lignes : `fait_envois[statut]` · Valeurs : compte de `envoi_id` |

### Page 2 — Funnel et CTOR

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Marketing / Activité — Funnel et CTOR                        page 2 / 3 │
├─────────────────────────────────────────────────────────────────────────┤
│ [Campagne ▾]                                                            │
│ ┌───────────────────────────────────────────────────────────────────┐  │
│ │ COURBE — CTOR par campagne dans le temps                           │  │
│ └───────────────────────────────────────────────────────────────────┘  │
│ ┌───────────────────────────────────────────────────────────────────┐  │
│ │ MATRICE — SaaS vs calcul interne MySQL, campagne par campagne      │  │
│ └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

| Visuel | Type | Zone → Champ |
|---|---|---|
| Courbe CTOR | Courbe | Axe : `fait_performance_campagnes[nom]` · Valeurs : `[CTOR (Click-to-Open)]` |
| Matrice SaaS vs MySQL | Matrice | Lignes : `[nom]` · Valeurs : `[envoyes]`, `[envoyes_calcules]`, `[ouverts]`, `[ouverts_calcules]`, `[clics]`, `[clics_calcules]`, `[coherent_avec_mysql]` |

**Point en attente** : `fait_evenements_web` (funnel web, importée) n'a pas encore de visuel dédié — à ajouter ici ou en page 4 séparée si besoin.

### Page 3 — Contacts (`role_marketing` uniquement)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Marketing / Activité — Contacts          page 3 / 3 — role_marketing seul│
├─────────────────────────────────────────────────────────────────────────┤
│ [Calendrier ▾]                                                           │
│ ┌───────────────────────────────────────────────────────────────────┐  │
│ │ MATRICE — Contacts (doublon probable flagué)                       │  │
│ └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

| Visuel | Type | Zone → Champ |
|---|---|---|
| Matrice contacts | Table | `dim_contact[contact_id]`, `[email_normalise]`, `[prenom]`, `[nom]`, `[contact_doublon_probable]`, `[nom_encodage_suspect]` |

**Mise en forme conditionnelle (méthode générale, piège réel rencontré)** : "Mettre en forme par = Règles" n'accepte qu'un champ **numérique**, jamais un booléen directement. Pour `contact_doublon_probable` : colonne cachée `doublon_num` déjà créée dans le modèle (`dim_contact[doublon_num]`, 0/1) — pointer la règle dessus (`≥ 1` → rouge `#D9534F`) tout en affichant la colonne booléenne normale dans la matrice.

---

## Rapport 4 — Support Client : Pilotage SAV

### Page 1 — SAV

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Support Client — SAV                                          page 1/2 │
├─────────────────────────────────────────────────────────────────────────┤
│ [Calendrier ▾]                                                           │
│ ┌─────────┐┌─────────┐┌─────────┐                                       │
│ │  242    ││  5,5 j  ││ 3,84/5  │                                       │
│ │ Tickets ││ Délai   ││Satisfac.│                                       │
│ │ ouverts ││ moyen   ││ moyenne │                                       │
│ └─────────┘└─────────┘└─────────┘                                       │
│ ┌────────────────────────────────┐ ┌────────────────────────────────┐  │
│ │ BARRES — Volumétrie par         │ │ COURBES — Créés vs résolus      │  │
│ │ statut / priorité               │ │ dans le temps                   │  │
│ └────────────────────────────────┘ └────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

| Visuel | Type | Zone → Champ |
|---|---|---|
| Tickets ouverts | Carte | `fait_tickets[Tickets Ouverts]` |
| Délai moyen | Carte | `fait_tickets[Delai Moyen Resolution (jours)]` |
| Satisfaction | Carte | `fait_tickets[Satisfaction Moyenne]` |
| Barres statut/priorité | Histogramme groupé | Axe : `[statut]` · Légende : `[priorite]` · Valeurs : `fait_tickets[Nb Tickets]` |
| Courbes créés vs résolus | Courbe 2 séries | Axe : `dim_date` Calendrier · Série "créés" : `[Nb Tickets]` (relation active sur `date_creation`) · Série "résolus" : **mesure à créer** (`USERELATIONSHIP` sur `date_derniere_maj`, relation inactive pas encore posée) |

### Page 2 — Détail tickets (drill-through)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Support Client — Détail tickets                page 2/2 — drill-through │
├─────────────────────────────────────────────────────────────────────────┤
│ [Ticket (contexte) ▾]                                                   │
│ ┌─────────────┐  Ticket sélectionné                                     │
│ │ TCK-00142   │                                                         │
│ └─────────────┘                                                         │
│ ┌───────────────────────────────────────────────────────────────────┐  │
│ │ MATRICE — Détail ticket (catégorie, priorité, nb messages, délai)  │  │
│ └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

| Visuel | Type | Zone → Champ |
|---|---|---|
| Ticket sélectionné | Carte | `fait_tickets[ticket_id]` |
| Matrice détail | Table | `[ticket_id]`, `[categorie]`, `[priorite]`, `[statut]`, `[nb_messages]`, `[delai_resolution_jours]`, `[schema_ancien]` |

---

## Rapport 5 — Inventaire & Stock : Ruptures et mouvements

### Page 1 — Ruptures

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Inventaire / Stock — Ruptures                                 page 1/2 │
├─────────────────────────────────────────────────────────────────────────┤
│ [Calendrier ▾]                                                           │
│ ┌─────────┐┌─────────┐┌─────────┐┌─────────┐                            │
│ │  50 %   ││   20    ││   21    ││   40    │                            │
│ │%rupture ││Stock neg││Ss seuil ││ Suivis  │                            │
│ └─────────┘└─────────┘└─────────┘└─────────┘                            │
│ ┌────────────────────────────────┐ ┌────────────────────────────────┐  │
│ │ BARRES — Niveau de stock par    │ │ MATRICE — Articles en stock     │  │
│ │ article (top ruptures)          │ │ négatif                         │  │
│ └────────────────────────────────┘ └────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

| Visuel | Type | Zone → Champ |
|---|---|---|
| % rupture | Carte | `dim_stock_articles[% Rupture]` |
| Stock négatif | Carte | `dim_stock_articles[Articles en Rupture]` |
| Sous seuil | Carte | `dim_stock_articles[Articles Sous Seuil]` |
| Articles suivis | Carte | `dim_stock_articles[Nb Articles]` |
| Barres top ruptures | Histogramme | Axe : `[libelle]` · Valeurs : `[quantite_stock]` · Top N (10, trié croissant) |
| Matrice stock négatif | Table | `[article_id]`, `[libelle]`, `[emplacement]`, `[quantite_stock]`, `[seuil_reappro]` · filtre `stock_negatif = TRUE` |

### Page 2 — Mouvements

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Inventaire / Stock — Mouvements                                page 2/2│
├─────────────────────────────────────────────────────────────────────────┤
│ [Article ▾]  [Calendrier ▾]                                             │
│ ┌───────────────────────────────────────────────────────────────────┐  │
│ │ BARRES EMPILÉES — Mouvements Entrée/Sortie par mois, par article   │  │
│ └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

| Visuel | Type | Zone → Champ |
|---|---|---|
| Barres empilées | Histogramme empilé | Axe : `dim_date` Calendrier (Mois) · Légende : `fait_mouvements_stock[type_mouvement]` · Valeurs : `[quantite]` (ou les 3 mesures dédiées `[Quantite Entrees]`/`[Quantite Sorties]`/`[Quantite Inventaire]`) |

⚠️ `Quantite Inventaire` peut être négative (-78 net mesuré) — c'est un écart de comptage **signé** par construction du simulateur (positif ou négatif), pas une anomalie.

---

## Rapport 6 — Transverse Direction : Vue consolidée

### Page 1 — Vue consolidée

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Transverse Direction — Vue consolidée                         page 1/2 │
├─────────────────────────────────────────────────────────────────────────┤
│ [Calendrier ▾]                                                           │
│ ┌─────────┐┌─────────┐┌─────────┐                                       │
│ │ 2,51M € ││ 1,17M € ││   32    │  ⚠️ chiffres "dernier mois" (HT)       │
│ │CA Ventes││ Dépenses││  Clics  │                                       │
│ └─────────┘└─────────┘└─────────┘                                       │
│ ┌───────────────────────────────────────────────────────────────────┐  │
│ │ COURBES INDEXÉES — CA Ventes / Dépenses / Clics, même grille       │  │
│ └───────────────────────────────────────────────────────────────────┘  │
│ ┌───────────────────────────────────────────────────────────────────┐  │
│ │ ⚠️ CONSTAT HONNÊTE : aucune corrélation mesurée clics↔CA             │  │
│ └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

| Visuel | Type | Zone → Champ |
|---|---|---|
| CA Ventes (dernier mois) | Carte | `synthese_mensuelle_transverse[CA Ventes]` + filtre visuel Top N=1 sur `[mois]` trié décroissant (sinon = total période) |
| Dépenses (dernier mois) | Carte | `fait_ecritures[Depenses Finance HT]` + même filtre |
| Clics (dernier mois) | Carte | `synthese_mensuelle_transverse[Clics Marketing]` + même filtre |
| Courbes indexées | Courbe 3 séries | Axe : `[mois]` · Séries : `[CA Ventes]`, `[Depenses Finance HT]`, `[Clics Marketing]` |
| Constat honnête | Zone de texte | Statique, repris de `docs/analyse-transverse.md` |

### Page 2 — Méthodologie et limites

Page entièrement en zones de texte statique (4 blocs : grille de mise en regard / absence de corrélation / cause structurelle / prochaine étape réelle) — aucun champ de données, reprend `docs/analyse-transverse.md`.

---

## Rapport 7 — Gouvernance Qualité : Flags de données

### Page 1 — Vue d'ensemble qualité

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Gouvernance qualité — Les flags, pas les chiffres              page 1/3│
├─────────────────────────────────────────────────────────────────────────┤
│ [Domaine ▾]                                                             │
│ ┌───────────┐ ┌──────────────────┐ ┌──────────────────────────────┐    │
│ │  JAUGE    │ │ BARRES — Volume   │ │ TABLE — Flags par sévérité   │    │
│ │  96,2%    │ │ flagué par        │ │                                │    │
│ │ conforme  │ │ domaine           │ │                                │    │
│ └───────────┘ └──────────────────┘ └──────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

| Visuel | Type | Zone → Champ |
|---|---|---|
| Jauge conformité | Jauge | Valeur : `synthese_qualite_donnees[% Lignes Conformes]` · Cible 100% (n'y arrivera jamais, assumé) |
| Barres par domaine | Histogramme | Axe : `[domaine]` · Valeurs : `[Lignes Flaguees Total]` ⚠️ pas de vraie dimension mensuelle (mart = photo, pas de série temporelle) |
| Table par sévérité | Table | `[flag]`, `[severite]`, `[lignes_totales]`, `[lignes_flaguees]`, `[pct_flague]` |

### Page 2 — Détail par domaine

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Gouvernance qualité — Détail par domaine                       page 2/3│
├─────────────────────────────────────────────────────────────────────────┤
│ [Domaine ▾]                                                             │
│ ┌───────────────────────────────────────────────────────────────────┐  │
│ │ MATRICE — Lignes flaguées par domaine, drill-through vers source   │  │
│ └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

| Visuel | Type | Zone → Champ |
|---|---|---|
| Matrice flags | Matrice | Lignes : `[domaine]`, `[flag]` · Valeurs : `[lignes_flaguees]`, `[pct_flague]` |
| Drill-through | — | 4 mini-pages cibles (une par table source) : `dim_client[clicod]` / `dim_fournisseur[fournisseur_id]` / `fait_ecritures[ecriture_id]` / `dim_contact[contact_id]` — Power BI n'autorise qu'un champ de drill-through par page cible |

### Page 3 — Définitions des flags

Texte statique (4 blocs : doublons probables / siren_valide / fournisseur_connu / date_format_derive) — alternative dynamique : table `synthese_qualite_donnees[flag]`+`[description]`+`[severite]` plutôt que du texte figé.

**RLS de ce rapport (5 tables)** :

| Table | role_finance | role_direction | role_commercial | role_marketing |
|---|---|---|---|---|
| `synthese_qualite_donnees` | ✅ | ✅ | ✅ | ✅ |
| `dim_client` | ✅ | ✅ | ✅ | ❌ |
| `dim_fournisseur` (sans IBAN) | ✅ | ✅ | ❌ | ❌ |
| `fait_ecritures` | ✅ | ✅ | ❌ | ❌ |
| `dim_contact` | ❌ | ❌ | ❌ | ✅ |

(`role_rh` : aucun accès.)

---

## Rapport 8 — P&L Simplifié : Produits & Charges

### Page 1 — Vue d'ensemble P&L

```
┌─────────────────────────────────────────────────────────────────────────┐
│ P&L simplifié — Produits / Charges                             page 1/2│
├─────────────────────────────────────────────────────────────────────────┤
│ [Calendrier ▾]                                                           │
│ ┌─────────┐┌─────────┐┌─────────┐┌─────────┐                            │
│ │13,46M € ││ 6,03M € ││ 7,43M € ││ 55,2 %  │                            │
│ │Produits ││ Charges ││Résultat ││ Marge % │                            │
│ └─────────┘└─────────┘└─────────┘└─────────┘                            │
│ ┌────────────────────────────────┐ ┌────────────────────────────────┐  │
│ │ WATERFALL — Produits → Charges  │ │ COURBE — Résultat cumulé (YTD)  │  │
│ │ par poste → Résultat            │ │                                  │  │
│ └────────────────────────────────┘ └────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

| Visuel | Type | Zone → Champ |
|---|---|---|
| Produits | Carte | `fait_ventes[Produits (CA HT Ventes)]` |
| Charges | Carte | `fait_ecritures[Charges (Achats HT Finance)]` |
| Résultat | Carte | `fait_ventes[Resultat Approx]` |
| Marge % | Carte | `fait_ventes[Marge %]` |
| Waterfall | Cascade | Catégorie : `fait_ecritures[compte_comptable]` · Valeurs : `[Charges (Achats HT Finance)]` — bornes Produits/Résultat via les options "Total départ/arrivée" du visuel Cascade natif |
| Courbe YTD | Courbe | Axe : `dim_date` Calendrier · Valeurs : **mesure à créer** `Resultat Cumule YTD = TOTALYTD([Resultat Approx], dim_date[date_jour])` (pas encore dans le modèle) |

### Page 2 — Définitions et limites

Texte statique (3 blocs : pas un P&L PCG complet / HT pas TTC / pas d'entité commune Ventes-Finance) — repris de `pistes-power-bi.md`.

---

## Points laissés ouverts (rien ajouté sans confirmation)

- Rapport 3 page 2 : visuel pour `fait_evenements_web` (funnel web) pas encore posé.
- Rapport 7 page 1 : pas de vraie dimension mensuelle pour "barres mensuelles" (le mart est un instantané, pas une série temporelle — décision assumée, documentée dans `synthese_qualite_donnees.sql`).
- `dim_date` ne couvre que déc. 2025 → sept. 2026 : les tickets (dès août 2024) et mouvements de stock plus anciens ne sont visibles que sans filtre de période (signalé sur les pages concernées). Étendre `dim_date` côté dbt réglerait le point.

## Couche visuelle des rapports 4 à 8 — posée le 2026-10-07

Pages et visuels générés en PBIR dans les `.pbix` (même thème « Petrol & Amber », même navigateur de pages et mêmes segments Chiclet que le rapport 1), puis vérifiés page par page dans Power BI Desktop (captures dans `Capture d'écran power bi/`). Écarts au plan ci-dessus, tous voulus :

- **Rapport 4 — bug de modèle corrigé** : `date_creation` porte l'heure, la relation vers `dim_date[date_jour]` ne rattachait que **5 tickets sur 640** (filtre « 2026 » → 4 tickets). Ajout de `date_creation_jour` / `date_maj_jour` (sans heure), relation active refaite sur `date_creation_jour` (219 tickets rattachés = tous ceux de la période du calendrier), relation **inactive** sur `date_maj_jour` + mesure `Tickets Resolus` (`USERELATIONSHIP`, statuts `resolu`/`ferme`). Page 2 = segments déroulants (ticket, statut, priorité) comme le rapport 1, pas de page drill-through.
- **Rapport 5** : pas de filtre de période en page 1 (le niveau de stock n'a pas de date) ; top 10 en filtre TopN croissant.
- **Rapport 6** : les « 1,40 M€ » de dépenses du dernier mois étaient le montant **TTC** de la synthèse ; le HT réel est **1,17 M€** (août 2026). `fait_ecritures` n'étant pas relié à la synthèse, nouvelle mesure `Depenses HT (mois synthese)` (`TREATAS` via `dim_date[annee_mois]`) + mesures `… Dernier Mois` (au lieu d'un filtre Top N). Courbes « indexées » remplacées par un graphique combiné : CA et dépenses HT en colonnes (€), clics en ligne sur l'axe de droite. Pas de segment calendrier (il ne filtrerait que les dépenses).
- **Rapport 7** : les 4 cibles de drill-through sont 4 tables de lignes flaguées sur la page 2 (les tables sources n'ont aucune relation avec le mart, un vrai drill-through ne filtrerait rien) ; page 3 = table des définitions lue dans le mart. `pct_flague` (stocké en points de %) formaté `0.00 %`.
- **Rapport 8** : table calculée `postes_pnl` + mesure `Montant Poste P&L` (produits positifs, achats négatifs) pour une vraie cascade Produits → achats par compte → Résultat (7,43 M€) ; `Resultat Cumule YTD` vide sur les mois sans données (pas de faux plateau).
- Colonne `dim_date[annee_mois]` (AAAA-MM) ajoutée aux rapports 4, 5, 6 et 8 pour les axes mensuels.
- Colonne `dim_date[mois_court]` (« janv. » … « déc. », triée sur `mois`) ajoutée aux rapports 4, 5 et 8 : `nom_mois` est en anglais.

**Charte visuelle (reprise des méthodes du projet 21, palette Petrol & Ambre)** : pages 1280 × 720 (et non 1920 × 1080, où les polices
par défaut deviennent illisibles) ; bandeau pétrole foncé avec titre du rapport et onglets (onglet actif ambre) ; segments Chiclet
compacts sans en-tête ; tuiles KPI pleines (valeur 26 pt blanche), fond par **seuils nets** vert/orange/rouge sur les indicateurs de
qualité (délai, satisfaction, ruptures, conformité, marge) — pas de dégradé, qui donne des teintes ternes ; panneaux à titre pétrole
sans sous-titre automatique ni titre d'axe ; tables à en-tête pétrole et lignes alternées ; pied de page source / limites au lieu de
paragraphes ; pages de texte en fiches numérotées. Rapport 7 : jauge retirée (doublon de la tuile « Lignes conformes ») ; page 2 =
les 4 tables de lignes flaguées seules (la matrice doublonnait la synthèse de la page 1 et le segment Domaine ne filtrait pas les
tables sources). Rapport 8 page 2 : table et histogramme HT / TTC par compte en preuve des limites.
**Rapports 1 à 3 alignés le 2026-10-07** : mêmes visuels (champs, filtres, tris, titres, mises en forme conditionnelles),
remis à l'échelle en 1280 × 720 sous le bandeau ; cartes recréées en tuiles (même champ) ; segments calendrier recréés sur
`dim_date[mois_court]` (colonne ajoutée aux 3 modèles) ; tailles de police fixées pour 1920 × 1080 retirées. **Bug corrigé** :
la mise en forme conditionnelle de la table Contacts (rapport 3) colorait en rouge les contacts où `doublon_num = 0`, c'est-à-dire
les 194 contacts sains au lieu des 12 doublons — règle passée à `doublon_num = 1`. Thème : `charte-powerbi/portfolio-petrol-ambre-v2.json`
à la racine du portfolio.

## Méthode générale — mise en forme conditionnelle sur un booléen

Rencontré sur plusieurs rapports (`contact_doublon_probable`, `est_doublon_probable`, etc.) : la mise en forme conditionnelle par **Règles** de Power BI n'accepte qu'un champ **numérique** (comparateurs min/max), jamais un booléen directement. Solution : une colonne calculée cachée `xxx_num = IF([bool], 1, 0)` à côté, la règle pointe dessus (`≥ 1` → couleur), la colonne booléenne normale reste affichée dans le visuel. Déjà fait pour `dim_contact[doublon_num]` (rapport 3) — à répliquer ailleurs si besoin.
