"""Genere la liste canonique des "vrais" evenements de facturation
(fournisseur, montant, date) -- source de verite commune consommee par
simulateur_sqlserver.py ET simulateur_facturx.py, pour que le
rapprochement facture/ecriture mesure un vrai taux de couverture plutot
que de comparer deux jeux de montants tires independamment (ce que
faisait la premiere version -- corrige apres avoir mesure un taux de
rapprochement proche de zero et en avoir identifie la cause reelle).

Couverture volontairement imparfaite (pas 100%) : 90% des evenements ont
a la fois une ecriture ET une facture recue (traitement complet), 5%
n'ont qu'une ecriture (saisie sans attendre le document, pratique reelle),
5% n'ont qu'une facture recue (recue mais pas encore comptabilisee --
delai de traitement). Ce delta de 10% EST la vraie donnee a mesurer, pas
un defaut a corriger.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from faker import Faker

OUT_DIR = Path(__file__).parent / "exports"


def generer_fournisseurs(rng: random.Random) -> list[dict]:
    fake = Faker("fr_FR")
    Faker.seed(19)
    fournisseurs = []
    for i in range(1, 81):
        r = rng.random()
        if r < 0.05:
            siren = None
        elif r < 0.10:
            siren = f"{rng.randint(100, 999)} {rng.randint(100, 999)} {rng.randint(100, 999)}"
        else:
            siren = str(rng.randint(100000000, 999999999))
        fournisseurs.append({"id": i, "raison_sociale": fake.company(), "siren": siren})
    return fournisseurs


def generer_evenements(fournisseurs: list[dict], annee_mois: str, rng: random.Random, n: int) -> list[dict]:
    annee, mois = int(annee_mois[:4]), int(annee_mois[4:])
    evenements = []
    for i in range(n):
        f = rng.choice(fournisseurs)
        jour = rng.randint(1, 28)
        montant_ht = round(rng.uniform(80, 15000), 2)
        montant_tva = round(montant_ht * 0.20, 2)
        montant_ttc = round(montant_ht + montant_tva, 2)

        r = rng.random()
        a_ecriture = r < 0.95       # 90% + 5% ecriture-seule
        a_facture = r < 0.90 or r >= 0.95  # 90% + 5% facture-seule

        evenements.append(
            {
                "annee_mois": annee_mois,
                "index": i,
                "fournisseur_id": f["id"],
                "fournisseur_nom": f["raison_sociale"],
                "fournisseur_siren": f["siren"],
                "annee": annee,
                "mois": mois,
                "jour": jour,
                "montant_ht": montant_ht,
                "montant_tva": montant_tva,
                "montant_ttc": montant_ttc,
                "a_ecriture": a_ecriture,
                "a_facture": a_facture,
            }
        )
    return evenements


def main() -> None:
    rng = random.Random(19)
    fournisseurs = generer_fournisseurs(rng)

    mois_simules = [f"2026{m:02d}" for m in range(1, 9)]
    tous_evenements = []
    for idx, aaaamm in enumerate(mois_simules):
        n = 60 + idx * 15
        tous_evenements.extend(generer_evenements(fournisseurs, aaaamm, rng, n))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with (OUT_DIR / "_evenements_communs.json").open("w", encoding="utf-8") as f:
        json.dump({"fournisseurs": fournisseurs, "evenements": tous_evenements}, f)

    n_deux = sum(1 for e in tous_evenements if e["a_ecriture"] and e["a_facture"])
    print(
        f"{len(tous_evenements)} evenements : {n_deux} avec ecriture+facture, "
        f"{sum(e['a_ecriture'] for e in tous_evenements)} avec ecriture, "
        f"{sum(e['a_facture'] for e in tous_evenements)} avec facture"
    )


if __name__ == "__main__":
    main()
