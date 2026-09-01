"""Génère les 28 fichiers .txt d'avis (+ une archive zip) à partir de data/avis_test.json.

Convention de nommage attendue par la Lambda `traiter-avis` :
    {avis_id}_{date}_{client_id}.txt      ex. AV001_2026-08-17_CLI-1042.txt

Le corps du fichier contient uniquement le texte de l'avis : c'est ce qui sera
envoyé à Amazon Comprehend. Les métadonnées voyagent dans le nom du fichier,
ce qui évite d'imposer un format structuré aux systèmes qui déposent les avis.

Usage :
    python scripts/generer_fichiers_avis.py
"""

from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "src" / "couche_commune" / "python"))

from nordichome import fichiers  # noqa: E402

SOURCE = RACINE / "data" / "avis_test.json"
DOSSIER_SORTIE = RACINE / "data" / "incoming"
ARCHIVE = RACINE / "data" / "avis_incoming.zip"


def main() -> None:
    jeu_de_donnees = json.loads(SOURCE.read_text(encoding="utf-8"))
    avis = jeu_de_donnees["avis"]

    DOSSIER_SORTIE.mkdir(parents=True, exist_ok=True)
    for ancien in DOSSIER_SORTIE.glob("*.txt"):
        ancien.unlink()

    noms = []
    for item in avis:
        nom = fichiers.nom_fichier(item["avis_id"], item["date"], item["client_id"])
        (DOSSIER_SORTIE / nom).write_text(item["texte"], encoding="utf-8")
        noms.append(nom)

    with zipfile.ZipFile(ARCHIVE, "w", zipfile.ZIP_DEFLATED) as archive:
        for nom in noms:
            archive.write(DOSSIER_SORTIE / nom, arcname=nom)

    repartition: dict[str, int] = {}
    for item in avis:
        attendu = item["sentiment_attendu"]
        repartition[attendu] = repartition.get(attendu, 0) + 1

    print(f"{len(noms)} fichiers écrits dans {DOSSIER_SORTIE}")
    print(f"Archive : {ARCHIVE}")
    print("Répartition annotée manuellement :")
    for sentiment, nombre in sorted(repartition.items()):
        print(f"  {sentiment:<9} {nombre:>2}  ({nombre / len(avis):.0%})")


if __name__ == "__main__":
    main()
