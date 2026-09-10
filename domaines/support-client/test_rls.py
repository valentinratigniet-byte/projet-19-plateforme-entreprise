"""Verifie la RLS reellement, par SET ROLE -- pas seulement que la policy
existe (meme discipline que les 3 autres domaines). Ici l'acces refuse
se manifeste par une erreur "permission denied for table" (aucun GRANT
SELECT pose pour ces roles), pas par 0 ligne via une policy RLS
`USING (false)` explicite -- role_rh/role_finance/role_commercial
n'ont aucun usage metier sur des tickets SAV, pas de raison de leur
donner acces a la table pour ensuite le refuser via policy."""

from __future__ import annotations

import os

import psycopg2

CASES = [
    # (role, acces_attendu)
    ("role_rh", False),
    ("role_finance", False),
    ("role_commercial", False),
    ("role_direction", True),
    ("role_support", True),
]
N_TICKETS_ATTENDU = None  # rempli dynamiquement (compte reel, pas fige)


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

    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM marts.fait_tickets")
        (total,) = cur.fetchone()

    for role, doit_voir in CASES:
        with conn.cursor() as cur:
            cur.execute(f"SET ROLE {role}")
            try:
                cur.execute("SELECT COUNT(*) FROM marts.fait_tickets")
                (compte,) = cur.fetchone()
            except psycopg2.errors.InsufficientPrivilege:
                conn.rollback()
                compte = 0
            cur.execute("RESET ROLE")

        attendu = total if doit_voir else 0
        statut = "OK" if compte == attendu else "ECHEC"
        print(f"[{statut}] {role}: {compte} lignes (attendu {attendu})")
        if compte != attendu:
            echecs.append((role, compte, attendu))

    conn.close()

    assert not echecs, f"RLS incorrecte: {echecs}"
    print(f"self-check OK: {len(CASES)} cas verifies sur {total} tickets")


if __name__ == "__main__":
    main()
