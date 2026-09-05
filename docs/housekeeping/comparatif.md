# Housekeeping — comparatif pganalyze vs pgHero vs script maison

Même format que les comparatifs d'outils du
[Projet 18](https://github.com/valentinratigniet-byte/projet-18-monitoring-energie-rte).
**pganalyze** comparé sur documentation publique (outil payant, décision
0€ du cadrage — [issue #2](https://github.com/valentinratigniet-byte/valentinratigniet-byte/issues/2)) ;
**pgHero** et le **script maison** réellement déployés et vérifiés.

| Critère | pganalyze | pgHero | Script maison |
|---|---|---|---|
| Coût | Payant (abonnement, tarif à la base) | Gratuit, open source | Gratuit |
| Déployé dans ce projet | ❌ non (comparé sur doc uniquement) | ✅ oui, vérifié | ✅ oui, vérifié |
| Périmètre moteur | PostgreSQL uniquement | PostgreSQL uniquement | **PostgreSQL + SQL Server + MySQL** |
| Installation | SaaS, agent à connecter à la base | Container Docker, `DATABASE_URL` | Script Python, à planifier (cron/Airflow) |
| Détection index inutilisés | Oui | Oui | Oui — **a exclu les clés primaires** (un `idx_scan=0` sur une PK ne veut pas dire "à supprimer", contrairement à ce qu'une lecture naïve suggérerait) |
| Détection bloat/fragmentation | Oui, avec historique et alertes proactives | Oui, instantané | Oui, instantané |
| Recommandations automatiques (EXPLAIN, requêtes lentes) | Oui, en continu, alertes par email/Slack | Query Stats (nécessite `pg_stat_statements`, **pas activé sur cet entrepôt** — détecté par pgHero lui-même, pas supposé) | Non — hors scope volontaire, un script ponctuel ne remplace pas un monitoring continu |
| Adapté à ce projet | Surdimensionné et payant pour un entrepôt de cette taille | **Bon choix pour Postgres seul** | **Seul outil qui couvre les 3 moteurs réellement utilisés** (SQL Server et MySQL ne sont couverts ni par pganalyze ni par pgHero) |

## Constat

**Aucun outil du marché ne couvre a lui seul les 3 technologies
réellement utilisées dans ce projet** (Postgres, SQL Server, MySQL) — un
choix architectural assumé dès le cadrage (vraies technos d'entreprise,
pas une seule base partout). pgHero reste le bon choix pour l'entrepôt
Postgres (gratuit, suffisant), le script maison comble le blanc laissé
par tous les outils du marché sur SQL Server et MySQL.

## Trouvailles réelles (pas simulées)

- **`raw._fichiers_ingeres`** (table manifeste d'idempotence, cf.
  `ingestion/adaptateurs/postgres_writer.py`) : 36,4 % de lignes mortes —
  cohérent avec les relances répétées de l'ingestion pendant les tests de
  ce projet, pas une anomalie de production.
- **`EcrituresComptables` (SQL Server)** : 11,1 % de fragmentation sur
  l'index de clé primaire — mesurable dès ~900 lignes.
- **`pg_stat_statements` non activé** sur l'entrepôt — détecté par pgHero
  lui-même (pas une supposition) ; à activer si un vrai suivi de requêtes
  lentes devient nécessaire en Phase 6+.
- **2 bugs de faux positifs corrigés dans le script maison avant de
  publier un résultat** : (1) la détection SQL Server remontait 182
  "index inutilisés" qui étaient en réalité des objets système internes
  (`sys.*`, `plan_persist_*`) — corrigé en filtrant `is_ms_shipped = 0` ;
  (2) la détection Postgres remontait les clés primaires comme
  "candidates à la suppression" alors qu'elles servent à l'unicité, pas
  seulement aux lectures — corrigé en les excluant explicitement. Même
  discipline "mesuré pas inventé" que le reste du projet : un faux
  positif détecté avant publication vaut mieux qu'un résultat impressionnant
  mais faux.
