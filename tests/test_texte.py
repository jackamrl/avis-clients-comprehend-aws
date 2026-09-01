from nordichome import texte


def test_les_accents_sont_neutralises():
    assert texte.normaliser("Délai dépassé") == "delai depasse"


def test_l_apostrophe_devient_une_espace_quelle_que_soit_sa_forme():
    # Sans cela, un motif du lexique comme « musique d attente » ne pourrait
    # jamais correspondre au texte réel « musique d'attente ».
    assert texte.normaliser("l’accueil") == "l accueil"
    assert texte.normaliser("l'accueil") == "l accueil"
    assert texte.normaliser("musique d'attente") == "musique d attente"


def test_le_trait_d_union_est_conserve():
    assert texte.normaliser("service après-vente") == "service apres-vente"


def test_les_determinants_de_tete_disparaissent():
    # Sans ce traitement, « le colis » et « les colis » seraient comptés
    # comme deux thèmes distincts lors de l'agrégation.
    assert texte.nettoyer_phrase_cle("le colis") == "colis"
    assert texte.nettoyer_phrase_cle("Les colis") == "colis"
    assert texte.nettoyer_phrase_cle("un très beau meuble") == "tres beau meuble"


def test_le_vocabulaire_generique_est_ecarte():
    assert texte.nettoyer_phrase_cle("la commande") is None
    assert texte.nettoyer_phrase_cle("le produit") is None


def test_les_phrases_trop_courtes_ou_trop_longues_sont_ecartees():
    assert texte.nettoyer_phrase_cle("le") is None
    assert texte.nettoyer_phrase_cle("42") is None
    assert texte.nettoyer_phrase_cle("un délai de livraison vraiment très long") is None
