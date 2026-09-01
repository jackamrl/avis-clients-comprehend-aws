"""Lambda #3 — api-rapports.

Backend HTTP du tableau de bord, derrière API Gateway (HTTP API) protégé par un
autoriseur JWT Cognito. La Lambda ne vérifie pas le jeton elle-même : API Gateway
rejette les requêtes non authentifiées avant même de l'invoquer.

Routes exposées :
    GET /rapports                    liste des rapports, du plus récent au plus ancien
    GET /rapports/{semaine_id}       rapport détaillé d'une semaine
    GET /avis?debut=&fin=&sentiment= avis unitaires d'une période (vue de détail)
"""

from __future__ import annotations

import json
import logging
import os
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Attr, Key

logger = logging.getLogger()
logger.setLevel(os.environ.get("NIVEAU_LOG", "INFO"))

dynamodb = boto3.resource("dynamodb")
table_avis = dynamodb.Table(os.environ["TABLE_AVIS"])
table_rapports = dynamodb.Table(os.environ["TABLE_RAPPORTS"])

INDEX_RAPPORTS = os.environ.get("INDEX_RAPPORTS", "rapports-par-date")
INDEX_AVIS_PAR_MOIS = os.environ.get("INDEX_AVIS_PAR_MOIS", "avis-par-mois")

LIMITE_PAR_DEFAUT = 12
LIMITE_MAX = 52


class EncodeurJson(json.JSONEncoder):
    """DynamoDB renvoie des Decimal, que le module json ne sait pas sérialiser."""

    def default(self, o):
        if isinstance(o, Decimal):
            return int(o) if o == o.to_integral_value() else float(o)
        return super().default(o)


def reponse(code: int, corps) -> dict:
    return {
        "statusCode": code,
        "headers": {"Content-Type": "application/json; charset=utf-8"},
        "body": json.dumps(corps, cls=EncodeurJson, ensure_ascii=False),
    }


def entier_borne(valeur: str | None, defaut: int, maximum: int) -> int:
    try:
        return max(1, min(int(valeur), maximum))
    except (TypeError, ValueError):
        return defaut


def lister_rapports(parametres: dict) -> dict:
    limite = entier_borne(parametres.get("limite"), LIMITE_PAR_DEFAUT, LIMITE_MAX)

    # Query sur l'index secondaire, trié à l'envers : DynamoDB rend directement
    # les rapports du plus récent au plus ancien, sans tri applicatif ni Scan.
    resultat = table_rapports.query(
        IndexName=INDEX_RAPPORTS,
        KeyConditionExpression=Key("type").eq("RAPPORT_HEBDO"),
        ScanIndexForward=False,
        Limit=limite,
    )

    rapports = resultat.get("Items", [])
    # La vue liste n'a pas besoin des exemples d'avis : on allège la charge utile.
    if parametres.get("resume") == "1":
        champs = {
            "semaine_id", "periode_debut", "periode_fin", "nb_avis",
            "pct_positif", "pct_negatif", "pct_neutre", "pct_mixte", "tendance",
        }
        rapports = [{c: r.get(c) for c in champs if c in r} for r in rapports]

    return {"nb": len(rapports), "rapports": rapports}


def obtenir_rapport(semaine_id: str) -> dict | None:
    resultat = table_rapports.get_item(Key={"semaine_id": semaine_id})
    return resultat.get("Item")


def lister_avis(parametres: dict) -> dict:
    debut = parametres.get("debut")
    fin = parametres.get("fin")
    if not debut or not fin:
        raise ValueError("les paramètres 'debut' et 'fin' (AAAA-MM-JJ) sont requis")

    sentiment = parametres.get("sentiment")
    mois_debut, mois_fin = debut[:7], fin[:7]
    seaux = sorted({mois_debut, mois_fin})

    avis: list[dict] = []
    for mois in seaux:
        requete = {
            "IndexName": INDEX_AVIS_PAR_MOIS,
            "KeyConditionExpression": Key("mois").eq(mois) & Key("date").between(debut, fin),
        }
        if sentiment:
            requete["FilterExpression"] = Attr("sentiment").eq(sentiment.upper())
        avis.extend(table_avis.query(**requete).get("Items", []))

    avis.sort(key=lambda item: (item["date"], item["avis_id"]))
    return {"nb": len(avis), "avis": avis}


def lambda_handler(event, context):  # noqa: ARG001 - signature imposée par Lambda
    # `routeKey` (« GET /rapports/{semaine_id} ») est la clé de routage stable :
    # contrairement au chemin, elle ne contient pas le nom de l'étape et reste
    # identique quel que soit le déploiement.
    route = event.get("routeKey", "")
    parametres = event.get("queryStringParameters") or {}
    variables = event.get("pathParameters") or {}

    logger.info("route %s", route)

    try:
        if route == "GET /avis":
            return reponse(200, lister_avis(parametres))

        if route == "GET /rapports/{semaine_id}":
            semaine_id = variables.get("semaine_id", "")
            rapport = obtenir_rapport(semaine_id)
            if not rapport:
                return reponse(404, {"erreur": f"rapport {semaine_id} introuvable"})
            return reponse(200, rapport)

        if route == "GET /rapports":
            return reponse(200, lister_rapports(parametres))

        return reponse(404, {"erreur": f"route inconnue : {route}"})

    except ValueError as erreur:
        return reponse(400, {"erreur": str(erreur)})
    except Exception:
        logger.exception("erreur lors du traitement de la route %s", route)
        return reponse(500, {"erreur": "erreur interne"})
