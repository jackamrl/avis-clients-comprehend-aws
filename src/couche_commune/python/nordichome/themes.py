"""Lexique métier : regroupement des avis en thèmes récurrents.

Pourquoi un lexique et pas uniquement les phrases clés de Comprehend ?
`detect_key_phrases` extrait « le colis », « la porte cassée », « une charnière
arrachée » : trois formulations d'un même problème métier. Un classement brut
des phrases clés produirait une longue liste plate, illisible pour un manager.
Le lexique projette ces formulations sur un petit nombre de thèmes stables et
comparables d'une semaine à l'autre, ce qui est la condition pour suivre une
tendance.

Les motifs sont évalués sur du texte normalisé (minuscules, sans accents) :
voir `nordichome.texte.normaliser`.
"""

from __future__ import annotations

import re
from typing import Iterable

from . import texte as util_texte

# polarite = polarité *attendue* du thème. Elle sert uniquement à l'affichage.
# Le classement positif/négatif d'un rapport s'appuie sur le sentiment réellement
# détecté par Comprehend, jamais sur cette valeur : un thème « qualité produit »
# apparaissant dans un avis négatif est une information, pas une erreur.
LEXIQUE: dict[str, dict] = {
    "retard_livraison": {
        "libelle": "Retards de livraison",
        "polarite": "negatif",
        "motifs": [
            r"\bretard",
            r"\bdelai",
            r"repouss",
            r"toujours rien recu",
            r"pas (encore )?recu",
            r"jamais recu",
            r"(mois|semaines?|jours?) d attente",
            r"livraison .{0,24}(longue|lente|interminable)",
            r"expedi\w* depuis",
            r"n avait (meme )?pas quitte l entrepot",
        ],
    },
    "colis_endommage": {
        "libelle": "Colis et produits endommagés",
        "polarite": "negatif",
        "motifs": [
            r"endommag",
            r"\babim",
            r"\bcass(e|ee|es|ees)\b",
            r"\bbris(e|ee|es|ees)\b",
            r"\bray(e|ee|es|ees)\b",
            r"fendu",
            r"eventr",
            r"detremp",
            r"arrach",
            r"emballage",
            r"carton \w+ (enfonce|troue|eventre)",
            r"choc pendant le transport",
            r"protection en mousse",
        ],
    },
    "sav_injoignable": {
        "libelle": "Service après-vente difficile à joindre",
        "polarite": "negatif",
        "motifs": [
            r"injoignable",
            r"impossible de joindre",
            r"(sans|aucune) reponse",
            r"ne rappelle",
            r"musique d attente",
            r"telephone satur",
            r"sonne dans le vide",
            r"relances? restent",
            r"sans accuse de reception",
            r"chat en ligne indisponible",
            r"(suivi )?apres-vente est (catastrophique|inexistant)",
            r"abandonne apres l achat",
            r"la ligne qui coupe",
        ],
    },
    "reactivite_service_client": {
        "libelle": "Réactivité du service client",
        "polarite": "positif",
        "motifs": [
            r"reactiv",
            r"reactif",
            r"repondu en moins de",
            r"pris? en charge",
            r"echange sans discuter",
            r"a corrige",
            r"le jour meme",
            r"surlendemain",
            r"tres professionnel",
            r"suivi par mail est clair",
            r"remplace",
            r"sans frais",
        ],
    },
    "accueil_boutique": {
        "libelle": "Accueil en boutique",
        "polarite": "positif",
        "motifs": [
            r"boutique",
            r"magasin",
            r"showroom",
            r"accueil",
            r"conseill(er|ere|eres|ers)\b",
            r"vendeu(r|se)",
            r"sans (aucune )?pression commerciale",
            r"en rayon",
        ],
    },
    "qualite_produit": {
        "libelle": "Qualité des produits",
        "polarite": "positif",
        "motifs": [
            r"qualite",
            r"finition",
            r"materiaux",
            r"\bsolide",
            r"robuste",
            r"bois massif",
            r"belle facture",
            r"assemblages",
            r"bien ajust",
            r"conforme",
            r"aucun signe d usure",
            r"confortable",
        ],
    },
}

_MOTIFS_COMPILES = {
    identifiant: [re.compile(motif) for motif in definition["motifs"]]
    for identifiant, definition in LEXIQUE.items()
}


def libelle(identifiant: str) -> str:
    return LEXIQUE.get(identifiant, {}).get("libelle", identifiant)


def polarite(identifiant: str) -> str:
    return LEXIQUE.get(identifiant, {}).get("polarite", "neutre")


def detecter(texte_avis: str, mots_cles: Iterable[str] = ()) -> list[str]:
    """Renvoie les identifiants de thèmes présents dans un avis.

    L'analyse porte sur le texte complet *et* sur les phrases clés extraites
    par Comprehend, concaténés : les phrases clés renforcent la détection quand
    le thème est exprimé dans un groupe nominal isolé.
    """
    corpus = util_texte.normaliser(texte_avis)
    supplement = " ".join(util_texte.normaliser(m) for m in mots_cles)
    if supplement:
        corpus = f"{corpus} {supplement}"

    return [
        identifiant
        for identifiant, motifs in _MOTIFS_COMPILES.items()
        if any(motif.search(corpus) for motif in motifs)
    ]
