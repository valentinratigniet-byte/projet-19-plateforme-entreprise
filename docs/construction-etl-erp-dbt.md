# Construire ce projet — ETL, ERP, dbt

Vue transversale du [guide de réalisation](guide-realisation.md) (674 lignes,
écrites phase par phase) : plutôt que de relire chronologiquement les 7
phases, ce document extrait 3 fils — comment l'ingestion (ETL) a été
bâtie, comment les sources de type ERP ont été traitées, et quels pièges
dbt reviennent indépendamment du domaine — avec, pour chacun, comment le
refaire sans retomber dans le même bug. Les outils cités sont détaillés
dans [`docs/outils.md`](outils.md).

## 1. ETL — un adaptateur par type de source, pas par domaine

Le principe qui a tenu sur les 3 domaines sans jamais être réécrit : un
adaptateur par *type* de source (fichier plat, Excel, SQL Server, CSV,
Factur-X, MySQL, JSON, API REST), réutilisé tel quel où qu'il serve.
L'orchestration spécifique à un domaine reste un petit script séparé
(`domaines/<domaine>/ingestion.py`) qui appelle ces briques génériques.

**Le writer commun, écrit en premier.** Avant le premier adaptateur de
lecture, une seule fonction d'écriture Postgres (`ingestion/adaptateurs/
postgres_writer.py`), réutilisée par les 3 domaines : tout en `TEXT` (le
typage arrive en staging dbt, pas à l'ingestion), deux colonnes de
traçabilité ajoutées automatiquement (`_source_file`, `_ingested_at`).
Deux fonctions, un seul choix à faire par table :

```python
def remplacer_table(conn, schema, table, lignes, source_file):
    """TRUNCATE + reload -- pour une source qui exporte l'état
    courant complet à chaque fois (ex. fichier clients AS/400)."""
    ...

def ajouter_lignes(conn, schema, table, lignes, source_file):
    """Append, idempotent au niveau fichier -- un source_file déjà
    marqué ingéré est sauté, sinon rejouer le workflow n8n
    dupliquerait tout à chaque exécution."""
    if deja_ingere(conn, schema, table, source_file):
        return 0
    ...
