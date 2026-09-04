"""Vérifie qu'Airflow tourne et que le projet dbt (monté en volume) est
accessible. Remplacé par le vrai DAG dbt (raw -> snapshots -> staging ->
marts -> tests -> slim CI) une fois le premier domaine construit — ce
placeholder ne doit pas rester après la Phase 2."""

from datetime import datetime

from airflow.decorators import dag, task


@dag(
    dag_id="healthcheck",
    schedule=None,
    start_date=datetime(2026, 9, 4),
    catchup=False,
    tags=["infra", "phase-1"],
)
def healthcheck():
    @task
    def check_dbt_project_mounted() -> None:
        import os

        assert os.path.isdir("/opt/dbt"), "/opt/dbt (montage du projet dbt) introuvable"

    check_dbt_project_mounted()


healthcheck()
