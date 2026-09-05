"""Adaptateur generique -- factures fournisseurs recues pendant la
periode de transition de la reforme francaise de facturation
electronique. Deux canaux geres par le meme adaptateur, parce que c'est
la meme source metier (facturation entrante), pas deux sources
differentes : Factur-X structure (XML) et PDF non structure (best-effort,
confiance degradee)."""

from __future__ import annotations

import re
from pathlib import Path
from xml.etree import ElementTree as ET


def lire_facturx_xml(path: Path) -> list[dict]:
    """Canal structure -- tous les champs sont fiables par construction
    (norme EN16931/UBL/CII)."""
    racine = ET.parse(path).getroot()
    factures = []
    for inv in racine.findall("Invoice"):
        factures.append(
            {
                "numero_facture": inv.findtext("InvoiceNumber"),
                "date_facture": inv.findtext("IssueDate"),
                "fournisseur_nom": inv.findtext("Seller/Name"),
                "fournisseur_siren": inv.findtext("Seller/SIREN") or None,
                "montant_ht": inv.findtext("TaxableAmount"),
                "montant_tva": inv.findtext("TaxAmount"),
                "montant_ttc": inv.findtext("GrandTotalAmount"),
                "canal": "facturx",
            }
        )
    return factures


_RE_NUMERO = re.compile(r"FACTURE N\.\s*(\S+)")
_RE_FOURNISSEUR = re.compile(r"Fournisseur:\s*(.+)")
_RE_SIREN = re.compile(r"SIREN:\s*(\S+)")
_RE_DATE = re.compile(r"Date:\s*(\S+)")
_RE_MONTANT = re.compile(r"Montant TTC:\s*([\d.,?X]+)\s*EUR")


def lire_facture_non_structuree(path: Path) -> list[dict]:
    """Canal degrade -- extraction best-effort par regex sur un texte
    OCR-like, champs potentiellement absents ou illisibles (conserves
    comme tels, pas devines)."""
    contenu = path.read_text(encoding="utf-8")
    factures = []
    for bloc in contenu.split("\n\n---\n\n"):
        if not bloc.strip():
            continue
        m_montant = _RE_MONTANT.search(bloc)
        montant = m_montant.group(1) if m_montant else None
        montant_lisible = montant is not None and "?" not in montant and "X" not in montant

        factures.append(
            {
                "numero_facture": (m := _RE_NUMERO.search(bloc)) and m.group(1),
                "date_facture": (m := _RE_DATE.search(bloc)) and m.group(1),
                "fournisseur_nom": (m := _RE_FOURNISSEUR.search(bloc)) and m.group(1),
                "fournisseur_siren": (m := _RE_SIREN.search(bloc)) and m.group(1),
                "montant_ht": None,  # jamais fourni cote non structure
                "montant_tva": None,
                "montant_ttc": montant if montant_lisible else None,
                "canal": "non_structure",
            }
        )
    return factures
