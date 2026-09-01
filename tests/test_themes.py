import pytest

from nordichome import themes


@pytest.mark.parametrize(
    ("avis", "attendu"),
    [
        ("Livraison en retard de trois semaines.", "retard_livraison"),
        ("Le miroir est arrivé brisé, aucune protection en mousse.", "colis_endommage"),
        ("Impossible de joindre le service après-vente.", "sav_injoignable"),
        ("Le service client a répondu en moins de deux heures.", "reactivite_service_client"),
        ("Excellent accueil dans votre showroom de Bordeaux.", "accueil_boutique"),
        ("Le bois massif est de belle qualité.", "qualite_produit"),
    ],
)
def test_chaque_theme_du_lexique_est_detectable(avis, attendu):
    assert attendu in themes.detecter(avis)


def test_un_avis_peut_porter_plusieurs_themes():
    avis = "Retard de deux semaines et à l'arrivée le carton était éventré."
    detectes = themes.detecter(avis)
    assert {"retard_livraison", "colis_endommage"} <= set(detectes)


def test_la_detection_ignore_les_accents_et_la_casse():
    assert "retard_livraison" in themes.detecter("RETARD de livraison")
    assert "retard_livraison" in themes.detecter("Delai non tenu")


def test_la_detection_traverse_les_elisions():
    # « d'attente » et « l'achat » doivent atteindre les motifs du lexique.
    assert "retard_livraison" in themes.detecter("Trois semaines d'attente.")
    assert "sav_injoignable" in themes.detecter(
        "Une longue musique d'attente puis plus rien."
    )
    assert "sav_injoignable" in themes.detecter(
        "On se sent abandonné après l'achat."
    )


def test_les_phrases_cles_renforcent_la_detection():
    # Le texte seul ne suffit pas ; la phrase clé issue de Comprehend complète.
    assert themes.detecter("Rien à signaler de particulier.") == []
    assert "accueil_boutique" in themes.detecter(
        "Rien à signaler de particulier.", ["accueil en boutique"]
    )


def test_tous_les_themes_du_jeu_de_donnees_sont_retrouves(jeu_de_donnees):
    """Le rappel sur les thèmes injectés volontairement doit rester total.

    C'est le garde-fou du lexique : toute régression lors d'un ajustement de
    motif est détectée ici plutôt qu'en soutenance.
    """
    manquants = []
    for avis in jeu_de_donnees["avis"]:
        detectes = set(themes.detecter(avis["texte"]))
        for attendu in avis["themes_attendus"]:
            if attendu not in detectes:
                manquants.append((avis["avis_id"], attendu))

    assert manquants == []
