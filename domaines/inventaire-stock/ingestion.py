"""Orchestration d'ingestion du domaine Inventaire/Stock.

Articles + mouvements (Firebird) -> remplace a chaque run (le systeme
embarque represente l'etat courant complet, pas un export incremental --
meme principe que les ecritures comptables). Pas de CDC ici : Firebird
n'expose pas de mecanisme de capture de changement comparable a SQL
Server, et le volume (quelques milliers de mouvements) ne le justifie
pas a ce stade.
"""

from __future__ import annotations

import os

import psycopg2

from adaptateurs.firebird import lire_firebird
from adaptateurs.postgres_writer import remplacer_table

FIREBIRD_DB = "/var/lib/firebird/data/inventaire.fdb"


def connecter_postgres():
    return psycopg2.connect(
        host=os.environ.get("PGHOST", "projet19-postgres"),
        port=os.environ.get("PGPORT", "5432"),
        dbname=os.environ.get("PGDATABASE", "projet19"),
        user=os.environ.get("PGUSER", "ingestion"),
        password=os.environ["PGPASSWORD"],
    )


def ingerer_firebird(conn) -> dict[str, int]:
    host = os.environ.get("FIREBIRD_HOST", "projet19-firebird")
    port = int(os.environ.get("FIREBIRD_PORT", "3050"))
    password = os.environ["FIREBIRD_ROOT_PASSWORD"]

    articles = lire_firebird(host, port, password, FIREBIRD_DB, "SELECT * FROM ARTICLES_STOCK")
    mouvements = lire_firebird(host, port, password, FIREBIRD_DB, "SELECT * FROM MOUVEMENTS_STOCK")

    return {
        "stock_articles": remplacer_table(conn, "raw", "stock_articles", articles, "firebird:ARTICLES_STOCK"),
        "stock_mouvements": remplacer_table(conn, "raw", "stock_mouvements", mouvements, "firebird:MOUVEMENTS_STOCK"),
    }


def main() -> None:
    conn = connecter_postgres()
    try:
        resultats = ingerer_firebird(conn)
    finally:
        conn.close()

    for table, n in resultats.items():
        print(f"raw.{table}: {n} lignes")

    assert resultats["stock_articles"] > 0, "aucun article charge"
    assert resultats["stock_mouvements"] > 0, "aucun mouvement charge"
    print("self-check OK")


if __name__ == "__main__":
    main()
