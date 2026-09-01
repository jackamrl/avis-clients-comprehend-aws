"""Exécute la chaîne d'agrégation en local, sans déployer sur AWS.

Deux modes :

  * hors ligne (par défaut) — le sentiment est repris de l'annotation manuelle
    `sentiment_attendu` du jeu de données. Permet de mettre au point le lexique
    de thèmes sans consommer de crédits ni de quota Comprehend.

  * réel (`--comprehend`) — appelle véritablement Amazon Comprehend avec les
    identifiants AWS courants, puis mesure la concordance entre l'annotation
    manuelle et la prédiction du service. C'est le chiffre à citer en soutenance
    quand on demande « comment savez-vous que ça marche ? ».

Usage :
    python scripts/simulation_locale.py
    python scripts/simulation_locale.py --comprehend --region eu-west-1
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "src" / "couche_commune" / "python"))

from nordichome import agregation, texte as util_texte, themes as lexique  # noqa: E402

JEU_DE_DONNEES = RACINE / "data" / "avis_test.json"


def _preparer_console() -> None:
    """La console Windows par défaut est en cp1252 et ignore les séquences ANSI."""
    for flux in (sys.stdout, sys.stderr):
        try:
            flux.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    if sys.platform == "win32":
        try:
            import ctypes

            noyau = ctypes.windll.kernel32
            # ENABLE_VIRTUAL_TERMINAL_PROCESSING (0x4) + modes de sortie par défaut.
            noyau.SetConsoleMode(noyau.GetStdHandle(-11), 7)
        except Exception:
            pass


_preparer_console()

VERT, ROUGE, GRIS, GRAS, FIN = "\033[92m", "\033[91m", "\033[90m", "\033[1m", "\033[0m"


def mots_cles_hors_ligne(texte_avis: str) -> list[str]:
    """Substitut grossier de `detect_key_phrases` pour le mode hors ligne."""
    vus: list[str] = []
    for mot in util_texte.normaliser(texte_avis).split():
        if len(mot) >= 6 and mot not in util_texte.TERMES_IGNORES and mot not in vus:
            vus.append(mot)
    return vus[:12]


def analyser_avec_comprehend(avis: list[dict], region: str) -> list[dict]:
    import boto3

    comprehend = boto3.client("comprehend", region_name=region)
    resultats = []

    for index, item in enumerate(avis, start=1):
        sentiment = comprehend.detect_sentiment(Text=item["texte"], LanguageCode="fr")
        phrases = comprehend.detect_key_phrases(Text=item["texte"], LanguageCode="fr")

        mots = []
        for phrase in sorted(phrases["KeyPhrases"], key=lambda p: -p["Score"]):
            terme = util_texte.nettoyer_phrase_cle(phrase["Text"])
            if terme and terme not in mots:
                mots.append(terme)

        etiquette = sentiment["Sentiment"]
        resultats.append(
            {
                **item,
                "sentiment": etiquette,
                "score_confiance": sentiment["SentimentScore"][etiquette.capitalize()],
                "mots_cles": mots[:15],
            }
        )
        print(f"\r  Comprehend : {index}/{len(avis)} avis", end="", file=sys.stderr)

    print(file=sys.stderr)
    return resultats


def analyser_hors_ligne(avis: list[dict]) -> list[dict]:
    return [
        {
            **item,
            "sentiment": item["sentiment_attendu"],
            "score_confiance": 0.95,
            "mots_cles": mots_cles_hors_ligne(item["texte"]),
        }
        for item in avis
    ]


def afficher_rapport(rapport: dict) -> None:
    print()
    print(f"{GRAS}RAPPORT HEBDOMADAIRE — semaine {rapport['semaine_id']}{FIN}")
    print(f"{GRIS}{'-' * 68}{FIN}")
    print(f"Période        : {rapport['periode_debut']} au {rapport['periode_fin']}")
    print(f"Avis analysés  : {rapport['nb_avis']}")
    print(f"Tendance       : {GRAS}{rapport['tendance']}{FIN}")
    print()
    print(f"  {VERT}Positifs{FIN}  {rapport['pct_positif']:>5} %  ({rapport['nb_positif']})")
    print(f"  {ROUGE}Négatifs{FIN}  {rapport['pct_negatif']:>5} %  ({rapport['nb_negatif']})")
    print(f"  {GRIS}Neutres{FIN}   {rapport['pct_neutre']:>5} %  ({rapport['nb_neutre']})")
    print(f"  {GRIS}Mitigés{FIN}   {rapport['pct_mixte']:>5} %  ({rapport['nb_mixte']})")

    for titre, couleur, cle in (
        ("CE QUI A POSÉ PROBLÈME", ROUGE, "top_negatifs"),
        ("CE QUI A BIEN FONCTIONNÉ", VERT, "top_positifs"),
    ):
        print()
        print(f"{couleur}{GRAS}{titre}{FIN}")
        if not rapport[cle]:
            print(f"  {GRIS}aucun thème récurrent{FIN}")
        for entree in rapport[cle]:
            barre = "█" * max(1, round(float(entree["part"]) / 5))
            print(
                f"  {entree['libelle']:<38} {entree['occurrences']:>2} avis "
                f"{entree['part']:>5} %  {couleur}{barre}{FIN}"
            )
            for exemple in entree["exemples"][:1]:
                print(f"      {GRIS}« {exemple['extrait'][:88]}… »{FIN}")


def evaluer_themes(avis_analyses: list[dict]) -> None:
    """Compare les thèmes détectés par le lexique aux thèmes injectés à dessein."""
    attendus_total = trouves_total = 0
    manques: list[str] = []
    supplements: list[str] = []

    for item in avis_analyses:
        attendus = set(item.get("themes_attendus", []))
        detectes = set(lexique.detecter(item["texte"], item.get("mots_cles", [])))

        attendus_total += len(attendus)
        trouves_total += len(attendus & detectes)
        manques += [f"{item['avis_id']} · {lexique.libelle(t)}" for t in attendus - detectes]
        supplements += [f"{item['avis_id']} · {lexique.libelle(t)}" for t in detectes - attendus]

    rappel = trouves_total / attendus_total if attendus_total else 0
    print()
    print(f"{GRAS}QUALITÉ DE LA DÉTECTION DE THÈMES{FIN}")
    print(f"{GRIS}{'-' * 68}{FIN}")
    print(f"Thèmes injectés volontairement  : {attendus_total}")
    print(f"Thèmes retrouvés par le lexique : {trouves_total}  (rappel {rappel:.0%})")
    print(f"Thèmes détectés en plus         : {len(supplements)}")

    if manques:
        print()
        print(f"{ROUGE}Attendus mais non détectés (angles morts du lexique){FIN}")
        for libelle in manques:
            print(f"  - {libelle}")

    if supplements:
        print()
        print(f"{GRIS}Détectés en plus de l'annotation manuelle. Ce ne sont pas{FIN}")
        print(f"{GRIS}nécessairement des erreurs : l'avis évoque bien le sujet.{FIN}")
        for libelle in supplements:
            print(f"  - {libelle}")


def evaluer_sentiments(avis_analyses: list[dict]) -> None:
    concordants = sum(
        1 for item in avis_analyses if item["sentiment"] == item["sentiment_attendu"]
    )
    total = len(avis_analyses)
    print()
    print(f"{GRAS}CONCORDANCE COMPREHEND / ANNOTATION MANUELLE{FIN}")
    print(f"{GRIS}{'-' * 68}{FIN}")
    print(f"{concordants}/{total} avis concordants ({concordants / total:.0%})")

    for item in avis_analyses:
        if item["sentiment"] != item["sentiment_attendu"]:
            print(
                f"  {item['avis_id']} : attendu {item['sentiment_attendu']:<8} "
                f"-> Comprehend {item['sentiment']}"
            )


def main() -> None:
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument(
        "--comprehend", action="store_true", help="appeler réellement Amazon Comprehend"
    )
    analyseur.add_argument("--region", default="eu-west-1")
    analyseur.add_argument("--json", action="store_true", help="sortie JSON brute")
    arguments = analyseur.parse_args()

    jeu = json.loads(JEU_DE_DONNEES.read_text(encoding="utf-8"))
    avis = jeu["avis"]

    if arguments.comprehend:
        avis_analyses = analyser_avec_comprehend(avis, arguments.region)
    else:
        avis_analyses = analyser_hors_ligne(avis)

    debut = date.fromisoformat(jeu["periode"]["debut"])
    fin = date.fromisoformat(jeu["periode"]["fin"])
    rapport = agregation.agreger(avis_analyses, debut, fin)

    if arguments.json:
        print(json.dumps(rapport, default=float, ensure_ascii=False, indent=2))
        return

    afficher_rapport(rapport)
    evaluer_themes(avis_analyses)
    if arguments.comprehend:
        evaluer_sentiments(avis_analyses)
    else:
        print()
        print(
            f"{GRIS}Mode hors ligne : les sentiments proviennent de l'annotation "
            f"manuelle.\nRelancez avec --comprehend pour mesurer la concordance "
            f"réelle du modèle.{FIN}"
        )


if __name__ == "__main__":
    main()
