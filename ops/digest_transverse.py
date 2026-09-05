"""Digest hebdomadaire transverse -- agrege les 3 marts deja verifies
individuellement (Ventes/Finance/Marketing) en un seul resume. Boucle
DE -> BA du cadrage (issue #2), jamais automatisee jusqu'ici -- chaque
chiffre est deja mesure ailleurs (dbt tests), ce script les rassemble."""

from __future__ import annotations

import os
from datetime import datetime, timezone

import psycopg2


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
    print(f"=== Digest transverse -- {datetime.now(timezone.utc).isoformat()} ===")

    with conn.cursor() as cur:
        cur.execute(
            "select sum(montant_net_eur) from marts.fait_ventes where statut = 'VALIDEE'"
        )
        (ca_net,) = cur.fetchone()
        print(f"Ventes -- CA net (commandes validées) : {ca_net:,.2f} EUR")

        cur.execute(
            "select canal, count(*), count(*) filter (where rapprochee) "
            "from marts.fait_rapprochement_factures group by canal"
        )
        for canal, total, rapprochees in cur.fetchall():
            pct = 100.0 * rapprochees / total if total else 0
            print(f"Finance -- rapprochement {canal} : {rapprochees}/{total} ({pct:.0f} %)")

        cur.execute(
            "select count(*), count(*) filter (where coherent_avec_mysql) "
            "from marts.fait_performance_campagnes"
        )
        total, coherentes = cur.fetchone()
        print(f"Marketing -- campagnes cohérentes SaaS/MySQL : {coherentes}/{total}")

    conn.close()


if __name__ == "__main__":
    main()
