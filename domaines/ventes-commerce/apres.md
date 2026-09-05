# Ventes/Commerce — état nettoyé et résultats

## Ce qui a été fait

AS/400 (fichier plat) + Excel (grille de remises) → adaptateurs
d'ingestion → `raw` (copie brute) → snapshots dbt (historisation SCD2) →
`staging` (nettoyage documenté) → `marts` (`dim_client`, `fait_ventes`) →
RLS multi-rôles vérifiée. Pipeline complet, vérifié à chaque étape (cf.
`docs/guide-realisation.md`), 14/14 tests dbt passent.

## Résultats chiffrés

| Indicateur | Avant | Après |
|---|---|---|
| Clients | 314 (28 doublons non résolus, mesuré — voir `avant.md`) | 314 (doublons flagués, visibles) |
| Commandes | 2320 (dates sur 2 formats, statuts en 7 variantes) | 2320 (1 format, 3 statuts + INCONNU) |
| Commandes avec client non identifié | ~3 %, non signalé | ~3 %, flaguées (`client_connu = false`) explicitement |
| Chiffre d'affaires HT | non calculable de façon fiable (montants en centimes-texte) | **15 092 645,63 €** |
| Chiffre d'affaires net (remises appliquées) | — | **15 063 193,73 €** |
| Remises négociées rattachées à un client AS/400 | 0 (aucune clé commune) | 3 sur 16 (19 %), avec confiance mesurée |

## Constat honnête sur les remises

Le rapprochement flou (`pg_trgm`, similarité de trigrammes) ne rattache
que **3 des 16 remises négociées** à un client AS/400 avec un niveau de
confiance jugé fiable (seuil 0,5, relevé après avoir mesuré 2 faux
positifs au seuil initial de 0,4). Ce n'est pas un échec du pipeline :
c'est une vraie limite du rapprochement automatique par nom, révélée
plutôt que masquée. Les 13 remises restantes n'affectent pas
`fait_ventes` (pas de remise fantôme appliquée), mais restent
concrètement non exploitées côté pilotage.

## Recommandations pour l'équipe Commerce

1. **Rattacher les remises à un `CLICOD`, pas à un nom tapé à la main.**
   La grille Excel devrait référencer l'identifiant AS/400 dès la
   négociation — élimine le besoin de rapprochement flou et son taux
   d'échec structurel.
2. **Unifier les deux fichiers de remises en un seul, avec historique.**
   La coexistence `v3`/`v4_FINAL` a produit ~40 % de valeurs divergentes
   sur les clients communs — un tableur partagé avec un journal de
   versions (ou directement dans l'entrepôt via `dim_client`) éviterait
   ce désaccord silencieux.
3. **Traiter les 28 doublons clients identifiés** (`est_doublon_probable`)
   — décision de fusion à valider côté équipe commerciale (quel
   enregistrement fait foi), pas automatisable sans arbitrage métier.
4. **Les ~3 % de commandes avec client inconnu** méritent une revue :
   client supprimé du référentiel après la commande ? Erreur de saisie
   du code ? Le flag `client_connu = false` permet de les isoler pour
   investigation, déjà disponible dans `marts.fait_ventes`.
