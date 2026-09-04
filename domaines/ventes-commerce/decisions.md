# Ventes/Commerce — journal de décisions

Format : **donnée concernée → décision → pourquoi → alternative écartée**,
en 7 étapes (Identification → Exploitation), cf. cadrage
([issue #2](https://github.com/valentinratigniet-byte/valentinratigniet-byte/issues/2)).

## 1. Identification

- **AS/400 (clients + commandes)** → simulé en export batch fichier plat
  (largeur fixe) → parce que c'est la vraie pratique terrain d'un atelier
  AS/400 (job batch nocturne, pas de connexion SQL directe possible sans
  licence IBM i) → alternative écartée : connexion DB2/400 live (coût
  licence, hors cadrage 0€).
- **Grille de remises** → identifiée comme un fichier Excel tenu par
  l'équipe commerciale, hors AS/400 → parce que c'est le cas réel le plus
  fréquent de "shadow IT" en gestion commerciale → alternative écartée :
  ignorer cette source (aurait laissé un angle mort sur les remises
  négociées).

## 2. Compartimentation / sectorisation

- **Client/commande** → domaine Ventes/Commerce, sensibilité "métier
  standard" (pas de données personnelles sensibles au sens RGPD) →
  accessible à `role_finance`/`role_direction`/`role_commercial` →
  `role_rh` explicitement exclu (aucune justification métier).
- **Commandes ANNULEE** → visibles par Finance/Direction (réconciliation
  budgétaire, dépréciations) mais pas par le rôle commercial opérationnel
  → alternative écartée : les masquer à tout le monde (aurait empêché
  Finance de faire son travail).

## 3. Extraction

- **Fichier plat AS/400** → adaptateur générique `fichier_plat.py`
  (largeur fixe) → réutilisable pour tout futur domaine avec ce type de
  source → alternative écartée : parseur spécifique au domaine (aurait
  dupliqué la logique).
- **Excel** → adaptateur générique `excel.py`, `data_only=False` →
  garde les formules cassées visibles comme texte plutôt que de les
  faire disparaître silencieusement → alternative écartée :
  `data_only=True` (aurait masqué le vrai défaut de la formule `#REF!`).
- **Écriture en `raw`** → colonnes en `TEXT`, jamais typées à l'ingestion
  → le typage est une décision de nettoyage documentée, pas un choix
  silencieux de l'adaptateur → limite acceptée consciemment : oblige
  chaque règle de typage à être écrite explicitement en staging.

## 4. Traitement

- **Format de date `CMDDAT`** → YYYYMMDD tenté en premier, repli DDMMYYYY
  si implausible → parce que la dérive réelle constatée (2 mois sur 8)
  n'est signalée par aucun indicateur dans le fichier lui-même →
  alternative écartée : forcer un seul format et rejeter les lignes en
  échec (aurait perdu 2 mois de commandes réelles).
- **Statuts de commande** → regroupés par préfixe (`VAL%`/`LIV%`/`ANN%`)
  plutôt qu'une table de correspondance exhaustive → plus robuste à de
  nouvelles variantes non anticipées → alternative écartée : liste
  figée de correspondances exactes (aurait cassé au premier statut non
  prévu).
- **Réconciliation v3/v4 des remises** → le fichier le plus récent gagne
  (`v4_FINAL` > `v3`) → hypothèse assumée en l'absence d'un vrai
  arbitrage métier disponible → alternative écartée : moyenne des deux
  valeurs (aurait inventé un chiffre sans justification).

## 5. Nettoyage

- **Doublons clients** → flagués (`est_doublon_probable`), pas fusionnés
  ni supprimés → une fusion automatique risquerait de perdre de la
  donnée sans validation métier → alternative écartée : dédoublonnage
  automatique façon Projet 12 (fuzzy matching + union-find) — pertinent
  mais pas fait ici, faute de règle de survivorship métier définie pour
  ce domaine.
- **`CLICOD` orphelin sur les commandes** → conservé avec flag
  `client_connu = false`, pas supprimé → la commande reste une donnée de
  chiffre d'affaires réelle même si le client n'est pas rattaché →
  alternative écartée : `INNER JOIN` silencieux (aurait fait disparaître
  ~3 % du chiffre d'affaires sans trace).
- **Formule Excel cassée** → détectée via regex, exclue du calcul
  (`remise_valide = false`) → évite de planter tout le modèle sur une
  seule ligne corrompue → alternative écartée : `TRY_CAST` silencieux
  (aurait masqué le problème au lieu de le rendre visible).

## 6. Entreposage

- **Rapprochement remise → client** → similarité de trigrammes
  (`pg_trgm`), seuil 0,5 → seuil relevé de 0,4 à 0,5 après avoir observé
  2 faux positifs réels au seuil initial (suffixe juridique commun
  "Sarl" gonflant artificiellement le score entre sociétés différentes)
  → alternative écartée : seuil 0,4 (aurait attribué une remise au
  mauvais client dans au moins 2 cas mesurés).
- **`marts.fait_ventes`** → grain = une commande, `montant_net_eur`
  calculé seulement si un rapprochement client fiable existe → mieux
  vaut une remise manquante qu'une remise fausse → alternative écartée :
  appliquer la remise moyenne du portefeuille par défaut (aurait
  fabriqué un chiffre).
- **RLS en `post_hook` dbt** plutôt qu'un script séparé → un modèle
  `table` fait `DROP`+`CREATE` à chaque `dbt run`, ce qui efface les
  policies posées à part (bug réel rencontré et vérifié) → alternative
  écartée : script RLS à rejouer manuellement après chaque run (fragile,
  s'oublie).

## 7. Exploitation

- **`fait_ventes`** → alimente l'analyse transverse (Phase 5, écart
  budgétaire) et les dashboards Finance/Direction → `role_commercial`
  l'utilise pour le suivi opérationnel (hors annulations).
- **Recommandation issue de ce domaine** → cf. `apres.md` : la
  réconciliation manuelle des 13 remises non rattachées automatiquement
  reste à faire côté équipe commerciale — l'outil signale le problème,
  il ne le résout pas à leur place.
