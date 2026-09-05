"""Simule la reception des factures fournisseurs pendant la periode de
transition de la reforme francaise de facturation electronique.

Consomme les evenements canoniques de `generer_evenements.py` (montants
reels partages avec SQL Server, pour que le rapprochement facture/ecriture
mesure un vrai taux de couverture plutot que deux jeux de montants tires
independamment -- corrige apres avoir mesure un taux de rapprochement
proche de zero en premiere version).

Part croissante de fournisseurs migres vers Factur-X (XML structure,
inspire EN16931/UBL/CII) au fil des mois, le reste en PDF non structure
(simule par un texte OCR-like, champs manquants/degrades).

Pourquoi ce n'est pas un vrai fichier Factur-X (PDF/A-3 + XML embarque) :
generer un PDF conforme demanderait une bibliotheque dediee pour un gain
d'authenticite marginal ici -- ce qui compte pour le nettoyage en aval,
ce sont les CHAMPS structures (ou leur absence), pas le conteneur PDF.
Hypothese assumee, documentee dans decisions.md.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

EVENEMENTS_PATH = Path(__file__).parent / "exports" / "_evenements_communs.json"
OUT_DIR = Path(__file__).parent / "exports"

TAUX_MIGRATION = {
    "202601": 0.20, "202602": 0.27, "202603": 0.34, "202604": 0.41,
    "202605": 0.48, "202606": 0.55, "202607": 0.60, "202608": 0.65,
}


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
    lignes = [f"FACTURE N. {f['numero_facture']}"]
    lignes.append(f"Fournisseur: {f['raison_sociale']}")
    if rng.random() > 0.4:
        lignes.append(f"SIREN: {f['siren'] or '???'}")
    lignes.append(f"Date: {f['date_facture']}")
    if rng.random() < 0.15:
        lignes.append(f"Montant TTC: {str(f['montant_ttc'])[:-1]}?,XX EUR")
    else:
        lignes.append(f"Montant TTC: {f['montant_ttc']:.2f} EUR")
    return "\n".join(lignes)


def construire_facture(e: dict, index_local: int) -> dict:
    return {
        "numero_facture": f"FA-{e['annee']}-{e['mois']:02d}-{index_local:03d}",
        "date_facture": f"{e['annee']}-{e['mois']:02d}-{e['jour']:02d}",
        "raison_sociale": e["fournisseur_nom"],
        "siren": e["fournisseur_siren"],
        "montant_ht": e["montant_ht"],
        "montant_tva": e["montant_tva"],
        "montant_ttc": e["montant_ttc"],
    }


def main() -> None:
    rng = random.Random(19)

    with EVENEMENTS_PATH.open(encoding="utf-8") as f:
        donnees = json.load(f)
    evenements = donnees["evenements"]

    par_mois: dict[str, list[dict]] = {}
    for e in evenements:
        if e["a_facture"]:
            par_mois.setdefault(e["annee_mois"], []).append(e)

    for aaaamm, evts in sorted(par_mois.items()):
        taux = TAUX_MIGRATION[aaaamm]
        migrees, non_structurees = [], []
        for i, e in enumerate(evts):
            facture = construire_facture(e, i)
            if rng.random() < taux:
                migrees.append(facture)
            else:
                non_structurees.append(facture)

        (OUT_DIR / f"factures_facturx_{aaaamm}.xml").write_text(
            generer_facturx_xml(migrees), encoding="utf-8"
        )
        blocs = [generer_facture_non_structuree(f, rng) for f in non_structurees]
        (OUT_DIR / f"factures_non_structurees_{aaaamm}.txt").write_text(
            "\n\n---\n\n".join(blocs), encoding="utf-8"
        )
        print(f"{aaaamm}: {len(migrees)} Factur-X, {len(non_structurees)} non structurees (migration {taux:.0%})")


def _self_check() -> None:
    xml_files = list(OUT_DIR.glob("factures_facturx_*.xml"))
    txt_files = list(OUT_DIR.glob("factures_non_structurees_*.txt"))
    assert len(xml_files) == 8, f"attendu 8 XML, trouve {len(xml_files)}"
    assert len(txt_files) == 8, f"attendu 8 txt, trouve {len(txt_files)}"
    print(f"self-check OK: {len(xml_files)} mois Factur-X, {len(txt_files)} mois non structures")


if __name__ == "__main__":
    main()
    _self_check()
