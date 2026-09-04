# Domaine Ventes/Commerce

**✅ Phase 2 terminée et vérifiée** (2026-09-05) — le premier domaine
construit bout en bout, selon la doctrine "tentaculaire mais
chirurgical" du [phasage](../../README.md#-phasage-par-domaine-pas-par-couche-technique).

Sources : AS/400 (DB2 for i, export batch fichier plat, simulé — cf.
[issue #2](https://github.com/valentinratigniet-byte/valentinratigniet-byte/issues/2)
pour le raisonnement) + Excel manuel (grille de remises négociées, 2
versions concurrentes).

## Ce qui est construit et vérifié

- **`source/`** — simulateurs d'usage (`simulateur_as400.py`,
  `simulateur_excel_remises.py`), défauts réels générés (dérive de date,
  doublons, FK partielle, formule cassée).
- **Ingestion** → `raw` (schéma brut, copie 1:1) — conteneurisée,
  idempotente (manifeste de fichiers ingérés).
- **dbt** — snapshot SCD2 sur les clients, staging (3 modèles, règles de
  nettoyage réelles), marts (`dim_client`, `fait_ventes`) — **14/14 tests
  passent**.
- **RLS multi-rôles** (`role_rh`/`role_finance`/`role_direction`/
  `role_commercial`) — **8/8 cas vérifiés par `SET ROLE`**, survit aux
  reruns dbt (post_hook).
- **Workflow n8n** — export prêt (`n8n/ventes-commerce-ingestion-workflow.json`),
  import manuel restant.

## Documentation

[`avant.md`](avant.md) (état brut chiffré) · [`decisions.md`](decisions.md)
(raisonnement, 7 étapes) · [`regles-transformation.md`](regles-transformation.md)
(brut → net, colonne par colonne) · [`apres.md`](apres.md) (résultats +
recommandations pour l'équipe Commerce).

Détail complet de la construction, y compris les bugs rencontrés et
corrigés, dans [`docs/guide-realisation.md`](../../docs/guide-realisation.md).
