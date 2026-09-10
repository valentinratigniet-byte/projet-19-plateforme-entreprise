"""Orchestration d'ingestion du domaine Support Client.

Tickets SAV (MongoDB) -> remplace a chaque run (la collection represente
l'etat courant complet, meme principe que les ecritures comptables) --
mais contrairement aux adaptateurs SQL, chaque document est transporte
tel quel dans une colonne unique `document` (JSON serialise en texte),
pas aplati en colonnes fixes : un document store ne garantit aucun
schema (cf. adaptateurs/mongodb.py -- derive de schema reelle simulee,
customer_ref vs client_id selon l'anciennete du ticket). L'aplatissement
arrive en staging dbt (::jsonb, ->>), pas ici.
"""

from __future__ import annotations

import os

import psycopg2

from adaptateurs.mongodb import lire_mongodb
from adaptateurs.postgres_writer import remplacer_table


def connecter_postgres():
    return psycopg2.connect(
        host=os.environ.get("PGHOST", "projet19-postgres"),
        port=os.environ.get("PGPORT", "5432"),
        dbname=os.environ.get("PGDATABASE", "projet19"),
        user=os.environ.get("PGUSER", "ingestion"),
        password=os.environ["PGPASSWORD"],
    )


def ingerer_tickets(conn) -> int:
    tickets = lire_mongodb(
        os.environ.get("MONGO_HOST", "projet19-mongodb"),
        int(os.environ.get("MONGO_PORT", "27017")),
        "root",
        os.environ["MONGO_ROOT_PASSWORD"],
        "support_client",
        "tickets",
    )
    return remplacer_table(conn, "raw", "support_tickets", tickets, "mongodb:tickets")


def main() -> None:
    conn = connecter_postgres()
    try:
        n = ingerer_tickets(conn)
    finally:
        conn.close()

    print(f"raw.support_tickets: {n} lignes")
    assert n > 0, "aucun ticket charge"
    print("self-check OK")


if __name__ == "__main__":
    main()
