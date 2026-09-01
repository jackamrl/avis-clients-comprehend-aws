"""Convention de nommage des fichiers d'avis déposés sur S3.

    {avis_id}_{AAAA-MM-JJ}_{client_id}.txt      ex. AV001_2026-08-17_CLI-1042.txt

Les métadonnées voyagent dans le nom du fichier plutôt que dans son contenu :
n'importe quel système amont (export CRM, formulaire web, collecte d'avis
marketplace) peut alimenter le pipeline en déposant du texte brut, sans avoir
à produire du JSON structuré.

La convention est définie ici et nulle part ailleurs : le générateur du jeu de
test et la Lambda d'ingestion s'appuient tous deux sur ce module, ce qui rend
impossible une divergence entre écriture et lecture.
"""

from __future__ import annotations

import os
import re
from datetime import datetime

MOTIF = re.compile(
    r"^(?P<avis_id>[A-Za-z0-9-]+)"
    r"_(?P<date>\d{4}-\d{2}-\d{2})"
    r"_(?P<client_id>[A-Za-z0-9-]+)$"
)

FORMAT_ATTENDU = "{avis_id}_{AAAA-MM-JJ}_{client_id}.txt"


class FichierInvalide(Exception):
    """Le fichier déposé ne respecte pas la convention attendue."""


def nom_fichier(avis_id: str, date_avis: str, client_id: str) -> str:
    return f"{avis_id}_{date_avis}_{client_id}.txt"


def lire_metadonnees(cle_s3: str) -> tuple[str, str, str]:
    """Extrait (avis_id, date, client_id) d'une clé S3.

    Lève `FichierInvalide` si la clé ne suit pas la convention : l'erreur est
    définitive, un réessai ne servirait à rien.
    """
    nom = os.path.basename(cle_s3)
    base, extension = os.path.splitext(nom)

    if extension.lower() != ".txt":
        raise FichierInvalide(f"extension non supportée : {nom}")

    correspondance = MOTIF.match(base)
    if not correspondance:
        raise FichierInvalide(f"nom non conforme : {nom} (attendu : {FORMAT_ATTENDU})")

    donnees = correspondance.groupdict()
    try:
        datetime.strptime(donnees["date"], "%Y-%m-%d")
    except ValueError as erreur:
        raise FichierInvalide(f"date invalide dans {nom}") from erreur

    return donnees["avis_id"], donnees["date"], donnees["client_id"]


def tronquer_utf8(valeur: str, limite_octets: int) -> str:
    """Tronque sans casser un caractère multi-octets.

    Les quotas Comprehend s'expriment en octets UTF-8, pas en caractères : un
    texte français accentué atteint la limite plus tôt qu'un texte anglais.
    """
    encode = valeur.encode("utf-8")
    if len(encode) <= limite_octets:
        return valeur
    return encode[:limite_octets].decode("utf-8", errors="ignore")
