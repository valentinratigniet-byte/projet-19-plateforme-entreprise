"""Reverse ETL -- calcule un segment dans l'entrepot (contacts engages :
au moins un clic, jamais desabonnes) et le repousse vers l'API SaaS pour
une action marketing concrete (ex. campagne de relance ciblee). Boucle
DE -> BA -> action metier, pas seulement DE -> reporting (cf. cadrage,
issue #2)."""

from __future__ import annotations

import os

import psycopg2

from adaptateurs.api_rest import ClientOAuth2, envoyer_segment

SAAS_BASE_URL = os.environ.get("SAAS_BASE_URL", "http://projet19-saas-mock:5000")

REQUETE_SEGMENT = """
    select distinct contact_id
    from marts.fait_envois
    where statut = 'CLIQUE'
      and contact_id not in (
          select contact_id from marts.fait_envois where statut = 'DESABONNE'
      )
"""


def calculer_segment(conn) -> list[int]:
    with conn.cursor() as cur:
        cur.execute(REQUETE_SEGMENT)
        return [row[0] for row in cur.fetchall()]


def main() -> None:
    conn = psycopg2.connect(
        host=os.environ.get("PGHOST", "projet19-postgres"),
        port=os.environ.get("PGPORT", "5432"),
        dbname=os.environ.get("PGDATABASE", "projet19"),
        user=os.environ.get("PGUSER", "dbt_transform"),  # job interne entrepot, pas un acces utilisateur final
        password=os.environ["PGPASSWORD"],
    )
    contacts = calculer_segment(conn)
    conn.close()

    oauth = ClientOAuth2(
        f"{SAAS_BASE_URL}/oauth/token",
        os.environ.get("SAAS_CLIENT_ID", "projet19"),
        os.environ["SAAS_CLIENT_SECRET"],
    )
    resultat = envoyer_segment(
        oauth, f"{SAAS_BASE_URL}/api/segments",
        {"nom": "contacts_engages_non_desabonnes", "contacts": contacts},
    )
    print(f"Segment envoye : {resultat}")

    assert resultat["taille_segment"] == len(contacts), "le SaaS n'a pas recu le bon nombre de contacts"
    print("self-check OK")


if __name__ == "__main__":
    main()
