"""Traitement d'une demande RGPD (droit a l'oubli) sur un contact
Marketing -- seul domaine du projet avec des donnees a caractere
personnel (cf. decisions.md, section 2). Anonymise dans `raw` (source
de verite) ; se propage a staging/marts au prochain `dbt run`, pas
besoin de toucher les marts directement.

Contrairement au mojibake/doublons (flague, jamais reecrit -- incertitude
sur la bonne valeur), une demande RGPD a une cible claire et une action
attendue explicite : ecraser reellement l'email/nom/prenom, pas un flag."""

from __future__ import annotations

import os
import sys

import psycopg2


def connecter():
    return psycopg2.connect(
        host=os.environ.get("PGHOST", "projet19-postgres"),
        port=os.environ.get("PGPORT", "5432"),
        dbname=os.environ.get("PGDATABASE", "projet19"),
        user=os.environ.get("PGUSER", "ingestion"),
        password=os.environ["PGPASSWORD"],
    )


def anonymiser(email: str) -> int:
    conn = connecter()
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            update raw.marketing_contacts
            set email = 'anonymise-' || id || '@rgpd.local',
                nom = 'ANONYMISE',
                prenom = 'ANONYMISE'
            where lower(email) = lower(%s)
            """,
            (email,),
        )
        nb = cur.rowcount
    conn.close()
    return nb


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python rgpd_anonymiser.py <email>", file=sys.stderr)
        sys.exit(1)

    email = sys.argv[1]
    nb = anonymiser(email)
    if nb == 0:
        print(f"Aucun contact trouvé pour {email} (déjà anonymisé, ou email inconnu).")
        sys.exit(1)
    print(f"{nb} contact(s) anonymisé(s) pour la demande sur {email}.")


if __name__ == "__main__":
    main()
