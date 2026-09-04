"""Génère ~100 avis synthétiques pour une semaine ISO (défaut : 2026-W33).

Les 28 avis de démonstration (semaine 34) ne sont pas touchés. Les fichiers
sont écrits dans data/incoming_w33/ pour un dépôt S3 séparé :

    aws s3 cp data/incoming_w33/ s3://nordichome-avis-<compte>/incoming/ --recursive --region eu-west-1

Puis, pour produire le rapport de cette semaine :

    .\\scripts\\lancer-rapport.ps1 -DateFin 2026-08-16
"""

from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "src" / "couche_commune" / "python"))

from nordichome import fichiers  # noqa: E402

# Lundi 10 → dimanche 16 août 2026 = semaine ISO 2026-W33
DEBUT = date(2026, 8, 10)
FIN = date(2026, 8, 16)
NB_CIBLE = 105  # 15 avis par jour × 7

DOSSIER = RACINE / "data" / "incoming_w33"
JSON_SORTIE = RACINE / "data" / "avis_semaine_33.json"

VILLES = [
    "Lille", "Lyon", "Nantes", "Bordeaux", "Toulouse", "Rennes", "Strasbourg",
    "Rouen", "Dijon", "Angers",
]
PRODUITS = [
    "canapé", "table basse", "buffet", "étagère", "lit", "commode", "fauteuil",
    "tapis", "miroir", "meuble TV", "chaise", "console",
]


def _date(offset_jour: int) -> str:
    return (DEBUT + timedelta(days=offset_jour)).isoformat()


def corpus() -> list[dict]:
    """105 avis : 15 par jour, polarités et thèmes volontairement déséquilibrés.

    Semaine un peu plus positive que la W34, pour que la comparaison
    semaine à semaine ait une histoire à raconter.
    """
    avis: list[dict] = []
    n = 101  # AV101 … pour ne pas collisionner avec AV001–AV028

    def add(jour, texte, sentiment, themes, client):
        nonlocal n
        avis.append(
            {
                "avis_id": f"AV{n:03d}",
                "date": _date(jour),
                "client_id": f"CLI-{client}",
                "texte": texte,
                "sentiment_attendu": sentiment,
                "themes_attendus": themes,
            }
        )
        n += 1

    # 7 jours × 15 avis. Motifs par jour pour varier sans tout dupliquer.
    for j in range(7):
        ville = VILLES[j]
        ville2 = VILLES[(j + 3) % len(VILLES)]
        p1, p2, p3 = PRODUITS[j], PRODUITS[j + 3], PRODUITS[(j + 6) % 12]
        d = 10 + j  # jour du mois, pour les formulations datées

        # --- 6 positifs ---
        add(j,
            f"Passage en boutique à {ville} : l'accueil a été chaleureux et sans pression commerciale. "
            f"La conseillère m'a aidée à choisir un {p1} adapté à notre salon. Très bonne expérience.",
            "POSITIVE", ["accueil_boutique"], 4000 + j)
        add(j,
            f"Le {p2} est de très belle qualité, les finitions sont soignées et le bois massif est robuste. "
            f"Conforme aux photos, je suis vraiment content de cet achat.",
            "POSITIVE", ["qualite_produit"], 4010 + j)
        add(j,
            f"Pièce manquante signalée le matin, le service client a répondu en moins d'une heure et a "
            f"envoyé le remplacement le jour même. Réactivité exemplaire.",
            "POSITIVE", ["reactivite_service_client"], 4020 + j)
        add(j,
            f"Excellent accueil dans le showroom de {ville2}. On nous a laissé le temps, le vendeur "
            f"connaissait bien les collections. Le {p3} commandé est solide et bien ajusté.",
            "POSITIVE", ["accueil_boutique", "qualite_produit"], 4030 + j)
        add(j,
            f"Erreur de référence de ma part. Le service client a corrigé en quelques minutes par téléphone "
            f"et a pris les frais de retour. Très professionnel et réactif.",
            "POSITIVE", ["reactivite_service_client"], 4040 + j)
        add(j,
            f"Le fauteuil est confortable, aucun signe d'usure après plusieurs semaines. La qualité des "
            f"matériaux est vraiment au rendez-vous, assemblages nickel.",
            "POSITIVE", ["qualite_produit"], 4050 + j)

        # --- 5 négatifs ---
        add(j,
            f"Commande du {d} juillet, livraison annoncée sous cinq jours. Toujours rien reçu à ce jour. "
            f"Le suivi n'indique rien d'exploitable. Inadmissible.",
            "NEGATIVE", ["retard_livraison"], 4100 + j)
        add(j,
            f"Le {p1} est arrivé avec le carton éventré et un coin cassé. L'emballage n'avait aucune "
            f"protection en mousse, clairement insuffisant pour le transport.",
            "NEGATIVE", ["colis_endommage"], 4110 + j)
        add(j,
            f"Impossible de joindre le service après-vente. Six appels, musique d'attente puis la ligne "
            f"qui coupe. Deux mails sans aucune réponse. On se sent abandonné après l'achat.",
            "NEGATIVE", ["sav_injoignable"], 4120 + j)
        add(j,
            f"Livraison repoussée trois fois. J'ai posé une journée de congé pour rien. Communication "
            f"inexistante sur ce retard, le transporteur et NordicHome se renvoient la balle.",
            "NEGATIVE", ["retard_livraison"], 4130 + j)
        add(j,
            f"Colis détrempé, {p2} rayé sur le dessus. En plus le délai annoncé n'a pas été tenu. "
            f"Double peine entre le retard et l'état du produit à l'arrivée.",
            "NEGATIVE", ["colis_endommage", "retard_livraison"], 4140 + j)

        # --- 2 neutres ---
        add(j,
            f"Commande conforme, {p3} reçu. Le montage a pris un peu de temps en suivant la notice. "
            f"Rien de particulier à signaler pour le moment.",
            "NEUTRAL", [], 4200 + j)
        add(j,
            f"Le produit correspond à la description du site. La couleur est légèrement plus claire "
            f"que sur l'écran, cela reste acceptable. Prix dans la moyenne.",
            "NEUTRAL", [], 4210 + j)

        # --- 2 mitigés ---
        add(j,
            f"La qualité du {p1} est bonne mais la livraison a été vraiment longue. Bilan mitigé, "
            f"je recommanderai en anticipant davantage la commande.",
            "MIXED", ["qualite_produit", "retard_livraison"], 4300 + j)
        add(j,
            f"Accueil correct en magasin à {ville}, en revanche le SAV a été difficile à joindre "
            f"quand j'ai eu une question après l'achat. Expérience inégale.",
            "MIXED", ["accueil_boutique", "sav_injoignable"], 4310 + j)

    return avis


