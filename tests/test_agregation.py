from datetime import date

import pytest

from nordichome import agregation


def avis(avis_id, jour, sentiment, texte, score=0.9):
    return {
        "avis_id": avis_id,
        "date": jour,
        "sentiment": sentiment,
        "texte": texte,
        "score_confiance": score,
        "mots_cles": [],
    }


# --------------------------------------------------------------------------- #
# Fenêtre temporelle
# --------------------------------------------------------------------------- #

def test_la_fenetre_par_defaut_couvre_sept_jours_pleins():
    debut, fin = agregation.calculer_fenetre({"date_fin": "2026-08-23"})
    assert (debut, fin) == (date(2026, 8, 17), date(2026, 8, 23))


def test_l_identifiant_de_semaine_suit_la_norme_iso():
    assert agregation.identifiant_semaine(date(2026, 8, 17)) == "2026-W34"
    assert agregation.identifiant_semaine(date(2026, 8, 23)) == "2026-W34"


def test_une_semaine_a_cheval_sur_deux_mois_interroge_deux_partitions():
    # Cas piège : sans ce découpage, les avis de fin août seraient perdus.
    seaux = agregation.seaux_mensuels(date(2026, 8, 30), date(2026, 9, 5))
    assert seaux == ["2026-08", "2026-09"]


def test_une_semaine_dans_un_seul_mois_n_interroge_qu_une_partition():
    assert agregation.seaux_mensuels(date(2026, 8, 17), date(2026, 8, 23)) == ["2026-08"]


# --------------------------------------------------------------------------- #
# Calcul du rapport
# --------------------------------------------------------------------------- #

def test_un_rapport_sans_avis_ne_plante_pas():
    rapport = agregation.agreger([], date(2026, 8, 17), date(2026, 8, 23))
    assert rapport["nb_avis"] == 0
    assert rapport["pct_positif"] == 0
    assert rapport["tendance"] == "indeterminee"
    assert rapport["top_negatifs"] == []


def test_les_pourcentages_reprennent_la_repartition_des_sentiments():
    donnees = [
        avis("A1", "2026-08-17", "POSITIVE", "Très bonne qualité."),
        avis("A2", "2026-08-17", "POSITIVE", "Accueil impeccable en boutique."),
        avis("A3", "2026-08-18", "NEGATIVE", "Livraison en retard."),
        avis("A4", "2026-08-18", "NEUTRAL", "Rien à signaler."),
    ]
    rapport = agregation.agreger(donnees, date(2026, 8, 17), date(2026, 8, 23))

    assert rapport["nb_avis"] == 4
    assert rapport["pct_positif"] == 50
    assert rapport["pct_negatif"] == 25
    assert rapport["pct_neutre"] == 25


@pytest.mark.parametrize(
    ("nb_positifs", "nb_negatifs", "attendu"),
    [(8, 2, "positive"), (2, 8, "negative"), (5, 5, "mitigee")],
)
def test_la_tendance_traduit_l_ecart_entre_positifs_et_negatifs(
    nb_positifs, nb_negatifs, attendu
):
    donnees = [
        avis(f"P{i}", "2026-08-17", "POSITIVE", "Belle qualité.") for i in range(nb_positifs)
    ] + [
        avis(f"N{i}", "2026-08-18", "NEGATIVE", "Livraison en retard.")
        for i in range(nb_negatifs)
    ]
    rapport = agregation.agreger(donnees, date(2026, 8, 17), date(2026, 8, 23))
    assert rapport["tendance"] == attendu


def test_les_themes_sont_classes_selon_le_sentiment_detecte_et_non_leur_polarite():
    """Un thème « positif » cité dans un avis négatif doit remonter côté négatif.

    C'est volontaire : la polarité déclarée dans le lexique ne sert qu'à
    l'affichage. Seul le sentiment renvoyé par Comprehend fait autorité.
    """
    donnees = [
        avis("A1", "2026-08-17", "NEGATIVE", "La qualité du produit est déplorable."),
    ]
    rapport = agregation.agreger(donnees, date(2026, 8, 17), date(2026, 8, 23))

    themes_negatifs = {e["theme"] for e in rapport["top_negatifs"]}
    assert "qualite_produit" in themes_negatifs
    assert rapport["top_positifs"] == []


def test_les_avis_neutres_comptent_dans_le_volume_mais_pas_dans_les_palmares():
    donnees = [avis("A1", "2026-08-17", "NEUTRAL", "Livraison en retard mais bon produit.")]
    rapport = agregation.agreger(donnees, date(2026, 8, 17), date(2026, 8, 23))

    assert rapport["nb_avis"] == 1
    assert rapport["top_negatifs"] == []
    assert rapport["top_positifs"] == []


def test_chaque_theme_est_illustre_par_un_extrait_d_avis():
    donnees = [avis("A1", "2026-08-17", "NEGATIVE", "Colis totalement endommagé à l'arrivée.")]
    rapport = agregation.agreger(donnees, date(2026, 8, 17), date(2026, 8, 23))

    exemples = rapport["top_negatifs"][0]["exemples"]
    assert exemples[0]["avis_id"] == "A1"
    assert "endommagé" in exemples[0]["extrait"]


def test_le_volume_quotidien_est_ordonne_chronologiquement():
    donnees = [
        avis("A1", "2026-08-19", "POSITIVE", "Bien."),
        avis("A2", "2026-08-17", "POSITIVE", "Bien."),
        avis("A3", "2026-08-17", "NEGATIVE", "Retard."),
    ]
    rapport = agregation.agreger(donnees, date(2026, 8, 17), date(2026, 8, 23))

    assert rapport["volume_par_jour"] == [
        {"date": "2026-08-17", "nb_avis": 2},
        {"date": "2026-08-19", "nb_avis": 1},
    ]


# --------------------------------------------------------------------------- #
# Bout en bout sur le jeu de données du projet
# --------------------------------------------------------------------------- #

def test_le_jeu_de_donnees_fait_bien_ressortir_les_themes_injectes(jeu_de_donnees):
    donnees = [
        {**item, "sentiment": item["sentiment_attendu"], "score_confiance": 0.95, "mots_cles": []}
        for item in jeu_de_donnees["avis"]
    ]
    rapport = agregation.agreger(donnees, date(2026, 8, 17), date(2026, 8, 23))

    assert rapport["nb_avis"] == 28
    assert rapport["semaine_id"] == "2026-W34"

    negatifs = [e["theme"] for e in rapport["top_negatifs"]]
    positifs = [e["theme"] for e in rapport["top_positifs"]]

    assert {"retard_livraison", "colis_endommage", "sav_injoignable"} <= set(negatifs)
    assert {"accueil_boutique", "reactivite_service_client", "qualite_produit"} <= set(positifs)
    # Le motif dominant de la semaine doit être la logistique.
    assert negatifs[0] == "retard_livraison"
