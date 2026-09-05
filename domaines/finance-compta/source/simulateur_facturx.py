"""Simule la reception des factures fournisseurs pendant la periode de
transition de la reforme francaise de facturation electronique : une
part croissante de fournisseurs migre vers Factur-X (XML structure,
inspire EN16931/UBL/CII) au fil des mois, le reste reste en PDF non
structure (simule ici par un texte OCR-like, champs manquants/degrades --
pas de vraie extraction PDF, la valeur est dans le contraste
structure/non-structure, pas dans le format de fichier lui-meme).

Pourquoi ce n'est pas un vrai fichier Factur-X (PDF/A-3 + XML embarque) :
generer un PDF conforme demanderait une bibliotheque dediee (ex. paquet
`factur-x`) pour un gain d'authenticite marginal ici -- ce qui compte
pour le nettoyage en aval, ce sont les CHAMPS structures (ou leur
absence), pas le conteneur PDF. Hypothese assumee, documentee dans
decisions.md.

Le taux de migration croit de 20% (janvier) a 65% (aout) -- une vraie
adoption progressive de la reforme, pas un interrupteur brutal.
"""

from __future__ import annotations

import random
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

from faker import Faker

OUT_DIR = Path(__file__).parent / "exports"


def _fournisseurs(rng: random.Random) -> list[dict]:
    fake = Faker("fr_FR")
    Faker.seed(19)
    fournisseurs = []
    for i in range(1, 81):
        r = rng.random()
        siren = None if r < 0.05 else str(rng.randint(100000000, 999999999))
        fournisseurs.append({"id": i, "raison_sociale": fake.company(), "siren": siren})
    return fournisseurs


def generer_facturx_xml(factures: list[dict]) -> str:
    racine = Element("Invoices")
    for f in factures:
        inv = SubElement(racine, "Invoice")
        SubElement(inv, "InvoiceNumber").text = f["numero_facture"]
        SubElement(inv, "IssueDate").text = f["date_facture"]
        seller = SubElement(inv, "Seller")
        SubElement(seller, "Name").text = f["raison_sociale"]
        SubElement(seller, "SIREN").text = f["siren"] or ""
        SubElement(inv, "TaxableAmount", currency="EUR").text = f"{f['montant_ht']:.2f}"
        SubElement(inv, "TaxAmount", currency="EUR").text = f"{f['montant_tva']:.2f}"
        SubElement(inv, "GrandTotalAmount", currency="EUR").text = f"{f['montant_ttc']:.2f}"
    brut = tostring(racine, encoding="unicode")
    return minidom.parseString(brut).toprettyxml(indent="  ")


def generer_facture_non_structuree(f: dict, rng: random.Random) -> str:
    """Simule une extraction OCR degradee -- champs parfois absents ou
    illisibles, pas un format propre."""
    lignes = [f"FACTURE N. {f['numero_facture']}"]
    lignes.append(f"Fournisseur: {f['raison_sociale']}")
    if rng.random() > 0.4:  # SIREN souvent absent/illisible en PDF scanne
        lignes.append(f"SIREN: {f['siren'] or '???'}")
    lignes.append(f"Date: {f['date_facture']}")
    if rng.random() < 0.15:
        # montant illisible -- OCR a manque un chiffre
        lignes.append(f"Montant TTC: {str(f['montant_ttc'])[:-1]}?,XX EUR")
    else:
        lignes.append(f"Montant TTC: {f['montant_ttc']:.2f} EUR")
    return "\n".join(lignes)


def generer_mois(
    fournisseurs: list[dict], annee_mois: str, rng: random.Random, n: int, taux_migration: float
) -> tuple[list[dict], list[dict]]:
    annee, mois = int(annee_mois[:4]), int(annee_mois[4:])
    migrees, non_structurees = [], []
    for i in range(n):
        f = rng.choice(fournisseurs)
        jour = rng.randint(1, 28)
        montant_ht = round(rng.uniform(80, 15000), 2)
        montant_tva = round(montant_ht * 0.20, 2)
        montant_ttc = round(montant_ht + montant_tva, 2)
        # Format de numero LEGEREMENT different de celui de SQL Server
        # (FA-AAAA-MM-XXX vs FAAAAAMMXXXX cote ERP) -- rapprochement reel a construire.
        facture = {
            "numero_facture": f"FA-{annee}-{mois:02d}-{i:03d}",
            "date_facture": f"{annee}-{mois:02d}-{jour:02d}",
            "raison_sociale": f["raison_sociale"],
            "siren": f["siren"],
            "montant_ht": montant_ht,
            "montant_tva": montant_tva,
            "montant_ttc": montant_ttc,
        }
        if rng.random() < taux_migration:
            migrees.append(facture)
        else:
            non_structurees.append(facture)
    return migrees, non_structurees


def main() -> None:
    rng = random.Random(19)
    fournisseurs = _fournisseurs(rng)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    mois_simules = [f"2026{m:02d}" for m in range(1, 9)]
    taux_migration_par_mois = [0.20, 0.27, 0.34, 0.41, 0.48, 0.55, 0.60, 0.65]

    for idx, aaaamm in enumerate(mois_simules):
        n = 50 + idx * 10
        migrees, non_structurees = generer_mois(
            fournisseurs, aaaamm, rng, n, taux_migration_par_mois[idx]
        )

        (OUT_DIR / f"factures_facturx_{aaaamm}.xml").write_text(
            generer_facturx_xml(migrees), encoding="utf-8"
        )

        blocs = [generer_facture_non_structuree(f, rng) for f in non_structurees]
        (OUT_DIR / f"factures_non_structurees_{aaaamm}.txt").write_text(
            "\n\n---\n\n".join(blocs), encoding="utf-8"
        )

        print(
            f"{aaaamm}: {len(migrees)} Factur-X, {len(non_structurees)} non structurees "
            f"(migration {taux_migration_par_mois[idx]:.0%})"
        )


def _self_check() -> None:
    xml_files = list(OUT_DIR.glob("factures_facturx_*.xml"))
    txt_files = list(OUT_DIR.glob("factures_non_structurees_*.txt"))
    assert len(xml_files) == 8, f"attendu 8 XML, trouve {len(xml_files)}"
    assert len(txt_files) == 8, f"attendu 8 txt, trouve {len(txt_files)}"
    print(f"self-check OK: {len(xml_files)} mois Factur-X, {len(txt_files)} mois non structures")


if __name__ == "__main__":
    main()
    _self_check()
