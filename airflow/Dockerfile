FROM apache/airflow:2.10.3-python3.12

# dbt-core/dbt-postgres installes dans l'image plutot que via
# _PIP_ADDITIONAL_REQUIREMENTS (pattern deconseille par Airflow en prod --
# reinstalle a chaque demarrage de conteneur) -- meme discipline que
# l'image dediee projet19-ingestion.
RUN pip install --no-cache-dir dbt-core==1.12.0 dbt-postgres==1.11.0
