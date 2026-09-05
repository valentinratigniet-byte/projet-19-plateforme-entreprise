"""Orchestration d'ingestion du domaine Marketing/Activité.

Contacts/campagnes/envois (MySQL) -> remplace a chaque run (le CRM
represente l'etat courant complet, meme raisonnement que Finance/Compta).
Evenements web (JSON mensuel) -> ajoute, idempotent par fichier.
Stats de campagnes (API SaaS, polling OAuth2) -> remplace a chaque run
(vue courante des metriques cote SaaS, pas un historique).
"""

from __future__ import annotations

import os
from pathlib import Path

import psycopg2

from adaptateurs.api_rest import ClientOAuth2, lire_api_paginee
from adaptateurs.json_file import lire_json
from adaptateurs.mysql import lire_mysql
from adaptateurs.postgres_writer import ajouter_lignes, remplacer_table

SOURCE_DIR = Path(__file__).parent / "source" / "exports"
SAAS_BASE_URL = os.environ.get("SAAS_BASE_URL", "http://projet19-saas-mock:5000")


def connecter_postgres():
    return psycopg2.connect(
        host=os.environ.get("PGHOST", "projet19-postgres"),
        port=os.environ.get("PGPORT", "5432"),
        dbname=os.environ.get("PGDATABASE", "projet19"),
        user=os.environ.get("PGUSER", "ingestion"),
        password=os.environ["PGPASSWORD"],
    )


def ingerer_mysql(conn) -> dict[str, int]:
    args = (
        os.environ.get("MYSQL_HOST", "projet19-mysql"),
        int(os.environ.get("MYSQL_PORT", "3306")),
        "root",
        os.environ["MYSQL_ROOT_PASSWORD"],
        "marketing_activite",
    )
    resultats = {}
    for table in ("contacts", "campagnes", "envois"):
        lignes = lire_mysql(*args, f"SELECT * FROM {table}")
        resultats[f"marketing_{table}"] = remplacer_table(
            conn, "raw", f"marketing_{table}", lignes, f"mysql:{table}"
        )
    return resultats


def ingerer_evenements_web(conn) -> int:
    total = 0
    for f in sorted(SOURCE_DIR.glob("evenements_web_*.json")):
        lignes = lire_json(f)
        total += ajouter_lignes(conn, "raw", "marketing_evenements_web", lignes, f.name)
    return total


def ingerer_stats_saas(conn) -> int:
    oauth = ClientOAuth2(
        f"{SAAS_BASE_URL}/oauth/token",
        os.environ.get("SAAS_CLIENT_ID", "projet19"),
        os.environ["SAAS_CLIENT_SECRET"],
    )
    stats = lire_api_paginee(oauth, f"{SAAS_BASE_URL}/api/campagnes/stats", par_page=3)
    return remplacer_table(conn, "raw", "marketing_stats_saas", stats, "api:campagnes/stats")


def main() -> None:
    conn = connecter_postgres()
    try:
        resultats = ingerer_mysql(conn)
        resultats["marketing_evenements_web"] = ingerer_evenements_web(conn)
        resultats["marketing_stats_saas"] = ingerer_stats_saas(conn)
    finally:
        conn.close()

    for table, n in resultats.items():
        print(f"raw.{table}: {n} nouvelles/actuelles lignes")

    assert resultats.get("marketing_contacts", 0) > 0, "aucun contact charge"
    print("self-check OK")


if __name__ == "__main__":
    main()
