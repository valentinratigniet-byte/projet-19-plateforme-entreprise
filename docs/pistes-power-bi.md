# Pistes Power BI — connecter l'entrepôt, pas encore fait

État réel (voir [`outils.md`](outils.md) et
[`anatomie-pipeline.md`](anatomie-pipeline.md#9-ce-qui-nest-délibérément-pas-montré-ici)) :
Power BI est **prêt côté entrepôt** (schéma `marts`, RLS déjà posée en
`post_hook` dbt) mais **pas encore connecté** à ce projet. Ce document liste
les rapports à construire, contre quels marts précis, et le point technique
à trancher avant le premier (le mapping RLS Postgres → Power BI).

## Point technique à trancher avant tout rapport

La RLS de ce projet est posée **côté Postgres**, par rôle (`role_finance`,
`role_direction`, `role_rh`, `role_commercial`, `role_marketing` —
`GRANT`/`CREATE POLICY` en post_hook, cf. `anatomie-pipeline.md#5`). Deux
façons de la faire respecter depuis Power BI, pas équivalentes :

| Option | Principe | Coût | Recommandé pour |
|---|---|---|---|
| **Import + RLS Power BI dupliquée** | Un connecteur unique (`dbt_transform` en lecture, comme pgHero), RLS *re-déclarée* dans Power BI (rôles + filtres DAX qui reproduisent les policies Postgres) | Double maintenance : toute évolution d'une policy Postgres doit être répercutée à la main côté Power BI | Rapports figés, faible fréquence de refresh, premier rapport à construire |
| **DirectQuery + rôle Postgres par viewer** | Chaque utilisateur Power BI se connecte avec ses propres identifiants Postgres (ou via RLS Power BI qui pousse un `SET ROLE` dynamique) | Nécessite soit des comptes Postgres nominatifs, soit `EffectiveUserName`/paramètre de connexion dynamique — plus proche de la doctrine "vérifié par `SET ROLE`" déjà appliquée ailleurs dans le projet | Rapport Finance (IBAN) et Direction, où la RLS n'est pas cosmétique |
| **Vue restreinte par rôle** | Une vue Postgres par rôle consommateur (`marts.dim_fournisseur_direction` sans `iban`), Power BI se connecte à la vue, pas à la table | Un objet Postgres de plus à maintenir en synchro avec le modèle dbt | Alternative si le mapping dynamique s'avère trop lourd à opérer |

Aucune de ces options n'est construite à ce jour — c'est le premier
chantier avant le rapport Finance/Direction ci-dessous, pas seulement un
détail de configuration.

## Rapports proposés

### 1. Ventes/Commerce — pilotage commercial

- **Sources** : `marts.fait_ventes`, `marts.dim_client`, `marts.dim_date`, `marts.ecart_budget_ventes`
- **Contenu** : CA HT par mois/région, top clients, statuts commande (les 3 canoniques + `INCONNU`, cf. `avant.md`/`apres.md` du domaine), écart budgétaire Prix/Volume déjà calculé dans le mart (pas à recalculer en DAX — la décomposition vit dans dbt)
- **RLS** : `role_commercial` (accès complet clients), `role_direction` (agrégats seulement)
- **Point d'attention réel** : les 13 remises Excel non rattachées à un client AS/400 (rapprochement flou `pg_trgm` à 19 % de confiance) doivent apparaître comme non affectées, pas comme un flag caché — cohérent avec la doctrine "flaguer, jamais masquer" du projet.

### 2. Finance/Compta — rapprochement factures & trésorerie

- **Sources** : `marts.fait_ecritures`, `marts.dim_fournisseur`, `marts.fait_rapprochement_factures`
- **Contenu** : montant TTC par compte comptable/statut de paiement, **taux de rapprochement par canal** (91 % Factur-X vs 44 % non structuré — l'indicateur le plus actionnable du domaine, cf. `apres.md`), fournisseurs à SIREN invalide à assainir
- **RLS** : `role_finance` (IBAN visible), `role_direction` (IBAN masqué — 4 colonnes explicites seulement, jamais `SELECT *`), `role_rh` (aucun accès)
- **Point d'attention réel** : c'est le rapport où le choix RLS ci-dessus n'est pas cosmétique — l'IBAN est une donnée bancaire sensible, le mauvais choix (Import + connecteur unique sans re-filtrage correct) l'exposerait à tous les viewers du rapport.

### 3. Marketing/Activité — performance campagnes

- **Sources** : `marts.fait_envois`, `marts.fait_performance_campagnes`, `marts.dim_contact`
- **Contenu** : taux d'ouverture/clic par campagne, cohérence stats SaaS vs MySQL (déjà vérifiée 8/8 côté dbt — le rapport l'affiche, ne la recalcule pas), volumétrie par statut d'envoi normalisé
- **RLS** : `role_marketing` (accès complet), `role_direction` — **aucun accès aux tables contact**, seulement à l'agrégat `fait_performance_campagnes` (minimisation RGPD déjà appliquée côté entrepôt, à ne pas contourner en exposant `dim_contact` dans ce rapport)

### 4. Support Client — SAV

- **Sources** : `marts.fait_tickets`
- **Contenu** : volumétrie par statut/priorité, délai de résolution, origine MongoDB (JSON imbriqué — vérifier que l'aplatissement staging n'a pas perdu de champ avant de publier des totaux)

### 5. Inventaire/Stock — ruptures et mouvements

- **Sources** : `marts.fait_mouvements_stock`, `marts.dim_stock_articles`
- **Contenu** : niveau de stock par article, mouvements entrée/sortie, **articles en stock négatif** — défaut réel du système source (Firebird, pas de validation temps réel côté ERP embarqué, cf. `outils.md`) à afficher tel quel, pas à corriger silencieusement dans le rapport.

### 6. Transverse Direction — vue consolidée

- **Sources** : `marts.synthese_mensuelle_transverse`, `marts.ecart_budget_ventes`
- **Contenu** : CA Ventes / dépenses Finance / clics Marketing sur la même grille mensuelle
- **Point d'attention réel, à afficher explicitement dans le rapport** : `analyse-transverse.md` a déjà mesuré **l'absence de corrélation** entre clics marketing et CA Ventes (pas d'entité commune entre les deux domaines à ce jour). Un rapport qui juxtapose les 3 courbes sans ce rappel laisserait croire à un lien qui n'a pas été trouvé — la bonne pratique ici est d'afficher le constat, pas de le taire pour un visuel plus vendeur.

### 7. Gouvernance qualité — les flags, pas les chiffres

- **Sources** : colonnes de flag déjà posées en staging sur les 5 domaines (`siren_valide`, `fournisseur_connu`, `contact_doublon_probable`, `date_format_derive`, `client_doublon_probable`...)
- **Contenu** : un rapport à part, pas noyé dans les autres — volumétrie de données flaguées par domaine et par type de défaut, pensé pour la personne qui doit *décider* une correction, pas pour la piloter au quotidien
- **Pourquoi celui-ci en particulier** : c'est le rapport qui rend visible la doctrine "flaguer, jamais corriger en silence" documentée dans `outils.md` — sans lui, les flags existent dans l'entrepôt mais personne ne les regarde.

## Ordre de construction suggéré

1. Trancher le point RLS ci-dessus (probablement Import + RLS dupliquée pour le premier rapport, le temps de vérifier le modèle — DirectQuery ensuite pour Finance).
2. **Ventes/Commerce** (rapport 1) — domaine le plus simple, pas de donnée sensible, sert de gabarit réutilisable pour les suivants.
3. **Finance/Compta** (rapport 2) — premier rapport où la RLS colonne compte réellement.
4. **Gouvernance qualité** (rapport 7) — transversal, réutilise les visuels déjà rodés sur les rapports 1-2.
5. Marketing, Support Client, Inventaire/Stock, Transverse Direction — dans l'ordre qui correspond au prochain domaine mis en avant, pas figé à l'avance (même doctrine que le reste du projet : le besoin réel avant le plan).

Une fois le premier rapport connecté, `docs/outils.md` et
`docs/bilan-projet.md` seront mis à jour pour refléter l'état réel — pas
avant, même discipline que le reste du projet.
