# Finance/Compta — journal de décisions

Format : **donnée concernée → décision → pourquoi → alternative écartée**,
en 7 étapes, cf. cadrage ([issue #2](https://github.com/valentinratigniet-byte/valentinratigniet-byte/issues/2)).

## 1. Identification

- **SQL Server** → source principale, l'ERP comptable lui-même (pas un
  export) → parce que c'est la réalité d'un ERP comptable moderne
  (Sage, Cegid, SAP Business One tournent sur SQL Server) → alternative
  écartée : simuler un export fichier comme l'AS/400 (aurait été
  redondant avec le domaine Ventes, moins réaliste pour ce type de
  système).
- **Factur-X** → identifié comme le canal de réception des factures
  fournisseurs, distinct de l'ERP → parce que c'est la vraie
  transformation en cours en France (réforme facturation électronique)
  → alternative écartée : ignorer la coexistence transitoire
  Factur-X/PDF (aurait manqué l'angle le plus actuel du domaine).

## 2. Compartimentation / sectorisation

- **Écritures/fournisseurs** → `role_rh` exclu (aucune justification
  métier), `role_finance`/`role_direction` accès complet → même logique
  que Ventes/Commerce.
- **IBAN des fournisseurs** → NOUVEAU par rapport à Ventes : restriction
  **au niveau colonne**, pas seulement ligne → `role_direction` n'a pas
  besoin de la donnée bancaire brute pour piloter, `role_finance` en a
  l'usage opérationnel (paiements) → alternative écartée : tout
  accorder à `role_direction` par simplicité (aurait exposé une donnée
  sensible sans besoin métier réel).

## 3. Extraction

- **SQL Server** → adaptateur générique `sqlserver.py` (`pymssql`) →
  réutilisable pour tout futur domaine sur cette techno → limite
  acceptée : édition Developer (gratuite, 0€), pas de licence
  production réelle.
- **CSV bancaire** → adaptateur générique `csv_file.py`, délimiteur
  configurable → le point-virgule (convention française) casserait un
  parseur CSV qui suppose une virgule par défaut, d'où la nécessité de
  ce paramètre.
- **Factur-X + non structuré** → **un seul adaptateur** (`facturx.py`)
  pour les deux canaux → parce que c'est la même source métier
  (facturation entrante), pas deux sources différentes → alternative
  écartée : deux adaptateurs séparés (aurait dupliqué la logique de
  traitement du champ `canal`, qui est justement ce qui les relie).

## 4. Traitement

- **Montants texte FR/US (SQL Server)** → normalisation espaces/virgule
  → point, cast numeric → pas de format canonique unique dans le
  brut, les deux coexistent réellement → alternative écartée : rejeter
  les lignes au format inattendu (aurait perdu ~15 % des écritures).
- **Doublons de saisie exacts (écritures)** → **supprimés**, contrairement
  aux commandes Ventes qui sont conservées telles quelles → parce que ce
  sont ici de vrais doublons de SAISIE (double-clic), pas des
  enregistrements distincts à valeur métier → alternative écartée :
  garder tous les doublons comme pour Ventes (aurait faussé les totaux
  comptables, qui doivent être exacts par nature).
- **Numéro de facture** → PAS utilisé pour le rapprochement
  facture/écriture → l'ERP et le fournisseur ne partagent pas la même
  numérotation (constat réel, pas une supposition) → alternative
  écartée : forcer un rapprochement par numéro normalisé (aurait produit
  des correspondances fausses ou aucune, les deux mauvaises).

## 5. Nettoyage

- **SIREN** → normalisé (espaces supprimés) et flaggé valide/invalide,
  pas rejeté → un fournisseur reste exploitable même sans SIREN correct
  → alternative écartée : exiger un SIREN valide pour toute jointure
  (aurait exclu 10 % des fournisseurs de toute analyse).
- **Montant illisible côté facture non structurée** → conservé `NULL`,
  jamais deviné → une facture sans montant lisible ne doit pas fausser
  un total → alternative écartée : estimer le montant à partir d'une
  moyenne (aurait fabriqué un chiffre comptable, inacceptable sur ce
  domaine).

## 6. Entreposage

- **Génération des événements canoniques partagés
  (`generer_evenements.py`)** → décision prise APRÈS avoir mesuré un
  bug réel : la première version générait les montants SQL Server et
  Factur-X de façon indépendante, donnant un taux de rapprochement
  quasi nul (~2%) qui n'était pas une vraie découverte mais un artefact
  du simulateur → corrigé en partageant une liste d'événements réels
  (même fournisseur, même montant) entre les deux simulateurs, avec une
  couverture volontairement imparfaite (90% des deux, 5%+5% d'un seul
  côté) → alternative écartée : garder les montants indépendants et
  documenter un "taux de rapprochement de 2%" comme si c'était un vrai
  résultat (aurait été un mensonge par omission).
- **RLS + colonne sur `dim_fournisseur`** → décision technique corrigée
  après un bug Postgres réel : un `GRANT SELECT` global sur la table
  neutralise un `REVOKE SELECT (colonne)` posé après (vérifié via
  `has_column_privilege`) → corrigé en n'accordant jamais le SELECT
  global à `role_direction`, seulement les colonnes explicites (IBAN
  exclue) → alternative écartée : garder le GRANT+REVOKE en pensant
  que ça fonctionnait (aurait laissé une fausse sécurité en production).

## 7. Exploitation

- **`fait_rapprochement_factures`** → donnée clé pour l'analyse
  transverse (Phase 5) et pour Finance : identifie concrètement quelles
  factures nécessitent une saisie manuelle (canal non structuré, 56 %
  non rattachées).
- **Recommandation issue de ce domaine** → cf. `apres.md` : l'écart de
  taux de rapprochement (91 % vs 44 %) est un argument chiffré direct
  pour accélérer la migration Factur-X côté fournisseurs restants.
