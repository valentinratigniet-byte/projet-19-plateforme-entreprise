"""Simule le flux JSON evenementiel (tracking web) -- consomme les
evenements canoniques de `generer_evenements.py` (mêmes contacts/
campagnes que MySQL, pour un funnel reel). Un fichier par mois, comme un
export/dump quotidien agrege cote analytics.

Defauts reels :
  - UTM incoherents (casse, valeurs manquantes) deja injectes en amont
  - evenements domain-dupliques (retry client) ajoutes ici
  - structure semi-structuree a aplatir (objet `contexte` imbrique)
"""

from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path

EVENEMENTS_PATH = Path(__file__).parent / "exports" / "_evenements_communs_marketing.json"
OUT_DIR = Path(__file__).parent / "exports"


def mettre_en_forme(e: dict) -> dict:
    """Structure semi-structuree volontaire (objet imbrique `contexte`) --
    a aplatir en staging, pas ici."""
    return {
        "session_id": e["session_id"],
        "contact_id": e["contact_id"],
        "type": e["type_evenement"],
        "horodatage": e["horodatage"],
        "contexte": {
            "utm_source": e["utm_source"],
            "utm_medium": e["utm_medium"],
            "utm_campaign": e["utm_campaign"],
            "page": e["url"],
        },
    }


def main() -> None:
    rng = random.Random(19)

    with EVENEMENTS_PATH.open(encoding="utf-8") as f:
        donnees = json.load(f)
    evenements = donnees["evenements_web"]

    par_mois: dict[str, list[dict]] = defaultdict(list)
    for e in evenements:
        mois = e["horodatage"][:7].replace("-", "")
        bloc = mettre_en_forme(e)
        par_mois[mois].append(bloc)
        # ~3% d'evenements domain-dupliques (retry client reel)
        if rng.random() < 0.03:
            par_mois[mois].append(dict(bloc))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for mois, blocs in sorted(par_mois.items()):
        (OUT_DIR / f"evenements_web_{mois}.json").write_text(
            json.dumps(blocs, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"{mois}: {len(blocs)} evenements")


def _self_check() -> None:
    fichiers = list(OUT_DIR.glob("evenements_web_*.json"))
    assert fichiers, "aucun fichier d'evenements genere"
    for f in fichiers:
        blocs = json.loads(f.read_text(encoding="utf-8"))
        assert blocs, f"{f.name} vide"
    print(f"self-check OK: {len(fichiers)} mois d'evenements generes")


if __name__ == "__main__":
    main()
    _self_check()
