# Finance/Compta — état nettoyé et résultats

## Ce qui a été fait

SQL Server (fournisseurs + écritures) + CSV (relevé bancaire) + Factur-X
(factures reçues, 2 canaux) → adaptateurs d'ingestion → `raw` → snapshot
dbt (SCD2 fournisseurs) → `staging` (nettoyage documenté) → `marts`
(`dim_fournisseur`, `fait_ecritures`, `fait_rapprochement_factures`) →
RLS multi-rôles + sécurité colonne vérifiées. 26/26 tests dbt passent.

## Résultats chiffrés

| Indicateur | Avant | Après |
|---|---|---|
| Fournisseurs | 80 (8 SIREN invalides/absents) | 80 (SIREN normalisé et flagué) |
| Écritures comptables | 866 (11 doublons de saisie exacts inclus) | **855** (doublons supprimés) |
| Montant HT total | non calculable de façon fiable (2 formats texte) | **6 033 449,03 €** |
| Montant TTC total | — | **7 240 138,82 €** |
| Factures reçues rattachées à une écriture (Factur-X) | — | **91 % (387/426)** |
| Factures reçues rattachées à une écriture (non structuré) | — | **44 % (190/428)** |
| Accès à l'IBAN fournisseur | non contrôlé | `role_finance` uniquement (colonne restreinte) |

## Constat honnête sur le rapprochement facture/écriture

L'écart entre 91 % (Factur-X) et 44 % (non structuré) n'est pas un
artefact — c'est directement lié à la qualité des données disponibles par
canal : le canal non structuré perd le SIREN dans 60 % des cas et produit
un montant illisible dans 15 % des cas, rendant le rapprochement
automatique structurellement moins fiable. C'est une mesure du **coût
réel du papier/PDF non structuré**, pas une limite du pipeline.

## Recommandations pour l'équipe Finance/Compta

1. **Accélérer la migration Factur-X des fournisseurs restants.** L'écart
   mesuré (91 % vs 44 % de rapprochement automatique) est un argument
   chiffré direct : chaque fournisseur non migré représente un volume de
   factures qui nécessitera une saisie manuelle de rapprochement.
2. **Ne pas se fier au numéro de facture pour un rapprochement automatique
   inter-systèmes.** L'ERP et les fournisseurs ne partagent pas la même
   numérotation — tout projet futur de rapprochement doit passer par
   SIREN + montant, comme fait ici, pas par numéro.
3. **Corriger l'import legacy qui mélange les formats numériques FR/US**
   côté SQL Server (~15 % des écritures) — un import mal configuré,
   pas une contrainte structurelle, facilement corrigeable côté ERP.
4. **Les ~2 % d'écritures avec fournisseur inconnu** méritent une revue
   (référentiel désynchronisé ?) — isolées via `fournisseur_connu = false`
   dans `marts.fait_ecritures`, prêtes pour investigation.
5. **L'IBAN reste un actif sensible** : la restriction d'accès mise en
   place (colonne, pas juste ligne) devrait s'étendre à tout futur usage
   de cette donnée dans les outils de visualisation connectés à
   l'entrepôt.
