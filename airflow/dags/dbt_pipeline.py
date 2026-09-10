"""DAG de production : raw -> snapshots (SCD2) -> staging -> marts -> tests
-> docs. Remplace le placeholder healthcheck.py (Phase 1).

Declenchement double, pas un choix entre les deux :
- EVENEMENTIEL -- chacun des 3 workflows d'ingestion n8n appelle l'API
  Airflow (POST /dags/dbt_pipeline/dagRuns) des qu'il termine. dbt peut
  donc demarrer quelques minutes apres la derniere ingestion du jour,
  au lieu d'attendre systematiquement 5h UTC.
- PLANIFIE -- le cron 5h UTC reste actif en filet de securite (n8n hors
  service, appel API rate, etc.) : les 3 domaines ont largement fini a
  cette heure-la de toute facon.
Les deux chemins passent par la meme porte (`attendre_les_3_domaines`)
pour ne jamais lancer dbt sur une donnee partielle -- un declenchement
premature (le premier domaine du jour qui finit, pas le dernier) se
contente de s'arreter proprement, ce n'est pas un echec.

2 webhooks n8n branches (cf. n8n/*.json, ops/README.md) :
- echec (n'importe quelle tache) -> "Projet 19 - Alerte echec DAG dbt"
- succes de dbt_test -> "Projet 19 - Verification RLS post-deploiement"
  (les policies RLS sont recreees a chaque dbt run via post_hook,
  revalider juste apres un run reel a plus de sens qu'a intervalle fixe)."""

import json
import os
import urllib.request
from datetime import datetime

import pendulum
import psycopg2
from airflow import DAG
from airflow.models import DagRun
from airflow.operators.bash import BashOperator
from airflow.operators.python import ShortCircuitOperator

DBT_DIR = "/opt/dbt"
DBT_FLAGS = "--profiles-dir . --project-dir . --log-path /tmp/dbt_logs --target-path /tmp/dbt_target"
# Lue depuis l'environnement du conteneur (docker-compose.yml) -- jamais
# committee en dur, meme raison que les mots de passe PG*/AIRFLOW_*.
# .get() avec defaut vide plutot que os.environ[...] : une variable
# manquante ne doit jamais empecher Airflow de PARSER le DAG (les 2 appels
# webhook plus bas sont deja best-effort -- try/except et "|| true" --,
# une URL vide echoue proprement de la meme facon, elle ne casse rien).
N8N_BASE = os.environ.get("N8N_WEBHOOK_BASE_URL", "")

# Une table par domaine, choisie pour etre toujours rafraichie a chaque
# ingestion reussie -- pas raw.finance_fournisseurs : le CDC peut tres
# legitimement n'avoir "rien de nouveau" un jour donne (cf.
# docs/construction-etl-erp-dbt.md#cdc), ce qui ne veut pas dire que
# l'ingestion Finance n'a pas tourne.
TABLES_TEMOINS = ["ventes_commandes", "finance_ecritures", "marketing_contacts"]


def _tous_domaines_ingeres_aujourdhui() -> bool:
    """Porte d'entree du DAG (ShortCircuitOperator) : ne laisse dbt
    demarrer que si (1) un run n'a pas deja REELLEMENT execute dbt
    aujourd'hui -- evite de le rejouer en double si plusieurs domaines
    declenchent le DAG le meme jour -- et (2) les 3 domaines ont une
    donnee fraiche du jour. Un retour False n'est pas un echec : le
    declenchement suivant (un autre domaine, ou le cron 5h UTC) retentera
    normalement.

    Piege reel rencontre en testant (Airflow standalone reel, pas
    suppose) : DagRun.state == 'success' meme quand CE short-circuit a
    tout saute (les taches en aval passent 'skipped', pas 'failed', et un
    DagRun dont aucune tache n'a echoue est 'success' -- y compris quand
    aucune n'a vraiment tourne). Verifier DagRun.state aurait bloque dbt
    en permanence des le tout premier declenchement premature de la
    journee. Verifie ici l'etat de la DERNIERE tache reelle
    (dbt_docs_generate) sur les runs du jour, pas l'etat du DagRun."""
    aujourdhui = pendulum.now("UTC").date()
    runs_du_jour = [
        r for r in DagRun.find(dag_id="dbt_pipeline")
        if r.logical_date and r.logical_date.date() == aujourdhui
    ]
    for r in runs_du_jour:
        derniere_tache = r.get_task_instance("dbt_docs_generate")
        if derniere_tache is not None and derniere_tache.state == "success":
            return False

    conn = psycopg2.connect(
        host=os.environ["PGHOST"],
        port=os.environ.get("PGPORT", "5432"),
        dbname=os.environ["PGDATABASE"],
        user=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
    )
    try:
        with conn.cursor() as cur:
            for table in TABLES_TEMOINS:
                cur.execute(f'SELECT max(_ingested_at)::date = CURRENT_DATE FROM "raw"."{table}"')
                (frais,) = cur.fetchone()
                if not frais:
                    return False
    finally:
        conn.close()
    return True


def notifier_echec(context) -> None:
    payload = {
        "dag_id": context["dag"].dag_id,
        "task_id": context["task_instance"].task_id,
        "execution_date": str(context["execution_date"]),
    }
    req = urllib.request.Request(
        f"{N8N_BASE}/projet19-dbt-echec",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass  # best-effort : ne fait jamais echouer le DAG a cause d'une alerte ratee


with DAG(
    dag_id="dbt_pipeline",
    schedule="0 5 * * *",
    start_date=datetime(2026, 9, 5),
    catchup=False,
    tags=["dbt", "production"],
    on_failure_callback=notifier_echec,
) as dag:
    attendre_les_3_domaines = ShortCircuitOperator(
        task_id="attendre_les_3_domaines",
        python_callable=_tous_domaines_ingeres_aujourdhui,
    )
    seed = BashOperator(task_id="dbt_seed", bash_command=f"dbt seed {DBT_FLAGS}", cwd=DBT_DIR)
    snapshot = BashOperator(task_id="dbt_snapshot", bash_command=f"dbt snapshot {DBT_FLAGS}", cwd=DBT_DIR)
    run = BashOperator(task_id="dbt_run", bash_command=f"dbt run {DBT_FLAGS}", cwd=DBT_DIR)
    test = BashOperator(task_id="dbt_test", bash_command=f"dbt test {DBT_FLAGS}", cwd=DBT_DIR)
    notifier_succes = BashOperator(
        task_id="notifier_succes_rls",
        bash_command=f"curl --fail --max-time 10 -X POST {N8N_BASE}/projet19-dbt-succes || true",
    )
    docs = BashOperator(task_id="dbt_docs_generate", bash_command=f"dbt docs generate {DBT_FLAGS}", cwd=DBT_DIR)

    attendre_les_3_domaines >> seed >> snapshot >> run >> test >> notifier_succes >> docs
