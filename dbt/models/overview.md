{% docs __overview__ %}

# Projet 19 — Plateforme data d'entreprise

Entrepôt en modèle **constellation** (dimensions partagées, plusieurs
faits) construit à partir de trois sources de production hétérogènes,
simulées mais réelles dans leur technologie : **AS/400** (Ventes/Commerce),
**SQL Server** (Finance/Compta), **MySQL** (Marketing/Activité). Détail
complet dans le [README](https://github.com/valentinratigniet-byte/projet-19-plateforme-entreprise).

## Comment lire ce catalogue

Chaque domaine suit exactement les mêmes 5 étapes, dans les mêmes
répertoires :

```
raw (copie fidèle) → snapshot (SCD2) → staging (nettoyage documenté) → marts (dimensions + faits)
```

- **Sources** : les 12 tables `raw` ont toutes une freshness déclarée,
  sur la même colonne `_ingested_at` (écrite par
  `ingestion/adaptateurs/postgres_writer.py`, commune aux 3 domaines).
  Elle horodate le dernier chargement, pas forcément un ajout individuel
  — sur un extrait "état courant complet" (SQL Server, MySQL), c'est un
  simple signal "l'ingestion a tourné", pas un curseur exploitable en
  incrémental (cf. le commentaire de `fait_ecritures.sql`).
- **Contrats de schéma** (`contract: enforced`) sur les marts directement
  consommés par la couche BI (`fait_ventes`, `fait_ecritures`,
  `fait_envois`) — un `dbt run` échoue explicitement si leur schéma dérive,
  plutôt que de laisser un dashboard se casser silencieusement en aval.
- **Modèles incrémentaux** sur les trois faits à plus fort volume
  (`fait_ventes`, `fait_ecritures`, `fait_evenements_web`) — la logique de
  filtre et son hypothèse assumée sont commentées en tête de chaque
  fichier SQL.
- **Tests unitaires** (`unit_tests`, dbt 1.8+) sur la logique de parsing la
  plus fragile — date AS/400 à deux formats, SIREN, mojibake MySQL —
  vérifiée sans toucher l'entrepôt réel.
- **Exposures** : voir l'onglet Exposures pour les consommateurs
  réellement branchés en aval (à ce jour : Filiation uniquement — Power BI
  et Metabase sont prêts côté entrepôt mais pas encore connectés pour ce
  projet).

## Gouvernance

RLS multi-rôles (`role_rh` / `role_finance` / `role_direction` /
`role_commercial` / `role_marketing`) posée en `post_hook` sur chaque
mart, ré-appliquée à chaque `dbt run` — un modèle `table` fait
DROP+CREATE à chaque exécution, ce qui efface policies et grants posés à
part si on ne les rejoue pas.

{% enddocs %}
