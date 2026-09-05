"""Verifie la RLS + la restriction colonne (IBAN) reellement, par
SET ROLE -- meme discipline que le domaine Ventes/Commerce."""

from __future__ import annotations

import os

import psycopg2

CASES_LIGNES = [
    # (role, table, count_attendu)
    ("role_rh", "marts.fait_ecritures", 0),
    ("role_rh", "marts.dim_fournisseur", 0),
    ("role_rh", "marts.fait_rapprochement_factures", 0),
    ("role_finance", "marts.fait_ecritures", 855),
    ("role_finance", "marts.dim_fournisseur", 80),
    ("role_direction", "marts.fait_ecritures", 855),
    ("role_direction", "marts.dim_fournisseur", 80),
]


def connecter():
    return psycopg2.connect(
        host=os.environ.get("PGHOST", "projet19-postgres"),
        port=os.environ.get("PGPORT", "5432"),
        dbname=os.environ.get("PGDATABASE", "projet19"),
        user=os.environ.get("PGSUPERUSER", "postgres"),
        password=os.environ["PGSUPERUSER_PASSWORD"],
    )


def verifier_lignes(conn) -> list[str]:
    echecs = []
    for role, table, attendu in CASES_LIGNES:
        with conn.cursor() as cur:
            cur.execute(f"SET ROLE {role}")
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            (compte,) = cur.fetchone()
            cur.execute("RESET ROLE")
        statut = "OK" if compte == attendu else "ECHEC"
        print(f"[{statut}] {role} sur {table}: {compte} lignes (attendu {attendu})")
        if compte != attendu:
            echecs.append(f"{role}/{table}: {compte} != {attendu}")
    return echecs


def verifier_colonne_iban(conn) -> list[str]:
    """role_finance doit voir l'IBAN, role_direction non (colonne
    revoquee) -- verifie par une vraie tentative de SELECT, pas en lisant
    les GRANT declares."""
    echecs = []
    with conn.cursor() as cur:
        cur.execute("SET ROLE role_finance")
        cur.execute("SELECT iban FROM marts.dim_fournisseur LIMIT 1")
        cur.fetchall()
        cur.execute("RESET ROLE")
    print("[OK] role_finance peut lire dim_fournisseur.iban")

    with conn.cursor() as cur:
        cur.execute("SET ROLE role_direction")
        try:
            cur.execute("SELECT iban FROM marts.dim_fournisseur LIMIT 1")
            cur.fetchall()
            echecs.append("role_direction a pu lire iban (ne devrait pas)")
            print("[ECHEC] role_direction a pu lire dim_fournisseur.iban")
        except psycopg2.errors.InsufficientPrivilege:
            print("[OK] role_direction ne peut pas lire dim_fournisseur.iban (comme attendu)")

    with conn.cursor() as cur:
        cur.execute("RESET ROLE")
    return echecs


def main() -> None:
    conn = connecter()
    conn.autocommit = True

    echecs = verifier_lignes(conn)
    echecs += verifier_colonne_iban(conn)

    conn.close()

    assert not echecs, f"RLS/colonne incorrecte: {echecs}"
    print(f"self-check OK: {len(CASES_LIGNES)} cas de lignes + 1 cas de colonne verifies")


if __name__ == "__main__":
    main()
