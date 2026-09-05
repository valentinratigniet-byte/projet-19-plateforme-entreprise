"""Alerte derive qualite -- compare les taux mesures en direct aux
references documentees (avant.md/apres.md de chaque domaine, mesurees a
la construction) plutot que de re-decouvrir un chiffre a chaque fois.
Seuil de derive volontairement large (+/- 10 points) : ce projet n'a
qu'une seule mesure de reference dans le temps, un ecart mineur n'est
pas forcement un signal reel -- voir ops/README.md."""

from __future__ import annotations

import os

import psycopg2

SEUIL_DERIVE_POINTS = 10.0

# (nom, requete, pct_reference, source_doc)
REFERENCES = [
    (
        "Ventes -- doublons clients probables",
        "select round(100.0 * count(*) filter (where est_doublon_probable) / count(*), 1) "
        "from staging.stg_ventes_clients",
        8.9,
        "domaines/ventes-commerce/avant.md (28/314)",
    ),
    (
        "Finance -- SIREN invalide ou absent",
        # siren_valide est NULL (pas false) quand le SIREN est absent
        # ("siren_normalise ~ regex" sur NULL renvoie NULL) -- "not
        # siren_valide" exclurait ces lignes du filtre au lieu de les
        # compter, sous-estimant le taux reel (trouve en testant : 0.0%
        # mesure au lieu des 10% attendus).
        "select round(100.0 * count(*) filter (where siren_valide is not true) / count(*), 1) "
        "from staging.stg_finance_fournisseurs",
        1.3,
        "domaines/finance-compta/avant.md (1/80)",
    ),
    (
        "Marketing -- doublons contacts probables",
        "select round(100.0 * count(*) filter (where contact_doublon_probable) / count(*), 1) "
        "from staging.stg_marketing_contacts",
        5.8,
        "domaines/marketing-activite/avant.md (12/206)",
    ),
]


def connecter():
    return psycopg2.connect(
        host=os.environ.get("PGHOST", "projet19-postgres"),
        port=os.environ.get("PGPORT", "5432"),
        dbname=os.environ.get("PGDATABASE", "projet19"),
        user=os.environ.get("PGUSER", "dbt_transform"),
        password=os.environ["PGPASSWORD"],
    )


def main() -> None:
    conn = connecter()
    derives = []

    with conn.cursor() as cur:
        for nom, requete, reference, source in REFERENCES:
            cur.execute(requete)
            (mesure,) = cur.fetchone()
            mesure = float(mesure or 0)
            ecart = abs(mesure - reference)
            statut = "DERIVE" if ecart > SEUIL_DERIVE_POINTS else "OK"
            print(f"[{statut}] {nom} : {mesure} % (référence {reference} %, {source})")
            if statut == "DERIVE":
                derives.append((nom, mesure, reference))

    conn.close()

    if derives:
        print(f"\n{len(derives)} dérive(s) détectée(s) (> {SEUIL_DERIVE_POINTS} points).")
    else:
        print("\nAucune dérive détectée.")


if __name__ == "__main__":
    main()
