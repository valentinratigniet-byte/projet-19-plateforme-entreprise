"""Adaptateur generique -- fichier CSV, delimiteur configurable (les
exports bancaires francais utilisent souvent ';', pas ',')."""

from __future__ import annotations

import csv
from pathlib import Path


def lire_csv(path: Path, delimiter: str = ",", encoding: str = "utf-8") -> list[dict]:
    with open(path, encoding=encoding, newline="") as f:
        return list(csv.DictReader(f, delimiter=delimiter))
