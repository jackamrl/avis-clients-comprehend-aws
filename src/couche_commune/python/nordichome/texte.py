"""Normalisation du texte français.

Amazon Comprehend renvoie des phrases clés brutes telles qu'elles apparaissent
dans l'avis (« le colis », « La livraison », « les délais de livraison »).
Sans nettoyage, l'agrégation hebdomadaire compterait ces variantes comme des
thèmes distincts. Ce module ramène tout à une forme canonique.
"""

from __future__ import annotations

import re
import unicodedata

# Déterminants et prépositions à retirer en tête de phrase clé.
PREFIXES_A_RETIRER = (
    "le", "la", "les", "l", "un", "une", "des", "du", "de", "d",
    "ce", "cet", "cette", "ces", "mon", "ma", "mes", "notre", "nos",
    "votre", "vos", "leur", "leurs", "son", "sa", "ses", "au", "aux",
    "tout", "toute", "tous", "toutes", "quelques", "plusieurs", "certains",
    "chaque", "aucun", "aucune", "beaucoup",
)

# Phrases clés sans valeur métier : bruit fréquent dans les avis.
TERMES_IGNORES = frozenset(
    {
        "chose", "choses", "fois", "moment", "temps", "jour", "jours",
        "semaine", "semaines", "mois", "an", "ans", "annee", "annees",
        "heure", "heures", "minute", "minutes", "euros", "euro",
        "coup", "cas", "peu", "point", "type", "sorte", "facon", "maniere",
        "personne", "personnes", "gens", "monde", "avis", "commentaire",
        "nordichome", "site", "commande", "commandes", "achat", "achats",
        "produit", "produits", "article", "articles",
    }
)

# L'apostrophe devient une espace : « l'accueil » -> « l accueil », ce qui
# permet de retirer l'élision comme un déterminant ordinaire et rend les motifs
# du lexique lisibles (« musique d attente » plutôt que deux variantes typographiques).
# Le trait d'union est conservé : « après-vente », « qualité-prix » sont des unités.
_PONCTUATION = re.compile(r"[^\w\s-]", flags=re.UNICODE)
_ESPACES = re.compile(r"\s+")


def sans_accents(valeur: str) -> str:
    """« délai » -> « delai ». Rend les comparaisons insensibles aux accents."""
    decompose = unicodedata.normalize("NFD", valeur)
    return "".join(c for c in decompose if unicodedata.category(c) != "Mn")


def normaliser(valeur: str) -> str:
    """Forme canonique utilisée pour toutes les comparaisons lexicales."""
    valeur = sans_accents(valeur.lower())
    valeur = _PONCTUATION.sub(" ", valeur)
    return _ESPACES.sub(" ", valeur).strip()


def nettoyer_phrase_cle(phrase: str) -> str | None:
    """Ramène une phrase clé Comprehend à un terme comparable.

    Renvoie ``None`` quand la phrase ne porte aucune information exploitable
    (trop courte, purement numérique, ou terme générique du vocabulaire e-commerce).
    """
    terme = normaliser(phrase)

    # « l'accueil » est devenu « l accueil » : l'élision se retire comme
    # n'importe quel déterminant. On boucle car « tous les colis » en enchaîne deux.
    mots = terme.split()
    while mots and mots[0] in PREFIXES_A_RETIRER:
        mots.pop(0)
    terme = " ".join(mots)

    if len(terme) < 4 or terme.isdigit():
        return None
    if terme in TERMES_IGNORES:
        return None
    # On borne la longueur : au-delà, la phrase clé est une proposition entière
    # qui ne se répétera jamais à l'identique et pollue le classement.
    if len(mots) > 4:
        return None
    return terme
