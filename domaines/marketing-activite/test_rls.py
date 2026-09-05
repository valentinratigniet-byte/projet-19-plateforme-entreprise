"""Verifie la RLS reellement, par SET ROLE -- y compris l'ABSENCE
d'acces de role_direction aux tables contenant des donnees personnelles
(pas seulement des lignes filtrees, aucun GRANT du tout)."""

from __future__ import annotations

import os

import psycopg2

CASES_LIGNES = [
    ("role_rh", "marts.dim_contact", 0),
    ("role_rh", "marts.fait_envois", 0),
    ("role_marketing", "marts.dim_contact", 206),
    ("role_marketing", "marts.fait_envois", 755),
    ("role_marketing", "marts.fait_performance_campagnes", 8),
    ("role_direction", "marts.fait_performance_campagnes", 8),
]

TABLES_INTERDITES_DIRECTION = ["marts.dim_contact", "marts.fait_envois", "marts.fait_evenements_web"]


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


def verifier_direction_sans_acces_pii(conn) -> list[str]:
    echecs = []
    for table in TABLES_INTERDITES_DIRECTION:
        with conn.cursor() as cur:
            cur.execute("SET ROLE role_direction")
            try:
                cur.execute(f"SELECT * FROM {table} LIMIT 1")
                cur.fetchall()
                echecs.append(f"role_direction a pu lire {table} (ne devrait pas)")
                print(f"[ECHEC] role_direction a pu lire {table}")
            except psycopg2.errors.InsufficientPrivilege:
                print(f"[OK] role_direction ne peut pas lire {table} (comme attendu)")
    with conn.cursor() as cur:
        cur.execute("RESET ROLE")
    return echecs


def main() -> None:
    conn = connecter()
    conn.autocommit = True

    echecs = verifier_lignes(conn)
    echecs += verifier_direction_sans_acces_pii(conn)

    conn.close()

    assert not echecs, f"RLS incorrecte: {echecs}"
    print(f"self-check OK: {len(CASES_LIGNES)} cas de lignes + {len(TABLES_INTERDITES_DIRECTION)} cas d'absence d'acces verifies")


if __name__ == "__main__":
    main()
