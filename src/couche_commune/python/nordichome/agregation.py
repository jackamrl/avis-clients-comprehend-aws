"""Logique d'agrégation hebdomadaire, sans dépendance à AWS.

Le calcul est isolé des appels DynamoDB / SES pour deux raisons : il devient
testable hors ligne (voir `tests/` et `scripts/simulation_locale.py`), et la
Lambda se réduit à de l'entrée-sortie, ce qui la rend beaucoup plus simple à
relire.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from . import texte as util_texte
from . import themes as lexique

NB_THEMES_AFFICHES = 5
NB_EXEMPLES_PAR_THEME = 2
LONGUEUR_EXTRAIT = 180

# Écart en points de pourcentage entre avis positifs et négatifs au-delà duquel
# la tendance de la semaine est jugée franche plutôt que mitigée.
SEUIL_TENDANCE = 15.0


# --------------------------------------------------------------------------- #
# Fenêtre temporelle
# --------------------------------------------------------------------------- #

def aujourdhui_local(fuseau: str) -> date:
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo(fuseau)).date()
    except Exception:  # base tzdata absente : le repli UTC reste acceptable
        return datetime.now(timezone.utc).date()


def calculer_fenetre(evenement: dict, fuseau: str = "Europe/Paris") -> tuple[date, date]:
    """Détermine la période analysée.

    Par défaut la fenêtre s'arrête la veille de l'exécution : lancé le lundi
    matin, le rapport couvre exactement le lundi au dimanche écoulés.
    """
    nb_jours = int(evenement.get("jours", 7))

    if evenement.get("date_fin"):
        fin = date.fromisoformat(evenement["date_fin"])
    else:
        fin = aujourdhui_local(fuseau) - timedelta(days=1)

    return fin - timedelta(days=nb_jours - 1), fin


def identifiant_semaine(jour: date) -> str:
    annee_iso, semaine_iso, _ = jour.isocalendar()
    return f"{annee_iso}-W{semaine_iso:02d}"


def seaux_mensuels(debut: date, fin: date) -> list[str]:
    """Partitions « AAAA-MM » couvrant la fenêtre (une, parfois deux)."""
    seaux: list[str] = []
    curseur = debut.replace(day=1)
    while curseur <= fin:
        seaux.append(curseur.strftime("%Y-%m"))
        curseur = (curseur.replace(day=28) + timedelta(days=4)).replace(day=1)
    return seaux


# --------------------------------------------------------------------------- #
# Agrégation
# --------------------------------------------------------------------------- #

def pourcentage(nombre: int, total: int) -> Decimal:
    if total == 0:
        return Decimal("0.0")
    return Decimal(str(round(100 * nombre / total, 1)))


def extrait(texte_avis: str) -> str:
    texte_avis = " ".join(texte_avis.split())
    if len(texte_avis) <= LONGUEUR_EXTRAIT:
        return texte_avis
    return texte_avis[:LONGUEUR_EXTRAIT].rsplit(" ", 1)[0] + "…"


def _classer(compteur: Counter, exemples: dict, total_categorie: int) -> list[dict]:
    return [
        {
            "theme": identifiant,
            "libelle": lexique.libelle(identifiant),
            "occurrences": occurrences,
            "part": pourcentage(occurrences, total_categorie),
            "exemples": exemples[identifiant][:NB_EXEMPLES_PAR_THEME],
        }
        for identifiant, occurrences in compteur.most_common(NB_THEMES_AFFICHES)
    ]


def agreger(avis: list[dict], debut: date, fin: date) -> dict:
    """Transforme une liste d'avis analysés en rapport hebdomadaire.

    Chaque élément attendu comporte au minimum : avis_id, date, texte,
    sentiment, score_confiance, mots_cles.
    """
    total = len(avis)
    compteur_sentiments = Counter(item.get("sentiment", "NEUTRAL") for item in avis)

    themes_positifs: Counter = Counter()
    themes_negatifs: Counter = Counter()
    exemples_positifs: dict[str, list[dict]] = defaultdict(list)
    exemples_negatifs: dict[str, list[dict]] = defaultdict(list)
    mots_positifs: Counter = Counter()
    mots_negatifs: Counter = Counter()
    volume_par_jour: Counter = Counter()
    somme_confiance = 0.0

    for item in avis:
        sentiment = item.get("sentiment", "NEUTRAL")
        volume_par_jour[item["date"]] += 1
        somme_confiance += float(item.get("score_confiance", 0))

        mots_cles = [str(m) for m in item.get("mots_cles", [])]
        # Les thèmes sont recalculés ici, et non figés à l'ingestion : faire
        # évoluer le lexique métier ne demande alors aucun retraitement des avis.
        detectes = lexique.detecter(item.get("texte", ""), mots_cles)

        # Le classement s'appuie sur le sentiment réellement détecté par
        # Comprehend. Les avis NEUTRAL et MIXED comptent dans le volume mais
        # n'alimentent aucun des deux palmarès, faute de polarité tranchée.
        if sentiment == "POSITIVE":
            cible_themes, cible_exemples, cible_mots = (
                themes_positifs, exemples_positifs, mots_positifs,
            )
        elif sentiment == "NEGATIVE":
            cible_themes, cible_exemples, cible_mots = (
                themes_negatifs, exemples_negatifs, mots_negatifs,
            )
        else:
            continue

        for identifiant in detectes:
            cible_themes[identifiant] += 1
            if len(cible_exemples[identifiant]) < NB_EXEMPLES_PAR_THEME:
                cible_exemples[identifiant].append(
                    {"avis_id": item["avis_id"], "extrait": extrait(item.get("texte", ""))}
                )

        for mot in mots_cles:
            terme = util_texte.nettoyer_phrase_cle(mot)
            if terme:
                cible_mots[terme] += 1

    nb_positif = compteur_sentiments.get("POSITIVE", 0)
    nb_negatif = compteur_sentiments.get("NEGATIVE", 0)
    nb_neutre = compteur_sentiments.get("NEUTRAL", 0)
    nb_mixte = compteur_sentiments.get("MIXED", 0)

    pct_positif = pourcentage(nb_positif, total)
    pct_negatif = pourcentage(nb_negatif, total)
    ecart = float(pct_positif) - float(pct_negatif)

    if total == 0:
        tendance = "indeterminee"
    elif ecart >= SEUIL_TENDANCE:
        tendance = "positive"
    elif ecart <= -SEUIL_TENDANCE:
        tendance = "negative"
    else:
        tendance = "mitigee"

    return {
        "semaine_id": identifiant_semaine(debut),
        "periode_debut": debut.isoformat(),
        "periode_fin": fin.isoformat(),
        "nb_avis": total,
        "nb_positif": nb_positif,
        "nb_negatif": nb_negatif,
        "nb_neutre": nb_neutre,
        "nb_mixte": nb_mixte,
        "pct_positif": pct_positif,
        "pct_negatif": pct_negatif,
        "pct_neutre": pourcentage(nb_neutre, total),
        "pct_mixte": pourcentage(nb_mixte, total),
        "score_confiance_moyen": (
            Decimal(str(round(somme_confiance / total, 4))) if total else Decimal("0")
        ),
        "tendance": tendance,
        "top_positifs": _classer(themes_positifs, exemples_positifs, nb_positif),
        "top_negatifs": _classer(themes_negatifs, exemples_negatifs, nb_negatif),
        "mots_cles_positifs": [
            {"terme": terme, "occurrences": n} for terme, n in mots_positifs.most_common(10)
        ],
        "mots_cles_negatifs": [
            {"terme": terme, "occurrences": n} for terme, n in mots_negatifs.most_common(10)
        ],
        "volume_par_jour": [
            {"date": jour, "nb_avis": n} for jour, n in sorted(volume_par_jour.items())
        ],
    }
