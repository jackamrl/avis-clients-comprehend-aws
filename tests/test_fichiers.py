import pytest

from nordichome import fichiers


def test_une_cle_conforme_est_decoupee_en_metadonnees():
    assert fichiers.lire_metadonnees("incoming/AV001_2026-08-17_CLI-1042.txt") == (
        "AV001",
        "2026-08-17",
        "CLI-1042",
    )


def test_l_ecriture_et_la_lecture_du_nom_sont_reciproques():
    nom = fichiers.nom_fichier("AV028", "2026-08-23", "CLI-2589")
    assert fichiers.lire_metadonnees(nom) == ("AV028", "2026-08-23", "CLI-2589")


@pytest.mark.parametrize(
    "cle",
    [
        "incoming/avis.txt",                       # métadonnées absentes
        "incoming/AV001_17-08-2026_CLI-1.txt",     # date au mauvais format
        "incoming/AV001_2026-13-45_CLI-1.txt",     # date inexistante
        "incoming/AV001_2026-08-17_CLI-1.csv",     # extension inattendue
        "incoming/AV001_2026-08-17.txt",           # client absent
    ],
)
def test_une_cle_non_conforme_est_rejetee(cle):
    with pytest.raises(fichiers.FichierInvalide):
        fichiers.lire_metadonnees(cle)


def test_la_troncature_respecte_la_limite_en_octets():
    # « é » pèse deux octets : la limite Comprehend s'atteint deux fois plus vite
    # sur un texte français que le nombre de caractères ne le laisse penser.
    texte = "é" * 100
    tronque = fichiers.tronquer_utf8(texte, 10)

    assert len(tronque.encode("utf-8")) <= 10
    assert tronque == "é" * 5


def test_la_troncature_ne_coupe_pas_un_caractere_en_deux():
    tronque = fichiers.tronquer_utf8("aé", 2)
    assert tronque == "a"


def test_un_texte_court_reste_intact():
    assert fichiers.tronquer_utf8("bonjour", 4800) == "bonjour"
