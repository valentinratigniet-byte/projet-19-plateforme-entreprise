"""Adaptateur generique -- fichier plat a largeur fixe (AS/400 et
equivalents). Un seul parseur reutilisable par n'importe quel domaine qui
recoit ce type de source, pas un parseur par domaine."""

from __future__ import annotations

from pathlib import Path


def lire_fichier_plat(
    path: Path, spec: list[tuple[str, int]], encoding: str = "cp1252"
) -> list[dict[str, str]]:
    largeur_totale = sum(w for _, w in spec)
    lignes: list[dict[str, str]] = []
    with open(path, encoding=encoding) as f:
        for numero, brute in enumerate(f, start=1):
            brute = brute.rstrip("\r\n")
            if len(brute) != largeur_totale:
                raise ValueError(
                    f"{path.name} ligne {numero}: largeur {len(brute)} "
                    f"!= attendue {largeur_totale}"
                )
            row: dict[str, str] = {}
            pos = 0
            for nom, largeur in spec:
                row[nom] = brute[pos : pos + largeur].strip()
                pos += largeur
            lignes.append(row)
    return lignes
