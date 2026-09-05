"""Orchestration d'ingestion du domaine Finance/Compta.

Fournisseurs + ecritures comptables (SQL Server) -> remplace a chaque run
(la base ERP represente l'etat courant complet, pas un export mensuel --
contrairement a l'AS/400 du domaine Ventes).
Releve bancaire (CSV mensuel) -> ajoute, idempotent par fichier.
Factures recues (Factur-X XML + non structure) -> ajoute dans UNE seule
table raw (meme source metier, deux canaux, discriminant `canal`),
idempotent par fichier.
"""

from __future__ import annotations

import os
from pathlib import Path

import psycopg2

from adaptateurs.csv_file import lire_csv
from adaptateurs.facturx import lire_facturx_xml, lire_facture_non_structuree
from adaptateurs.postgres_writer import ajouter_lignes, remplacer_table
from adaptateurs.sqlserver import lire_sqlserver

SOURCE_DIR = Path(__file__).parent / "source" / "exports"


def connecter_postgres():
    return psycopg2.connect(
        host=os.environ.get("PGHOST", "projet19-postgres"),
        port=os.environ.get("PGPORT", "5432"),
        dbname=os.environ.get("PGDATABASE", "projet19"),
        user=os.environ.get("PGUSER", "ingestion"),
        password=os.environ["PGPASSWORD"],
    )


def ingerer_sqlserver(conn) -> dict[str, int]:
    fournisseurs = lire_sqlserver(
        os.environ.get("MSSQL_HOST", "projet19-sqlserver"),
        int(os.environ.get("MSSQL_PORT", "1433")),
        "sa",
        os.environ["MSSQL_SA_PASSWORD"],
        "finance_compta",
        "SELECT * FROM dbo.Fournisseurs",
    )
    ecritures = lire_sqlserver(
        os.environ.get("MSSQL_HOST", "projet19-sqlserver"),
        int(os.environ.get("MSSQL_PORT", "1433")),
        "sa",
        os.environ["MSSQL_SA_PASSWORD"],
        "finance_compta",
        "SELECT * FROM dbo.EcrituresComptables",
    )
    resultats = {}
    resultats["finance_fournisseurs"] = remplacer_table(
        conn, "raw", "finance_fournisseurs", fournisseurs, "sqlserver:Fournisseurs"
    )
    resultats["finance_ecritures"] = remplacer_table(
        conn, "raw", "finance_ecritures", ecritures, "sqlserver:EcrituresComptables"
    )
    return resultats


def ingerer_releve_bancaire(conn) -> int:
    total = 0
    for f in sorted(SOURCE_DIR.glob("releve_bancaire_*.csv")):
        lignes = lire_csv(f, delimiter=";", encoding="cp1252")
        total += ajouter_lignes(conn, "raw", "finance_releve_bancaire", lignes, f.name)
    return total


def ingerer_factures_recues(conn) -> int:
    total = 0
    for f in sorted(SOURCE_DIR.glob("factures_facturx_*.xml")):
        lignes = lire_facturx_xml(f)
        total += ajouter_lignes(conn, "raw", "finance_factures_recues", lignes, f.name)
    for f in sorted(SOURCE_DIR.glob("factures_non_structurees_*.txt")):
        lignes = lire_facture_non_structuree(f)
        total += ajouter_lignes(conn, "raw", "finance_factures_recues", lignes, f.name)
    return total


def main() -> None:
    conn = connecter_postgres()
    try:
        resultats = ingerer_sqlserver(conn)
        resultats["finance_releve_bancaire"] = ingerer_releve_bancaire(conn)
        resultats["finance_factures_recues"] = ingerer_factures_recues(conn)
    finally:
        conn.close()

    for table, n in resultats.items():
        print(f"raw.{table}: {n} nouvelles/actuelles lignes")

    assert resultats.get("finance_fournisseurs", 0) > 0, "aucun fournisseur charge"
    print("self-check OK")


if __name__ == "__main__":
    main()
