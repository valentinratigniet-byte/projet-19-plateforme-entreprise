"""Verifie la RLS reellement, par SET ROLE -- pas seulement que les
policies existent (meme discipline que le Projet 18)."""

from __future__ import annotations

import os

import psycopg2

CASES = [
    # (role, table, count_attendu)
    ("role_rh", "marts.fait_ventes", 0),
    ("role_rh", "marts.dim_client", 0),
    ("role_finance", "marts.fait_ventes", 2320),
    ("role_finance", "marts.dim_client", 314),
    ("role_direction", "marts.fait_ventes", 2320),
    ("role_direction", "marts.dim_client", 314),
    ("role_commercial", "marts.fait_ventes", 2052),  # 2320 - 268 ANNULEE
    ("role_commercial", "marts.dim_client", 314),
]


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

    for role, table, attendu in CASES:
        with conn.cursor() as cur:
            cur.execute(f"SET ROLE {role}")
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            (compte,) = cur.fetchone()
            cur.execute("RESET ROLE")

        statut = "OK" if compte == attendu else "ECHEC"
        print(f"[{statut}] {role} sur {table}: {compte} lignes (attendu {attendu})")
        if compte != attendu:
            echecs.append((role, table, compte, attendu))

    conn.close()

    assert not echecs, f"RLS incorrecte: {echecs}"
    print(f"self-check OK: {len(CASES)} cas verifies")


if __name__ == "__main__":
    main()