```

**Construction, dans l'ordre réellement suivi :**

1. Le writer commun (ci-dessus) — sans lui, rien d'autre ne peut écrire dans `raw`.
2. Un lecteur par type de source — `fichier_plat.py`, `excel.py`, `sqlserver.py`, `csv_file.py`, `facturx.py`, `mysql.py`, `json_file.py`, `api_rest.py` (client OAuth2 avec refresh). Chacun ne fait qu'une chose : lire et retourner des lignes.
3. L'orchestration par domaine — choisit quelle table cible, quel adaptateur, et `remplacer_table` ou `ajouter_lignes` pour chaque source.
4. Conteneurisation — le VPS n'a ni `psycopg2` ni `openpyxl` installés nativement : image dédiée `projet19-ingestion` (216 Mo), pas d'installation système.
5. Orchestration n8n — un workflow par domaine, puis 7 workflows transverses (housekeeping, sauvegarde, vérification RLS post-déploiement, RGPD...).

**Pièges réels rencontrés :**

- **Idempotence oubliée au premier essai** — en relançant le script d'ingestion une 2ᵉ fois, `raw.ventes_commandes` a doublé : `ajouter_lignes` réinjectait tous les fichiers à chaque exécution. Corrigé avec une table manifeste `raw._fichiers_ingeres` (table cible + nom de fichier) — un fichier déjà ingéré est sauté.
- **Un rôle applicatif sans `CREATE SCHEMA`** — le rôle `ingestion` n'a que le droit de créer des tables dans un schéma déjà existant (moindre privilège décidé dès le cadrage). Corrigé en retirant la création de schéma du code : `raw` est déjà créé une fois par l'init de l'entrepôt.
- **Un en-tête Excel saisi à la main casse le SQL** — une colonne nommée `"Remise (%)"` contient un `%` qui casse le parsing de `psycopg2.extras.execute_values` une fois utilisée comme identifiant. Corrigé en sanitisant les *noms* de colonnes avant de les utiliser comme identifiants SQL — jamais les valeurs.

> **Pour refaire :** écrire le writer commun (avec son idempotence) avant
> le premier adaptateur spécifique, et tester la **2ᵉ exécution** d'un
> script d'ingestion avant de le considérer fini — la plupart des bugs
> d'ETL ne se voient qu'au deuxième passage, jamais au premier.

**Avant / après, mesuré — domaine Ventes/Commerce (AS/400 + Excel)**
(détail complet et méthode : [`avant.md`](../domaines/ventes-commerce/avant.md) /
[`apres.md`](../domaines/ventes-commerce/apres.md)) :

| Indicateur | Avant | Après |
|---|---|---|
| Clients | 314 (28 doublons non résolus) | 314 (doublons flagués, visibles) |
| Commandes | 2320 (dates sur 2 formats, statuts en 7 variantes) | 2320 (1 format, 3 statuts + `INCONNU`) |
| Chiffre d'affaires HT | non calculable (montants en centimes-texte) | **15 092 645,63 €** |
| Remises rattachées à un client AS/400 | 0 (aucune clé commune) | 3 sur 16 (19 %), avec confiance mesurée |

**Constat honnête** : le rapprochement flou (`pg_trgm`) ne rattache que 3
des 16 remises négociées avec un niveau de confiance jugé fiable — pas un
échec du pipeline, une vraie limite du rapprochement par nom révélée
plutôt que masquée. Les 13 remises restantes n'affectent pas
`fait_ventes` (pas de remise fantôme appliquée), mais restent
concrètement non exploitées côté pilotage tant qu'un `CLICOD` n'est pas
saisi à la source.

## 2. ERP — la source qu'on ne touche jamais

Deux systèmes se comportent comme un vrai ERP : SQL Server (Finance/Compta,
*littéralement* l'ERP comptable — fournisseurs et écritures y sont peuplés
directement, pas exportés en fichier) et l'AS/400 (Ventes/Commerce, ERP de
gestion commerciale, traité en export batch, jamais en connexion directe).

**Lire un ERP, sans jamais y écrire** (`ingestion/adaptateurs/sqlserver.py`,
code réel, intégral) :

```python
"""Adaptateur générique -- SQL Server. Un seul lecteur réutilisable,
pas un par domaine."""
import pymssql

def lire_sqlserver(host, port, user, password, database, requete):
    conn = pymssql.connect(server=host, port=port, user=user,
                            password=password, database=database)
    try:
        with conn.cursor(as_dict=True) as cur:
            cur.execute(requete)  # toujours un SELECT, jamais un INSERT/UPDATE
            return list(cur)
    finally:
        conn.close()
