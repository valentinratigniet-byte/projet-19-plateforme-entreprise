"""DAG de production : raw -> snapshots (SCD2) -> staging -> marts -> tests
-> docs. Remplace le placeholder healthcheck.py (Phase 1). Tourne apres les
3 ingestions n8n (2h/3h/4h) -- 5h UTC laisse une marge large."""

from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator

DBT_DIR = "/opt/dbt"
# --log-path/--target-path pointes hors du volume monte (../dbt, proprietaire
# = utilisateur du poste hote) : le conteneur tourne en uid 50000 (AIRFLOW_UID),
# qui n'a pas le droit d'ecrire dans dbt/logs sur ce montage -- PermissionError
# trouvee au premier vrai run, corrigee avant de considerer le DAG fonctionnel.
DBT_FLAGS = "--profiles-dir . --project-dir . --log-path /tmp/dbt_logs --target-path /tmp/dbt_target"

with DAG(
    dag_id="dbt_pipeline",
    schedule="0 5 * * *",
    start_date=datetime(2026, 9, 5),
    catchup=False,
    tags=["dbt", "production"],
) as dag:
    seed = BashOperator(task_id="dbt_seed", bash_command=f"dbt seed {DBT_FLAGS}", cwd=DBT_DIR)
    snapshot = BashOperator(task_id="dbt_snapshot", bash_command=f"dbt snapshot {DBT_FLAGS}", cwd=DBT_DIR)
    run = BashOperator(task_id="dbt_run", bash_command=f"dbt run {DBT_FLAGS}", cwd=DBT_DIR)
    test = BashOperator(task_id="dbt_test", bash_command=f"dbt test {DBT_FLAGS}", cwd=DBT_DIR)
    docs = BashOperator(task_id="dbt_docs_generate", bash_command=f"dbt docs generate {DBT_FLAGS}", cwd=DBT_DIR)

    seed >> snapshot >> run >> test >> docs