def main() -> None:
    avis = corpus()
    assert len(avis) == NB_CIBLE, len(avis)

    jeu = {
        "entreprise": "NordicHome",
        "periode": {
            "debut": DEBUT.isoformat(),
            "fin": FIN.isoformat(),
            "semaine_iso": "2026-W33",
        },
        "commentaire": (
            "Avis synthétiques semaine 33. À déposer dans incoming/ du bucket S3. "
            "Ne pas confondre avec les 28 avis de la semaine 34 (data/incoming/)."
        ),
        "avis": avis,
    }
    JSON_SORTIE.write_text(json.dumps(jeu, ensure_ascii=False, indent=2), encoding="utf-8")

    DOSSIER.mkdir(parents=True, exist_ok=True)
    for ancien in DOSSIER.glob("*.txt"):
        ancien.unlink()

    for item in avis:
        nom = fichiers.nom_fichier(item["avis_id"], item["date"], item["client_id"])
        (DOSSIER / nom).write_text(item["texte"], encoding="utf-8")

    repartition: dict[str, int] = {}
    for item in avis:
        repartition[item["sentiment_attendu"]] = repartition.get(item["sentiment_attendu"], 0) + 1

    print(f"{len(avis)} fichiers dans {DOSSIER}")
    print(f"JSON : {JSON_SORTIE}")
    print("Répartition annotée :")
    for sentiment, nombre in sorted(repartition.items()):
        print(f"  {sentiment:<9} {nombre:>3}  ({nombre / len(avis):.0%})")
    print()
    print("Dépôt S3 :")
    print("  aws s3 cp data/incoming_w33/ s3://nordichome-avis-599915810057/incoming/ --recursive --region eu-west-1")
    print("Rapport :")
    print("  .\\scripts\\lancer-rapport.ps1 -DateFin 2026-08-16")


if __name__ == "__main__":
    main()
