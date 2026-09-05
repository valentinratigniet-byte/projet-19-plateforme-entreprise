# Analyse transverse — Phase 5

Le fil narratif qui a motivé le choix des 3 domaines dès le cadrage
([issue #2](https://github.com/valentinratigniet-byte/valentinratigniet-byte/issues/2)) :
campagne marketing → impact ventes → écart budgétaire finance. Ce document
présente ce qui a été **réellement mesuré** sur les données entreposées
de ce projet — y compris ce qui n'a **pas** été trouvé, plutôt que de
forcer une conclusion.

## 1. Écart budgétaire Ventes — méthode Prix/Volume (Projet 15)

Réutilise directement la décomposition du
[Projet 15](https://github.com/valentinratigniet-byte/projet-15-reporting-ecarts-cg),
appliquée ici sur les vraies données Ventes de ce projet
(`marts.ecart_budget_ventes`), face à un budget hypothèse clairement
labellisée (+8 %/mois depuis 3 500 unités, prix cible 255 €/unité — cf.
`dbt/seeds/budget_ventes_2026.csv`).

| Mois | Écart volume | Écart prix | Écart total |
|---|---|---|---|
| 2026-01 | -13 260 € | +54 777 € | +41 517 € |
| 2026-02 | +253 980 € | +35 084 € | +289 064 € |
| 2026-03 | +200 430 € | +77 330 € | +277 760 € |
| 2026-04 | +503 115 € | -91 493 € | +411 622 € |
| 2026-05 | +679 065 € | -134 102 € | +544 963 € |
| 2026-06 | +659 685 € | -93 938 € | +565 747 € |
| 2026-07 | +850 935 € | +7 097 € | +858 032 € |
| 2026-08 | +852 465 € | +126 993 € | +979 458 € |

**Lecture** : l'écart volume devient massivement favorable à partir
d'avril — la croissance réelle des commandes dépasse largement
l'hypothèse prudente posée en janvier (+8 %/mois). L'écart prix est plus
volatil (favorable en janvier/février/juillet/août, défavorable
avril-juin), cohérent avec les fluctuations de prix moyen réel déjà
documentées dans `domaines/ventes-commerce/apres.md`. **Ce n'est pas un
vrai budget négocié** — même limite assumée que le Projet 15, l'écart
mesuré face à la réalité est réel, le point de comparaison est une
hypothèse.

## 2. Recherche d'une corrélation marketing → ventes

`marts.synthese_mensuelle_transverse` met les 3 domaines côte à côte sur
la même grille mensuelle :

| Mois | Clics marketing | CA Ventes | Dépenses Finance |
|---|---|---|---|
| 2026-01 | 27 | 934 017 € | 429 578 € |
| 2026-02 | 26 | 1 252 964 € | 694 730 € |
| 2026-03 | 37 | 1 318 670 € | 622 352 € |
| 2026-04 | 29 | 1 535 917 € | 803 397 € |
| 2026-05 | 30 | 1 759 273 € | 1 021 079 € |
| 2026-06 | 25 | 1 877 212 € | 1 093 703 € |
| 2026-07 | 36 | 2 274 302 € | 1 177 230 € |
| 2026-08 | 32 | 2 509 203 € | 1 398 070 € |

**Constat honnête : aucune corrélation visible.** Les clics marketing
oscillent sans tendance (25 à 37, pas de croissance) pendant que le CA
Ventes croît de +169 % sur la période. Ce n'est pas un échec de l'analyse
— c'est une vraie découverte, à ne pas maquiller :

**Cause structurelle identifiée** : les domaines Ventes/Commerce et
Marketing/Activité **n'ont aucune entité commune**. Les "clients" de
l'AS/400 (comptes B2B gérés par un commercial) et les "contacts" MySQL du
CRM marketing (individus ciblés par campagne email) sont deux populations
distinctes dans ce modèle — un `contact_id` marketing ne se rapproche
d'aucun `clicod` Ventes. Chercher une causalité entre les deux revient
donc à comparer deux processus indépendants, ce qui explique
mécaniquement l'absence de signal. La croissance du CA Ventes s'explique
plus simplement par la croissance organique du volume de commandes
injectée dans le simulateur AS/400 (150 → 430 commandes/mois sur la
période), sans lien avec l'activité marketing.

## 3. Contexte Finance

Les dépenses comptabilisées (`marts.fait_ecritures`) croissent elles
aussi sur la période (429 k€ → 1,4 M€), cohérent avec la croissance
générale de l'activité. La marge brute approximative
(CA Ventes − dépenses Finance, à prendre avec précaution : les deux
domaines n'ont pas de lien garanti non plus, cf. point 2) passe de
504 k€ à 1,1 M€ sur la période.

## 4. Recommandation clé — la vraie prochaine étape de consolidation

Pour qu'une analyse causale marketing → ventes soit un jour possible, il
manque une **dimension "tiers" partagée** entre les domaines — un
identifiant qui reconnaît qu'un même client final peut exister à la fois
comme compte AS/400 (Ventes) et comme contact CRM (Marketing). C'est le
vrai chantier de "connectique multi-domaines" que ce projet met en
évidence, pas une intégration technique triviale : ça suppose une
politique de rapprochement d'entités (nom, email, SIREN pour le
B2B — même famille de problème que le rapprochement flou déjà fait dans
`domaines/ventes-commerce/` et `domaines/finance-compta/`), pas encore
fait ici. Recommandation : en faire un chantier dédié avant toute
tentative future d'attribution marketing → revenu.

## 5. Dictionnaire de données et connectique

Le dictionnaire global est généré via `dbt docs generate` (catalogue +
graphe de lineage complet sur les 24 modèles / 3 snapshots / 51 tests du
projet) — vérifié fonctionnel, alimente `entrepot/`. La connectique de
visualisation (Power BI/Metabase) se branche sur les marts déjà exposés
avec RLS (`marts.*`), aucune configuration supplémentaire requise côté
entrepôt.
