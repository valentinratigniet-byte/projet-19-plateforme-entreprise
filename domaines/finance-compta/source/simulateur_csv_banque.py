"""Simule l'export CSV mensuel du releve bancaire -- utilise pour le
rapprochement paiement/facture. Format volontairement fidele a un vrai
export bancaire francais : delimiteur point-virgule (le separateur
decimal virgule entrerait en conflit avec une virgule-CSV), montants en
texte format FR.

Defauts reels injectes :
  - libelle qui ne reference le fournisseur QUE par un extrait du nom
    (troncature, prefixe "VIR"/"PRLV") -- pas de FournisseurID, rapprochement
    a construire, pas donne
  - quelques lignes dupliquees (rejeu d'export bancaire, arrive reellement)
  - montants en negatif pour les paiements sortants (convention bancaire)
"""

from __future__ import annotations

import csv
import random
from datetime import date
from pathlib import Path

OUT_DIR = Path(__file__).parent / "exports"


def montant_fr(valeur: float) -> str:
    return f"{valeur:,.2f}".replace(",", " ").replace(".", ",")


def generer_mois(
    fournisseurs: list[dict], annee_mois: str, rng: random.Random, n: int
) -> list[dict]:
    annee, mois = int(annee_mois[:4]), int(annee_mois[4:])
    lignes = []
    for _ in range(n):
        f = rng.choice(fournisseurs)
        jour = rng.randint(1, 28)
        d = date(annee, mois, jour)
        montant = -round(rng.uniform(80, 15000), 2)

        # Libelle bancaire realiste : extrait tronque du nom, pas le nom complet
        nom_tronque = f["raison_sociale"][: rng.randint(8, 16)].upper()
        prefixe = rng.choice(["VIR", "PRLV"])
        libelle = f"{prefixe} {nom_tronque}"

        lignes.append(
            {
                "Date operation": d.strftime("%d/%m/%Y"),
                "Libelle": libelle,
                "Montant": montant_fr(montant),
                "Devise": "EUR",
            }
        )

        # ~2% de lignes dupliquees -- rejeu d'export bancaire, arrive reellement
        if rng.random() < 0.02:
            lignes.append(dict(lignes[-1]))

    return lignes


def ecrire_csv(path: Path, lignes: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="cp1252", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["Date operation", "Libelle", "Montant", "Devise"], delimiter=";"
        )
        writer.writeheader()
        writer.writerows(lignes)


# Noms de fournisseurs -- doivent rester coherents avec ceux generes dans
# simulateur_sqlserver.py pour permettre un vrai rapprochement plus tard.
# Genere ici avec la meme seed/logique pour rester dans le meme univers.
def _noms_fournisseurs(rng: random.Random) -> list[dict]:
    from faker import Faker

    fake = Faker("fr_FR")
    Faker.seed(19)
    return [{"raison_sociale": fake.company()} for _ in range(80)]


def main() -> None:
    rng = random.Random(19)
    fournisseurs = _noms_fournisseurs(rng)

    mois_simules = [f"2026{m:02d}" for m in range(1, 9)]
    for idx, aaaamm in enumerate(mois_simules):
        n = 40 + idx * 8
        lignes = generer_mois(fournisseurs, aaaamm, rng, n)
        ecrire_csv(OUT_DIR / f"releve_bancaire_{aaaamm}.csv", lignes)
        print(f"{aaaamm}: {len(lignes)} lignes")


def _self_check() -> None:
    fichiers = list(OUT_DIR.glob("releve_bancaire_*.csv"))
    assert len(fichiers) == 8, f"attendu 8 fichiers, trouve {len(fichiers)}"
    for f in fichiers:
        with f.open(encoding="cp1252") as fh:
            rows = list(csv.DictReader(fh, delimiter=";"))
        assert rows, f"{f.name} vide"
    print(f"self-check OK: {len(fichiers)} fichiers de releve generes")


if __name__ == "__main__":
    main()
    _self_check()
