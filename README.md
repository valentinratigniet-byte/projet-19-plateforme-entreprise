# Projet 19 — Plateforme data d'entreprise multi-domaines

> **🚧 Cadrage posé, implémentation pas commencée.** Cadrage complet dans
> l'issue [valentinratigniet-byte/valentinratigniet-byte#2](https://github.com/valentinratigniet-byte/valentinratigniet-byte/issues/2)
> (architecture, intérêt par poste cible, doctrine, phasage) — source de
> vérité, à lire en premier. Ce README sera réécrit au fil de
> l'implémentation pour ne documenter que ce qui est **réellement construit
> et vérifié**, jamais le plan seul (même discipline que le
> [Projet 18](https://github.com/valentinratigniet-byte/projet-18-monitoring-energie-rte)).

## 🎯 Problème métier

Trois bases "de production" simulées mais délibérément hétérogènes et mal
fichues (Ventes/Commerce, Finance/Compta, Marketing/Activité) — chacune
vivante via un simulateur d'usage sur plusieurs mois simulés, pour que le
volume et les vrais problèmes (bloat, index inutilisés, doublons)
émergent de l'usage plutôt que d'être injectés à la main. L'objectif :
les rendre exploitables — nettoyage, ETL/ELT, entrepôt en modèle
**constellation** (dimensions partagées, plusieurs faits), RLS
multi-rôles réelle, documentation vivante, connectique de visualisation
multiple, et un volet **housekeeping** (index/bloat) intégré nativement,
pas en périphérie.

**Ambition assumée** : le plus gros projet solo du portfolio à ce jour,
comparable en ampleur au projet binôme
[projet-baptiste-valentin](https://github.com/valentinratigniet-byte/projet-baptiste-valentin)
mais fait seul — voir l'issue de cadrage pour le détail.

## 🗂️ Architecture cible (cf. issue #2)

```mermaid
flowchart LR
    subgraph Sources["3 bases sources (simulateurs d'usage)"]
        V["Ventes/Commerce"]
        F["Finance/Compta"]
        M["Marketing/Activité"]
    end
    Sources --> ETL["ELT (dbt)\nnettoyage + standardisation"]
    ETL --> DWH["Entrepôt — modèle constellation\ndimensions partagées + faits multiples"]
    DWH --> BI["Power BI + Metabase"]
    DWH --> FIL["Filiation (lignage)"]
    HERMES["Hermès Agent\n(VPS/Coolify du Projet 18)"] -.surveille.-> ETL
    HERMES -.surveille.-> DWH
```

Infra réutilisée, pas recréée : VPS + Coolify + n8n déjà en place depuis le
[Projet 18](https://github.com/valentinratigniet-byte/projet-18-monitoring-energie-rte).

## 🚀 Phasage (par domaine, pas par couche technique)

1. Infra partagée (VPS/Coolify existant + Hermès Agent)
2. Domaine 1 — Ventes/Commerce, bout en bout (source sale → nettoyage → staging → fait → RLS → doc)
3. Domaine 2 — Finance/Compta
4. Domaine 3 — Marketing/Activité (volume + housekeeping à grande échelle)
5. Consolidation constellation + dictionnaire global + connectique multi-domaines
6. Housekeeping transverse (index/bloat sur les 3 sources + l'entrepôt)
7. Filiation branché

**Doctrine "tentaculaire mais chirurgical"** (reprise et étendue du Projet 18) :
un seul domaine construit et validé de bout en bout avant de lancer le
suivant — jamais plusieurs chantiers à moitié faits en parallèle.

## 🗃️ Structure du repo (à ce stade)

```
projet-19-plateforme-entreprise/
├── README.md
└── LICENSE
```

Se remplira domaine par domaine au fil des phases — voir l'issue #2 pour
le détail de chaque brique (simulateurs d'usage, dbt, RLS, Hermès Agent,
connectique).

---

*Projet 19 du [Portfolio Data](https://github.com/valentinratigniet-byte). Réutilise l'infra du
[Projet 18](https://github.com/valentinratigniet-byte/projet-18-monitoring-energie-rte). Cadrage :
[issue #2](https://github.com/valentinratigniet-byte/valentinratigniet-byte/issues/2).*
