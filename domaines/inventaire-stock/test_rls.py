"""Verifie la RLS reellement, par SET ROLE (meme discipline que les autres
domaines) -- role_stock/role_direction voient tout, les autres roles 0
ligne (policy USING(true) restreinte aux GRANT poses)."""

from __future__ import annotations

import os

import psycopg2

CASES = [
    # (role, acces_attendu)
    ("role_rh", False),
    ("role_finance", False),
    ("role_commercial", False),
    ("role_direction", True),
    ("role_stock", True),
]

TABLES = ["marts.dim_stock_articles", "marts.fait_mouvements_stock"]


def connecter():
    return psycopg2.connect(
        host=os.environ.get("PGHOST", "projet19-postgres"),
        port=os.environ.get("PGPORT", "5432"),
        dbname=os.environ.get("PGDATABASE", "projet19"),
        user=os.environ.get("PGSUPERUSER", "postgres"),
        password=os.environ["PGSUPERUSER_PASSWORD"],
    )


def main() -> None:
    conn = connecter()
    conn.autocommit = True
    echecs = []
    totaux = {}

    with conn.cursor() as cur:
        for table in TABLES:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            (totaux[table],) = cur.fetchone()

    for role, doit_voir in CASES:
        for table in TABLES:
            with conn.cursor() as cur:
                cur.execute(f"SET ROLE {role}")
                try:
                    cur.execute(f"SELECT COUNT(*) FROM {table}")
                    (compte,) = cur.fetchone()
                except psycopg2.errors.InsufficientPrivilege:
                    conn.rollback()
                    compte = 0
                cur.execute("RESET ROLE")

            attendu = totaux[table] if doit_voir else 0
            statut = "OK" if compte == attendu else "ECHEC"
            print(f"[{statut}] {role} / {table}: {compte} lignes (attendu {attendu})")
            if compte != attendu:
                echecs.append((role, table, compte, attendu))

    conn.close()

    assert not echecs, f"RLS incorrecte: {echecs}"
    n_articles = totaux["marts.dim_stock_articles"]
    n_mouvements = totaux["marts.fait_mouvements_stock"]
    print(f"self-check OK: {len(CASES)} roles verifies sur {n_articles} articles / {n_mouvements} mouvements")


if __name__ == "__main__":
    main()
