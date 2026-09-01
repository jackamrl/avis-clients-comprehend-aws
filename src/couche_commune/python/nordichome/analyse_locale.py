"""Repli d'analyse quand Amazon Comprehend n'est pas encore souscrit.

Un compte AWS tout neuf renvoie souvent `SubscriptionRequiredException` sur
Comprehend pendant quelques heures. Ce module produit une sortie de même forme
(`sentiment`, scores, phrases clés) pour ne pas bloquer la démonstration.

Dès que Comprehend répond, la Lambda l'utilise à nouveau : ce n'est pas un
remplacement du service managé, c'est une continuité de service.
"""

from __future__ import annotations

import re

from . import texte as util_texte
from . import themes as lexique

POSITIFS = (
    "impeccable", "excellent", "excellente", "superbe", "bravo", "content",
    "contente", "heureux", "heureuse", "merci", "professionnel", "professionnelle",
    "reactif", "reactive", "reactivite", "qualite", "solide", "robuste",
    "confortable", "chaleureux", "chaleureuse", "parfait", "parfaite",
    "irréprochable", "irreprochable", "exemplaire", "appreciable", "appreciable",
    "bien", "bonne", "bon", "top", "recommande", "recommanderai",
)

NEGATIFS = (
    "inadmissible", "catastrophique", "frustrant", "impossible", "injoignable",
    "retard", "retards", "abime", "abimee", "casse", "cassee", "brise", "brisee",
    "raye", "rayee", "endommag", "detremp", "eventr", "abandonne", "nul",
    "horrible", "decevant", "decevante", "mauvais", "mauvaise", "probleme",
    "plainte", "jamais", "rien recu", "sans reponse", "longue",
)


def _presence(normalise: str, termes: tuple[str, ...]) -> int:
    return sum(1 for terme in termes if re.search(rf"\b{re.escape(terme)}", normalise))


def analyser_localement(contenu: str) -> dict:
    """Renvoie un dict compatible avec la sortie formatée de Comprehend."""
    normalise = util_texte.normaliser(contenu)
    themes = lexique.detecter(contenu)

    n_pos = _presence(normalise, POSITIFS)
    n_neg = _presence(normalise, NEGATIFS)
    n_pos += sum(1 for t in themes if lexique.polarite(t) == "positif")
    n_neg += sum(1 for t in themes if lexique.polarite(t) == "negatif")

    if n_pos > 0 and n_neg > 0:
        etiquette = "MIXED"
        scores = {"Positive": 0.35, "Negative": 0.35, "Neutral": 0.10, "Mixed": 0.80}
    elif n_neg > n_pos and n_neg >= 1:
        etiquette = "NEGATIVE"
        scores = {"Positive": 0.05, "Negative": 0.85, "Neutral": 0.07, "Mixed": 0.03}
    elif n_pos > n_neg and n_pos >= 1:
        etiquette = "POSITIVE"
        scores = {"Positive": 0.85, "Negative": 0.05, "Neutral": 0.07, "Mixed": 0.03}
    else:
        etiquette = "NEUTRAL"
        scores = {"Positive": 0.10, "Negative": 0.10, "Neutral": 0.75, "Mixed": 0.05}

    mots_cles: list[str] = []
    for identifiant in themes:
        libelle = util_texte.nettoyer_phrase_cle(lexique.libelle(identifiant))
        if libelle and libelle not in mots_cles:
            mots_cles.append(libelle)

    for mot in normalise.split():
        terme = util_texte.nettoyer_phrase_cle(mot)
        if terme and terme not in mots_cles:
            mots_cles.append(terme)
        if len(mots_cles) >= 12:
            break

    return {
        "sentiment": etiquette,
        "score_confiance": scores[etiquette.capitalize()],
        "scores": scores,
        "mots_cles": mots_cles,
        "moteur": "local",
    }
