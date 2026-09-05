# Domaine Marketing/Activité

**✅ Phase 4 terminée et vérifiée** (2026-09-05) — troisième et dernier
domaine construit bout en bout, le plus riche fonctionnellement des trois.

Sources : MySQL (CRM/campagnes) + flux JSON événementiel (tracking web) +
API SaaS (webhook push + polling OAuth2 + reverse ETL). Détail du
raisonnement dans l'[issue #2](https://github.com/valentinratigniet-byte/valentinratigniet-byte/issues/2).

## Ce qui est construit et vérifié

- **`source/`** — `generer_evenements.py` (socle partagé contacts/
  campagnes/envois/événements pour un vrai funnel), simulateurs MySQL et
  JSON. **`saas-mock/`** — mock API SaaS (Flask) avec OAuth2, polling
  paginé, webhook, reverse ETL.
- **Ingestion** → `raw` — MySQL/JSON/stats SaaS, conteneurisée, idempotente.
- **dbt** — snapshot SCD2 contacts, 5 modèles staging, 4 marts
  (`dim_contact`, `fait_envois`, `fait_evenements_web`,
  `fait_performance_campagnes`) — **45/45 tests dbt du projet passent**,
  dont un test de cohérence SaaS ↔ MySQL.
- **RLS avec minimisation d'accès** — `role_direction` n'a **aucun accès**
  aux tables contenant des données personnelles (pas juste des lignes
  filtrées), seulement à l'agrégat `fait_performance_campagnes` —
  **9/9 cas vérifiés** par `SET ROLE` + tentative de lecture réelle.
- **4 mécanismes SaaS vérifiés réellement** : OAuth2 (refresh attendu en
  conditions réelles, 32s), polling paginé, webhook push (réception
  confirmée côté destinataire), **reverse ETL** (segment de 124 contacts
  engagés calculé dans l'entrepôt et confirmé reçu côté SaaS).
- **Workflow n8n** — export prêt (pull quotidien + webhook push).

## Trouvaille phare

**Vérification croisée SaaS ↔ MySQL : 8/8 campagnes cohérentes** — les
statistiques d'engagement rapportées par l'outil marketing et le
comptage indépendant depuis le CRM interne concordent exactement, un vrai
contrôle plutôt qu'une confiance aveugle en une seule source.

## Documentation

[`avant.md`](avant.md) · [`decisions.md`](decisions.md) (7 étapes) ·
[`regles-transformation.md`](regles-transformation.md) ·
[`apres.md`](apres.md) (résultats + 5 recommandations).

Détail complet de la construction dans
[`docs/guide-realisation.md`](../../docs/guide-realisation.md).

---

**Les 3 domaines du Projet 19 sont maintenant terminés** (Ventes/Commerce,
Finance/Compta, Marketing/Activité). Prochaine étape : Phase 5
(consolidation constellation + analyse transverse).