```

Fournisseurs et écritures comptables passent par `remplacer_table` :
l'ERP représente l'état courant complet, pas un flux d'événements à
accumuler — chaque run récupère l'intégralité de la table telle qu'elle
existe maintenant dans l'ERP.

**Les vrais défauts d'un ERP, absorbés plutôt qu'ignorés** — simuler un
ERP réaliste, c'est simuler ses défauts, pas une base propre :

| Défaut observé | Où | Comment il est absorbé en aval |
|---|---|---|
| Dates ambiguës | AS/400 (`CMDDAT`) | Deux formats tentés (YYYYMMDD puis DDMMYYYY), dérive rendue visible via un flag `date_format_derive`, jamais corrigée en silence. |
| Aucune colonne de modif fiable | AS/400 + SQL Server | Snapshot dbt en stratégie `check` (comparaison de colonnes réelles) plutôt que `timestamp`. |
| Numérotation propre à l'ERP | Écritures SQL Server vs factures Factur-X | Rapprochement par SIREN + montant, jamais par numéro — les deux mondes ne partagent pas la même numérotation. |
| Doublons de saisie | Écritures comptables | *Dédoublonnés* en staging (contrairement aux commandes Ventes) : un doublon comptable est une vraie erreur de saisie (double-clic), pas un enregistrement distinct à garder. |
| SIREN mal formaté | Fournisseurs | Normalisé (espaces supprimés) et flagué invalide plutôt que rejeté — une facture reste rattachable même si son SIREN est mal renseigné. |

**Sécurité spécifique à une donnée ERP sensible.** L'IBAN des
fournisseurs devait être invisible pour `role_direction` mais visible
pour `role_finance`. Bug Postgres réel rencontré : un `GRANT SELECT`
global posé sur la table rend inopérant un `REVOKE SELECT (colonne)`
posé ensuite — vérifié via `has_column_privilege`, le revoke n'avait
mesurablement aucun effet. Corrigé en n'accordant **jamais** le SELECT
global à ce rôle : uniquement les colonnes explicitement listées, IBAN
exclue.

> **Pour refaire :** historiser (snapshot) **avant** tout nettoyage,
> jamais après — un ERP en "remplacement complet" à chaque extraction ne
> garde aucun historique lui-même ; c'est au pipeline de le faire, sur la
> donnée la plus brute possible.

**Avant / après, mesuré — domaine Finance/Compta (l'ERP SQL Server)**
(détail complet et méthode : [`avant.md`](../domaines/finance-compta/avant.md) /
[`apres.md`](../domaines/finance-compta/apres.md)) :

| Indicateur | Avant | Après |
|---|---|---|
| Fournisseurs | 80 (1 SIREN invalide/absent) | 80 (SIREN normalisé et flagué) |
| Écritures comptables | 866 (11 doublons de saisie exacts inclus) | **855** (doublons supprimés) |
| Montant TTC total | non calculable (2 formats texte FR/US) | **7 240 138,82 €** |
| Factures rattachées à une écriture — canal Factur-X (structuré) | — | **91 % (387/426)** |
| Factures rattachées à une écriture — canal non structuré (PDF/OCR) | — | **44 % (190/428)** |
| Accès à l'IBAN fournisseur | non contrôlé | `role_finance` uniquement (colonne restreinte) |

**Constat honnête** : l'écart 91 % vs 44 % n'est pas un artefact du
pipeline — c'est une mesure directe du **coût réel du papier/PDF non
structuré** : le canal non structuré perd le SIREN dans 60 % des cas et
produit un montant illisible dans 15 % des cas. Un argument chiffré
concret pour prioriser la migration Factur-X des fournisseurs restants,
pas une intuition.

## 3. dbt — cinq couches, les pièges qui reviennent

Le détail pas-à-pas complet (snapshot → staging → marts → tests → docs)
et les 5 fonctionnalités avancées ajoutées ensuite (incremental,
contracts, freshness, exposures, unit tests) sont dans le guide de
réalisation et les modèles eux-mêmes (`dbt/models/`). Cette section
retient les pièges dbt qui ne sont *pas* spécifiques à un domaine.

| Piège | Symptôme | Correctif |
|---|---|---|
| Colonnes brutes citées en majuscules | `column does not exist` dans le snapshot | Citer les colonnes (`"CLICOD"`) partout où elles sont référencées, y compris dans `unique_key`/`check_cols`. |
| `ALTER DEFAULT PRIVILEGES` ne suffit pas | `dbt_transform` ne peut pas lire les tables `raw` | Ne s'applique qu'aux objets créés PAR le rôle qui exécute la commande — utiliser `FOR ROLE ingestion` puisque les tables raw sont créées par ce rôle-là. |
| Snapshot qui écrit dans un schéma en lecture seule | `permission denied` sur `raw` | `target_schema` déplacé vers `raw_historise`, possédé par `dbt_transform` — garde la séparation ingestion/transformation. |
| RLS qui disparaît au run suivant | 2ᵉ vérification RLS échoue après une 1ʳᵉ réussie | Un modèle `table` fait DROP+CREATE à chaque `dbt run` — poser GRANT/policies en `post_hook` du modèle, jamais dans un script séparé. |
| Seed dans le mauvais schéma | `permission denied for schema raw` au premier `dbt seed` | Un seed n'est pas une source ingérée — `seeds: +schema: marts` dans `dbt_project.yml`. |

> **Pour refaire :** vérifier l'idempotence d'un snapshot dès son premier
> succès — relancer `dbt snapshot` une 2ᵉ fois sans changement de donnée
> doit produire `INSERT 0 0`, sinon le SCD2 ne fonctionne pas réellement,
> même si la commande n'a rien retourné en erreur.

### Captures réelles — `dbt docs generate`, entrepôt local rechargé pour l'occasion

Pas la production (l'entrepôt de prod n'est volontairement pas exposé sur
Internet, cf. Phase 7 du guide de réalisation) — un entrepôt Postgres
local reconstruit spécifiquement pour vérifier ces fonctionnalités avant
de les documenter.

![dbt docs — nouvelle page d'accueil (overview.md)](screenshots/dbtdocs-overview.png)

*Page d'accueil du catalogue dbt, avant vide, maintenant un vrai doc
block qui explique comment lire le projet — sources avec freshness,
contrats, modèles incrémentaux, tests unitaires, exposures.*

![dbt docs — fait_ventes, contrat de schéma + incremental](screenshots/dbtdocs-contract-fait-ventes.png)

*`fait_ventes` : badge "incremental" et "CONTRACT: Enforced" lus
directement dans le manifest après un run réel, 13 colonnes typées. C'est
en vérifiant cette page qu'un vrai `dbt run` a détecté `_ingested_at`
déclaré `TIMESTAMP` au lieu de `TIMESTAMPTZ` — corrigé avant cette
capture, pas après.*

![dbt docs — fait_ecritures, même garantie côté Finance](screenshots/dbtdocs-contract-fait-ecritures.png)

*Même principe sur le domaine Finance/Compta — contrat de schéma et
incremental (curseur `ecriture_id`, pas `_ingested_at` : voir la partie
ERP ci-dessus pour pourquoi).*

![dbt docs — exposure Filiation](screenshots/dbtdocs-exposure-filiation.png)

*Un seul consommateur déclaré en aval : Filiation, réellement branché
(Phase 7). Power BI et Metabase sont prêts côté entrepôt mais pas
réellement connectés à ce projet à ce jour — volontairement absents de
cette page plutôt qu'inventés.*

## Ordre de construction, si c'était à refaire

L'ordre réellement suivi sur les 7 phases — chaque étape ne dépend que de
la précédente :

1. **Infra partagée minimale** — entrepôt Postgres + rôles à privilège minimal (`ingestion`, `dbt_transform`) avant tout code.
2. **Un domaine complet, du writer au mart** — pas les 3 en parallèle : un seul jusqu'au bout (ingestion → snapshot → staging → marts → RLS vérifiée) pour laisser le patron se stabiliser avant de le répéter.
3. **Répéter sur les domaines suivants** — chaque nouveau domaine réutilise les adaptateurs génériques déjà écrits ; n'en ajouter que pour un type de source vraiment nouveau.
4. **Consolidation transverse** — dimension partagée (`dim_date`) et analyse inter-domaines seulement une fois les 3 domaines individuellement vérifiés.
5. **Housekeeping et documentation vivante** — `dbt docs`, index/bloat, lignage, une fois qu'il y a quelque chose de stable à documenter.
6. **Orchestration de production** — DAG Airflow réel + workflows n8n testés avec de vrais appels, en dernier puisqu'il orchestre tout ce qui précède.

---

Voir aussi : [`guide-realisation.md`](guide-realisation.md) (le journal
complet, phase par phase) et [`outils.md`](outils.md) (chaque outil,
pourquoi ce choix, comment il est déclenché).
