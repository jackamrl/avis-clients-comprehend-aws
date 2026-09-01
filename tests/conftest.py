"""Rend la couche partagée importable comme elle l'est dans Lambda.

Sur AWS, le contenu de `src/couche_commune/python/` est monté dans
`/opt/python`, présent par défaut dans le PYTHONPATH de l'exécution Lambda.
En local, on reproduit ce montage.
"""

import json
import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "src" / "couche_commune" / "python"))


@pytest.fixture(scope="session")
def jeu_de_donnees() -> dict:
    return json.loads((RACINE / "data" / "avis_test.json").read_text(encoding="utf-8"))
