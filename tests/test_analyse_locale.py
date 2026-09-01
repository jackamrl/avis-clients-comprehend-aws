from nordichome import analyse_locale


def test_un_avis_de_retard_est_classe_negatif():
    resultat = analyse_locale.analyser_localement(
        "Livraison en retard de trois semaines, c'est inadmissible."
    )
    assert resultat["sentiment"] == "NEGATIVE"
    assert resultat["moteur"] == "local"


def test_un_avis_d_accueil_est_classe_positif():
    resultat = analyse_locale.analyser_localement(
        "Excellent accueil en boutique, la conseillère était superbe."
    )
    assert resultat["sentiment"] == "POSITIVE"
