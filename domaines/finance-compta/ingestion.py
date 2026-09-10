"""Orchestration d'ingestion du domaine Finance/Compta.

Fournisseurs (SQL Server) -> CDC natif (cf. adaptateurs/sqlserver_cdc.py) :
seuls les changements reels depuis le dernier LSN traite sont lus et
appliques (upsert/delete), pas une relecture complete. Ecritures
comptables -> remplace a chaque run (l'ERP en represente l'etat courant
complet, un flux d'evenements comptables n'a pas le meme besoin
d'historiser une valeur "avant" -- une ecriture ne se modifie pas, elle
s'annule par une nouvelle ecriture, contrairement a une fiche
fournisseur).
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
from adaptateurs.postgres_writer import ajouter_lignes, appliquer_cdc, remplacer_table
from adaptateurs.sqlserver import lire_sqlserver
from adaptateurs.sqlserver_cdc import lire_changements, lsn_actuel_max

SOURCE_DIR = Path(__file__).parent / "source" / "exports"
CDC_CAPTURE_INSTANCE = "dbo_Fournisseurs"


def connecter_postgres():
    return psycopg2.connect(
        host=os.environ.get("PGHOST", "projet19-postgres"),
        port=os.environ.get("PGPORT", "5432"),
        dbname=os.environ.get("PGDATABASE", "projet19"),
        user=os.environ.get("PGUSER", "ingestion"),
        password=os.environ["PGPASSWORD"],
    )


def _lire_watermark(conn, capture_instance: str) -> str | None:
    with conn.cursor() as cur:
        cur.execute(
            "CREATE TABLE IF NOT EXISTS raw._cdc_watermarks "
            "(capture_instance TEXT PRIMARY KEY, dernier_lsn TEXT, maj_le TIMESTAMPTZ DEFAULT now())"
        )
        cur.execute(
            "SELECT dernier_lsn FROM raw._cdc_watermarks WHERE capture_instance = %s",
            (capture_instance,),
        )
        row = cur.fetchone()
    conn.commit()
    return row[0] if row else None


def _ecrire_watermark(conn, capture_instance: str, lsn: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO raw._cdc_watermarks (capture_instance, dernier_lsn, maj_le) "
            "VALUES (%s, %s, now()) ON CONFLICT (capture_instance) "
            "DO UPDATE SET dernier_lsn = EXCLUDED.dernier_lsn, maj_le = now()",
            (capture_instance, lsn),
        )
    conn.commit()


def ingerer_fournisseurs_cdc(conn) -> int:
    """Premier appel (pas de filigrane enregistre) : instantane complet en
    amorce, jamais du CDC seul -- CDC ne voit rien de plus ancien que sa
    propre activation (sys.sp_cdc_enable_table), il n'aurait aucun moyen
    de restituer l'etat des fournisseurs deja presents avant cette date.
    Le filigrane est alors pose au LSN maximal courant (pas minimal) pour
    ne pas relire en double ce que l'instantane vient deja de charger.
    Appels suivants : uniquement les changements reels via CDC."""
    host = os.environ.get("MSSQL_HOST", "projet19-sqlserver")
    port = int(os.environ.get("MSSQL_PORT", "1433"))
    password = os.environ["MSSQL_SA_PASSWORD"]

    depuis_lsn = _lire_watermark(conn, CDC_CAPTURE_INSTANCE)

    if depuis_lsn is None:
        fournisseurs = lire_sqlserver(
            host, port, "sa", password, "finance_compta", "SELECT * FROM dbo.Fournisseurs"
        )
        for f in fournisseurs:
            f["_cdc_operation"] = "insert"
            f["_cdc_lsn"] = "0" * 20  # marqueur : instantane initial, pas un LSN reel
        n = appliquer_cdc(
            conn, "raw", "finance_fournisseurs", fournisseurs, "FournisseurID",
            "cdc:instantane_initial",
        )
        lsn_depart = lsn_actuel_max(host, port, "sa", password, "finance_compta")
        if lsn_depart:
            _ecrire_watermark(conn, CDC_CAPTURE_INSTANCE, lsn_depart)
        return n

    changements, nouveau_lsn = lire_changements(
        host, port, "sa", password, "finance_compta", CDC_CAPTURE_INSTANCE, depuis_lsn
    )
    n = appliquer_cdc(
        conn, "raw", "finance_fournisseurs", changements, "FournisseurID",
        f"cdc:{CDC_CAPTURE_INSTANCE}:{depuis_lsn}->{nouveau_lsn or depuis_lsn}",
    )
    if nouveau_lsn and nouveau_lsn != depuis_lsn:
        _ecrire_watermark(conn, CDC_CAPTURE_INSTANCE, nouveau_lsn)
    return n


def ingerer_sqlserver(conn) -> dict[str, int]:
    ecritures = lire_sqlserver(
        os.environ.get("MSSQL_HOST", "projet19-sqlserver"),
        int(os.environ.get("MSSQL_PORT", "1433")),
        "sa",
        os.environ["MSSQL_SA_PASSWORD"],
        "finance_compta",
        "SELECT * FROM dbo.EcrituresComptables",
    )
    resultats = {}
    resultats["finance_fournisseurs"] = ingerer_fournisseurs_cdc(conn)
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
        with conn.cursor() as cur:
            cur.execute('SELECT count(*) FROM "raw"."finance_fournisseurs"')
            (n_fournisseurs_en_base,) = cur.fetchone()
    finally:
        conn.close()

    for table, n in resultats.items():
        print(f"raw.{table}: {n} changement(s)/nouvelles lignes cette execution")

    # CDC : 0 changement est un resultat normal (rien n'a change depuis le
    # dernier appel) -- le vrai invariant est l'etat de la table, pas le
    # delta de cette execution precise.
    assert n_fournisseurs_en_base > 0, "aucun fournisseur en base (raw.finance_fournisseurs vide)"
    print("self-check OK")


if __name__ == "__main__":
    main()
