# Marketing/Activité — journal de décisions

Format : **donnée concernée → décision → pourquoi → alternative écartée**.

## 1. Identification

- **MySQL (CRM/stack web)** → source principale, base live (pas un
  export) → parce que c'est la réalité d'une stack marketing/web
  moderne → alternative écartée : simuler un export fichier (aurait été
  moins réaliste pour ce type de système, déjà couvert par AS/400
  côté Ventes).
- **API SaaS** → identifiée comme le 4e type de source du projet, avec
  4 mécanismes poussés (push/pull, OAuth2, reverse ETL) → parce que
  c'est la réalité d'une équipe marketing qui utilise un outil externe
  (Mailchimp/Brevo) plutôt qu'un système interne pour l'envoi de
  campagnes → alternative écartée : simuler l'outil comme un simple
  fichier d'export (aurait manqué tout l'intérêt technique des
  mécanismes poussés validés dans le cadrage).

## 2. Compartimentation / sectorisation

- **Contacts (email, nom)** → NOUVEAU par rapport à Ventes/Finance :
  `role_direction` n'a **aucun accès**, pas seulement des lignes
  filtrées, sur `dim_contact`/`fait_envois`/`fait_evenements_web` →
  ce sont des données à caractère personnel, la Direction pilote sur
  des agrégats (`fait_performance_campagnes`), pas sur des fiches
  individuelles → alternative écartée : RLS ligne comme les autres
  domaines (aurait laissé un accès techniquement possible à une donnée
  personnelle sans besoin métier réel — principe de minimisation).
- **Stats agrégées** → accessibles à `role_marketing` ET
  `role_direction` → aucune donnée personnelle dans un agrégat par
  campagne.

## 3. Extraction

- **MySQL** → adaptateur générique `mysql.py` (`pymysql`) →
  réutilisable pour tout futur domaine sur cette techno.
- **JSON événementiel** → adaptateur générique `json_file.py`, avec
  aplatissement structurel des objets imbriqués → nécessité de stockage
  relationnel, pas une transformation de valeur.
- **API SaaS (OAuth2 + polling + webhook + reverse ETL)** → **un seul
  adaptateur** `api_rest.py`, générique (`ClientOAuth2`, gestion du
  refresh) → réutilisable pour toute future API du même type →
  alternative écartée : un adaptateur par mécanisme (aurait dupliqué la
  logique de gestion du jeton, commune aux 4 usages).
- **Jeton OAuth2 court (30s)** → délibérément court pour forcer un vrai
  cycle de refresh observable pendant le développement, pas seulement
  au démarrage → alternative écartée : jeton longue durée (aurait
  masqué un bug de refresh potentiel, jamais exercé en pratique).

## 4. Traitement

- **Statuts d'envoi FR/EN** → regroupés par préfixe → un stack
  marketing réel mélange souvent les conventions de nommage de
  plusieurs outils au fil du temps → alternative écartée : forcer un
  seul vocabulaire dès la source (aurait été irréaliste).
- **Typo UTM "emial"** → corrigée explicitement, une seule variante
  précise → alternative écartée : normalisation floue générale de
  toutes les fautes de frappe UTM possibles (aurait risqué de
  fusionner des sources réellement différentes sous couvert de
  correction).

## 5. Nettoyage

- **Mojibake sur les noms** → **flagué, pas réparé automatiquement** →
  une réparation SQL à l'aveugle (ré-encodage latin1→utf8) risquerait
  de fabriquer un texte faux sur des séquences d'octets invalides →
  alternative écartée : tenter la réparation en SQL avec gestion
  d'erreur (ajout de complexité pour un gain incertain — un vrai
  correctif relève de la source, pas d'un rattrapage aval).
- **Doublons de contacts** → flagués, pas fusionnés → même raisonnement
  que Ventes/Commerce : pas de règle de survivorship métier définie.
- **Événements web domain-dupliqués (~3%)** → **conservés tels quels**
  dans `fait_evenements_web` → un log d'événements brut garde tout ce
  qui a été reçu, le dédoublonnage est une décision d'analyse
  spécifique (ex. sessions uniques), pas une règle de nettoyage
  générale à appliquer par défaut.

## 6. Entreposage

- **Vérification croisée SaaS ↔ MySQL** (`fait_performance_campagnes`)
  → décision de calculer les deux et de les comparer, plutôt que de
  faire confiance à une seule source → révèle une vraie cohérence
  (8/8), pas supposée → alternative écartée : ne garder que les stats
  SaaS sans vérification (aurait fait confiance à une boîte noire sans
  contrôle).
- **RLS en post_hook dbt** → même raison que les 2 autres domaines
  (DROP+CREATE à chaque `dbt run`).

## 7. Exploitation

- **Reverse ETL** → segment "contacts engagés non désabonnés" (124
  contacts) repoussé vers le SaaS pour une campagne de relance ciblée
  → boucle explicitement DE → BA → action marketing concrète, pas
  seulement un rapport.
- **`fait_performance_campagnes`** → seul mart du domaine consultable
  par la Direction pour le pilotage, cohérent avec la restriction
  d'accès décidée à l'étape 2.
