"""Adaptateur generique -- fichier JSON (liste d'objets, potentiellement
semi-structures). Aplatit les objets imbriques en colonnes plates pour le
stockage relationnel (necessite structurel de l'ingestion, PAS une regle
de nettoyage -- les valeurs restent inchangees, seul l'arbre devient une
ligne)."""

from __future__ import annotations

import json
from pathlib import Path


def _aplatir(objet: dict, prefixe: str = "") -> dict:
    plat = {}
    for cle, valeur in objet.items():
        nom = f"{prefixe}{cle}" if not prefixe else f"{prefixe}_{cle}"
        if isinstance(valeur, dict):
            plat.update(_aplatir(valeur, nom))
        else:
            plat[nom] = valeur
    return plat


def lire_json(path: Path) -> list[dict]:
    objets = json.loads(path.read_text(encoding="utf-8"))
    return [_aplatir(o) for o in objets]
