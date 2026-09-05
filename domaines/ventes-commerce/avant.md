# Ventes/Commerce — état brut

Deux sources, simulées mais délibérément sales
(`source/simulateur_as400.py`, `source/simulateur_excel_remises.py`),
chargées telles quelles dans `raw` (schéma brut, copie 1:1) — aucune
transformation à ce stade.

## AS/400 (clients + commandes)

| Métrique | Valeur |
|---|---|
| Clients (fichier `CLIENTS_AS400`) | 314 |
| dont doublons probables (variante de saisie) | 28 (8,9 %) — mesuré en base le 2026-09-05 en construisant `ops/verifier_derive_qualite.py` ; corrige un chiffre précédemment documenté (14, 4,5 %) qui datait d'une génération antérieure des données et n'a pas été revérifié depuis |
| Commandes (8 mois simulés, 2026-01 à 2026-08) | 2320 |
| Commandes avec `CLICOD` orphelin (client absent du fichier clients) | ~3 % |
| Mois avec dérive de format de date (DDMMYYYY au lieu de YYYYMMDD) | 2 (2026-03, 2026-04) |
| Variantes orthographiques du statut de commande | `VAL`/`Val`/`VALID`, `LIV`/`Liv`/`LIVR`, `ANN`/`ANNUL`/`Ann` |

Défauts confirmés dans le contenu réel des fichiers générés, pas
seulement documentés en théorie (cf. `docs/guide-realisation.md`).

## Excel — grille de remises négociées

| Métrique | Valeur |
|---|---|
| Fichiers concurrents | 2 (`remises_ventes_v3.xlsx`, `remises_ventes_v4_FINAL.xlsx`) |
| Clients avec remise (union des 2 fichiers) | 16 noms saisis à la main |
| Remises qui divergent entre v3 et v4 pour le même client | ~40 % des cas communs aux deux fichiers |
| Formule cassée (`#REF!` à l'ouverture) | 1 ligne |
| Clients référencés par CLICOD AS/400 | 0 — uniquement par nom tapé à la main |

## Score qualité initial

- **Identifiants** : 0 clé commune fiable entre l'Excel (noms) et l'AS/400
  (`CLICOD`) — rapprochement à construire, pas donné.
- **Cohérence temporelle** : 25 % des mois simulés (2/8) ont un format de
  date différent du reste, sans indicateur explicite dans le fichier.
- **Fiabilité des remises** : aucune version de référence entre les 2
  fichiers Excel — conflit réel, pas résolu à la source.
