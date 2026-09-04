# Guide de réalisation

Écrit au fil de la construction réelle — chaque section correspond à ce
qui a été fait, vérifié, et fonctionne. Pas un plan à l'avance (ça, c'est
l'[issue #2](https://github.com/valentinratigniet-byte/valentinratigniet-byte/issues/2)).

## Phase 1 — Infra partagée : Airflow

**Objectif** : orchestrer le futur pipeline dbt (raw → snapshots → staging
→ marts → tests → slim CI) sans ajouter de charge inutile sur un VPS à
2 vCPU.

**Ce qui a été fait** :
1. Stack Airflow minimale — `LocalExecutor`, pas de Celery/Redis/workers
   (inutile pour ce volume, et le VPS n'a que 2 vCPU). Metadata DB dédiée
   (Postgres léger, séparée de l'entrepôt).
2. Déployée sur le VPS existant (`/opt/projet19/airflow/`), pas via le
   catalogue "1-clic" de Coolify (pas de template Airflow disponible) —
   `docker compose` direct, secrets réels écrits directement sur le
   serveur via SFTP (jamais commités, `.env.example` documente juste la
   forme attendue).
3. Webserver exposé uniquement sur `127.0.0.1:8090` pour l'instant — pas
   encore de routage public HTTPS via Traefik/Coolify. Volontairement
   séparé : vérifier que le service tourne avant de l'exposer.

**Vérifié, pas juste "up"** :
- `docker ps` → `airflow-webserver` et `airflow-postgres` healthy,
  `airflow-scheduler` opérationnel.
- `curl http://127.0.0.1:8090/health` → `HTTP 200`.
- `airflow dags list` → le DAG `healthcheck` détecté.
- DAG `healthcheck` déclenché manuellement → **state: success** — confirme
  que le conteneur peut bien lire `/opt/dbt` (volume monté), pas juste que
  le webserver répond.

**Routage HTTPS public — fait juste après, même session** :

Airflow n'a pas été déployé via le catalogue Coolify (pas de template
disponible), donc `coolify-proxy` (Traefik) ne rejoint pas automatiquement
son réseau comme il le fait pour les ressources gérées par Coolify
(n8n, Metabase). Reproduit le même schéma manuellement :
1. Labels Traefik ajoutés sur `airflow-webserver` dans le
   `docker-compose.yml` (routers http→https redirect + https avec
   `certresolver: letsencrypt`), en copiant exactement le pattern déjà
   utilisé par le n8n du Projet 18 (`docker inspect` sur le conteneur n8n
   pour lire ses labels réels plutôt que deviner).
2. `docker network connect airflow_default coolify-proxy` — attache
   manuellement le proxy au réseau d'Airflow (Coolify le fait
   automatiquement pour ses propres ressources, pas pour celle-ci).
3. `docker compose up -d airflow-webserver` pour recréer le conteneur avec
   les nouveaux labels.

**Vérifié** : `http://airflow-projet19.76.13.43.130.sslip.io/health` →
`302` (redirection vers HTTPS) ; `https://.../health` → `200`, avec
vérification **stricte** du certificat (pas de `-k`) qui passe — donc un
vrai certificat Let's Encrypt valide, pas juste servi en HTTPS auto-signé.
Fonctionné du premier coup, contrairement au Projet 18 où l'équivalent
avait demandé un contournement via la base Coolify — différence : ici
c'est une ressource neuve avec labels corrects dès le départ, pas une
ressource existante mal configurée à corriger après coup.

**Pas encore fait** : le vrai DAG de production (remplace
`healthcheck.py`, arrive en Phase 2 avec le premier domaine).
