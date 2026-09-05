"""DAG de production : raw -> snapshots (SCD2) -> staging -> marts -> tests
-> docs. Remplace le placeholder healthcheck.py (Phase 1). Tourne apres les
3 ingestions n8n (2h/3h/4h) -- 5h UTC laisse une marge large.

2 webhooks n8n branches (cf. n8n/*.json, ops/README.md) :
- echec (n'importe quelle tache) -> "Projet 19 - Alerte echec DAG dbt"
- succes de dbt_test -> "Projet 19 - Verification RLS post-deploiement"
  (les policies RLS sont recreees a chaque dbt run via post_hook,
  revalider juste apres un run reel a plus de sens qu'a intervalle fixe)."""

import json
import urllib.request
from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator

DBT_DIR = "/opt/dbt"
DBT_FLAGS = "--profiles-dir . --project-dir . --log-path /tmp/dbt_logs --target-path /tmp/dbt_target"
N8N_BASE = "https://n8n-tbgietry5lj93vrnsibihqdr.76.13.43.130.sslip.io/webhook"


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
    seed = BashOperator(task_id="dbt_seed", bash_command=f"dbt seed {DBT_FLAGS}", cwd=DBT_DIR)
    snapshot = BashOperator(task_id="dbt_snapshot", bash_command=f"dbt snapshot {DBT_FLAGS}", cwd=DBT_DIR)
    run = BashOperator(task_id="dbt_run", bash_command=f"dbt run {DBT_FLAGS}", cwd=DBT_DIR)
    test = BashOperator(task_id="dbt_test", bash_command=f"dbt test {DBT_FLAGS}", cwd=DBT_DIR)
    notifier_succes = BashOperator(
        task_id="notifier_succes_rls",
        bash_command=f"curl --fail --max-time 10 -X POST {N8N_BASE}/projet19-dbt-succes || true",
    )
    docs = BashOperator(task_id="dbt_docs_generate", bash_command=f"dbt docs generate {DBT_FLAGS}", cwd=DBT_DIR)

    seed >> snapshot >> run >> test >> notifier_succes >> docs
