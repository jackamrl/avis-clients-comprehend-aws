"""Lambda #1 — traiter-avis.

Déclenchée par l'événement S3 `ObjectCreated` sur le préfixe `incoming/`.
Pour chaque fichier déposé : lecture du texte, appel à Amazon Comprehend
(`detect_sentiment` + `detect_key_phrases`), écriture dans la table DynamoDB
« Avis ».

La convention de nommage des fichiers est décrite dans `nordichome.fichiers`.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.parse
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

from nordichome import analyse_locale, fichiers, texte as util_texte
from nordichome.fichiers import FichierInvalide

logger = logging.getLogger()
logger.setLevel(os.environ.get("NIVEAU_LOG", "INFO"))

s3 = boto3.client("s3")
comprehend = boto3.client("comprehend")
table_avis = boto3.resource("dynamodb").Table(os.environ["TABLE_AVIS"])

LANGUE = os.environ.get("LANGUE", "fr")

# DetectSentiment et DetectKeyPhrases acceptent 5 000 octets UTF-8.
# On reste en dessous pour garder une marge sur les caractères accentués.
LIMITE_OCTETS_COMPREHEND = 4800

# Score minimal pour retenir une phrase clé : en dessous, Comprehend renvoie
# surtout du bruit syntaxique.
SEUIL_PHRASE_CLE = 0.80
NOMBRE_MAX_PHRASES_CLES = 15


def _formater(etiquette: str, scores: dict, mots_cles: list[str], moteur: str) -> dict:
    score_confiance = scores.get(etiquette.capitalize(), 0.0)
    return {
        "sentiment": etiquette,
        "score_confiance": Decimal(str(round(score_confiance, 4))),
        "scores_detail": {
            "positif": Decimal(str(round(scores["Positive"], 4))),
            "negatif": Decimal(str(round(scores["Negative"], 4))),
            "neutre": Decimal(str(round(scores["Neutral"], 4))),
            "mixte": Decimal(str(round(scores["Mixed"], 4))),
        },
        "mots_cles": mots_cles,
        "moteur": moteur,
    }


def analyser(contenu: str) -> dict:
    """Appelle Comprehend ; repli local si le compte n'a pas encore souscrit le service."""
    extrait = fichiers.tronquer_utf8(contenu, LIMITE_OCTETS_COMPREHEND)

    try:
        sentiment = comprehend.detect_sentiment(Text=extrait, LanguageCode=LANGUE)
        phrases = comprehend.detect_key_phrases(Text=extrait, LanguageCode=LANGUE)
    except ClientError as erreur:
        code = erreur.response.get("Error", {}).get("Code", "")
        # Compte AWS neuf : Comprehend n'est pas encore « souscrit ».
        if code in {"SubscriptionRequiredException", "OptInRequired"}:
            logger.warning("Comprehend indisponible (%s) — repli sur l'analyse locale", code)
            local = analyse_locale.analyser_localement(extrait)
            return _formater(
                local["sentiment"], local["scores"], local["mots_cles"], "local"
            )
        raise

    scores = sentiment["SentimentScore"]
    etiquette = sentiment["Sentiment"]

    mots_cles: list[str] = []
    for phrase in sorted(phrases["KeyPhrases"], key=lambda p: -p["Score"]):
        if phrase["Score"] < SEUIL_PHRASE_CLE:
            continue
        terme = util_texte.nettoyer_phrase_cle(phrase["Text"])
        if terme and terme not in mots_cles:
            mots_cles.append(terme)
        if len(mots_cles) >= NOMBRE_MAX_PHRASES_CLES:
            break

    return _formater(etiquette, scores, mots_cles, "comprehend")


def traiter_objet(bucket: str, cle: str) -> dict:
    avis_id, date_avis, client_id = fichiers.lire_metadonnees(cle)

    objet = s3.get_object(Bucket=bucket, Key=cle)
    contenu = objet["Body"].read().decode("utf-8").strip()
    if not contenu:
        raise FichierInvalide(f"fichier vide : {cle}")

    resultat = analyser(contenu)

    element = {
        "avis_id": avis_id,
        "date": date_avis,
        # Clé de partition de l'index secondaire : un seau par mois. Cela évite
        # le Scan intégral lors de l'agrégation hebdomadaire tout en gardant des
        # partitions de taille raisonnable à mesure que l'historique grossit.
        "mois": date_avis[:7],
        "client_id": client_id,
        "texte": contenu,
        "langue": LANGUE,
        "fichier_source": cle,
        "date_traitement": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        **resultat,
    }

    # put_item est idempotent sur avis_id : re-déposer le même fichier écrase
    # proprement l'analyse précédente au lieu de créer un doublon.
    table_avis.put_item(Item=element)

    logger.info(
        "avis %s traité : %s (%.2f)",
        avis_id,
        resultat["sentiment"],
        float(resultat["score_confiance"]),
    )
    return {
        "avis_id": avis_id,
        "sentiment": resultat["sentiment"],
        "score_confiance": float(resultat["score_confiance"]),
        "nb_mots_cles": len(resultat["mots_cles"]),
    }


def lambda_handler(event, context):  # noqa: ARG001 - signature imposée par Lambda
    traites: list[dict] = []
    ignores: list[dict] = []

    for enregistrement in event.get("Records", []):
        bucket = enregistrement["s3"]["bucket"]["name"]
        cle = urllib.parse.unquote_plus(enregistrement["s3"]["object"]["key"])

        try:
            traites.append(traiter_objet(bucket, cle))
        except FichierInvalide as erreur:
            # Erreur définitive : un réessai donnerait le même résultat. On
            # journalise et on continue, sans faire échouer le lot entier.
            logger.warning("fichier ignoré : %s", erreur)
            ignores.append({"cle": cle, "raison": str(erreur)})
        except ClientError:
            # Throttling Comprehend ou indisponibilité DynamoDB : on laisse
            # remonter pour que Lambda réessaie, puis bascule le message en
            # file de lettres mortes si l'incident persiste.
            logger.exception("échec du traitement de %s", cle)
            raise

    resume = {"traites": len(traites), "ignores": len(ignores), "detail": traites}
    logger.info("résumé du lot : %s", json.dumps(resume, ensure_ascii=False))
    return resume
