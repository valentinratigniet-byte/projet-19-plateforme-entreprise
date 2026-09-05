# Finance/Compta — état brut

Trois sources, simulées mais délibérément hétérogènes et sales
(`source/simulateur_sqlserver.py`, `source/simulateur_csv_banque.py`,
`source/simulateur_facturx.py`), chargées telles quelles dans `raw` —
aucune transformation à ce stade.

## SQL Server (fournisseurs + écritures comptables)

| Métrique | Valeur |
|---|---|
| Fournisseurs | 80 |
| dont SIREN invalide ou absent | 1 (1,3 %) — mesuré en base le 2026-09-05 en construisant `ops/verifier_derive_qualite.py` ; corrige un chiffre précédemment documenté (8, 10 %) qui datait d'une génération antérieure des données et n'a pas été revérifié depuis |
| Écritures comptables (8 mois simulés) | 866 |
| dont montants stockés en texte format FR (virgule) | ~15 % |
| dont `FournisseurID` orphelin | ~2 % |
| dont doublons de saisie exacts (double-clic comptable) | 11 lignes |

## CSV — relevé bancaire mensuel

| Métrique | Valeur |
|---|---|
| Lignes (8 mois) | 553 |
| Libellé référençant le fournisseur par nom complet | 0 — uniquement extrait tronqué |
| Lignes strictement dupliquées (rejeu d'export) | ~2 % |

## Factur-X — factures fournisseurs reçues

| Métrique | Valeur |
|---|---|
| Factures reçues (8 mois) | 854 |
| Canal Factur-X (structuré, XML) | 426 (50 %) |
| Canal non structuré (PDF/OCR dégradé) | 428 (50 %) |
| Taux de migration Factur-X | croissant, 20 % (janvier) → 65 % (août) |
| SIREN absent côté non structuré | ~60 % des factures de ce canal |
| Montant illisible côté non structuré | ~15 % des factures de ce canal |

## Constat sur le rapprochement facture ↔ écriture

Les deux sources (écritures SQL Server, factures reçues) **ne partagent
pas la même numérotation** : l'ERP assigne sa propre référence interne
(`FA202601XXXX`), le fournisseur numérote à sa façon
(`FA-2026-01-XXX`) — rapprocher par numéro de facture est structurellement
impossible, constaté avant même de nettoyer quoi que ce soit. Le
rapprochement doit passer par SIREN + montant, pas par numéro.

## Score qualité initial

- **Identifiants** : 10 % des fournisseurs n'ont pas de SIREN exploitable
  directement (absent ou mal formé).
- **Cohérence de format** : montants sur 2 formats numériques différents
  côté SQL Server (texte FR vs US), aucun indicateur de format dans le
  fichier lui-même.
- **Fiabilité du canal non structuré** : SIREN absent dans 6 cas sur 10,
  montant illisible dans 1,5 cas sur 10 — une facture sur deux reçue par
  ce canal est difficilement exploitable automatiquement.
