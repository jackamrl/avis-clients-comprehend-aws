"""Applique la transformation AWS SAM en local et résume les ressources générées.

`sam validate` fait la même chose, mais suppose SAM CLI installé. Ce script ne
dépend que d'`aws-sam-translator`, tiré par cfn-lint :

    pip install --user cfn-lint
    python scripts/verifier_template.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

RACINE = Path(__file__).resolve().parent.parent

PARAMETRES = {
    "EmailExpediteur": "expediteur@exemple.fr",
    "EmailManager": "manager@exemple.fr",
    "ExpressionPlanification": "cron(0 8 ? * MON *)",
    "FuseauPlanification": "Europe/Paris",
    "RetentionLogsJours": 14,
}

ATTENDUES = {
    "AWS::Lambda::Function": 3,
    "AWS::DynamoDB::Table": 2,
    "AWS::S3::Bucket": 2,
    "AWS::Scheduler::Schedule": 1,
    "AWS::Cognito::UserPool": 1,
    "AWS::Cognito::UserPoolClient": 1,
    "AWS::ApiGatewayV2::Api": 1,
    "AWS::SES::EmailIdentity": 2,
    "AWS::CloudWatch::Alarm": 3,
    "AWS::SQS::Queue": 1,
    "AWS::Logs::LogGroup": 3,
    "AWS::Lambda::LayerVersion": 1,
}


def main() -> int:
    from cfnlint.decode import cfn_yaml
    from samtranslator.translator.transform import transform

    # cfn-lint 0.x renvoie (modèle, erreurs) ; cfn-lint 1.x renvoie le modèle seul.
    charge = cfn_yaml.load(str(RACINE / "template.yaml"))
    modele = charge[0] if isinstance(charge, tuple) else charge

    # Le traducteur SAM attend des URI S3, tels que `sam package` les produit.
    # On simule cette étape pour pouvoir valider le template sans SAM CLI.
    for definition in modele["Resources"].values():
        proprietes = definition.get("Properties", {})
        for champ in ("CodeUri", "ContentUri"):
            if isinstance(proprietes.get(champ), str):
                proprietes[champ] = "s3://paquet-fictif/code.zip"

    resultat = transform(modele, PARAMETRES, MagicMock())
    ressources = resultat["Resources"]

    comptes: dict[str, int] = {}
    for definition in ressources.values():
        comptes[definition["Type"]] = comptes.get(definition["Type"], 0) + 1

    print(f"{len(ressources)} ressources CloudFormation générées\n")
    for type_ressource in sorted(comptes):
        marque = " "
        if type_ressource in ATTENDUES:
            marque = "OK" if comptes[type_ressource] == ATTENDUES[type_ressource] else "!!"
        print(f"  {marque}  {comptes[type_ressource]:>2} x {type_ressource}")

    manquantes = [t for t in ATTENDUES if t not in comptes]
    ecarts = [
        f"{t} : {comptes[t]} au lieu de {ATTENDUES[t]}"
        for t in ATTENDUES
        if t in comptes and comptes[t] != ATTENDUES[t]
    ]

    print()
    if manquantes or ecarts:
        for type_ressource in manquantes:
            print(f"MANQUANT : {type_ressource}")
        for ecart in ecarts:
            print(f"ÉCART    : {ecart}")
        return 1

    for verification in (
        verifier_planification,
        verifier_api,
        verifier_index_dynamodb,
    ):
        verification(ressources)

    print("Transformation SAM valide, ressources et garde-fous conformes.")
    return 0


# --------------------------------------------------------------------------- #
# Garde-fous ciblés sur les réglages les plus faciles à casser
# --------------------------------------------------------------------------- #

def _unique(ressources: dict, type_ressource: str) -> dict:
    return next(d for d in ressources.values() if d["Type"] == type_ressource)


def verifier_planification(ressources: dict) -> None:
    proprietes = _unique(ressources, "AWS::Scheduler::Schedule")["Properties"]
    assert proprietes.get("ScheduleExpressionTimezone"), (
        "sans fuseau explicite, le cron serait interprété en UTC : le rapport "
        "arriverait à 9h en été et 8h en hiver"
    )
    assert proprietes["Target"].get("Input"), (
        "la charge utile fixe le nombre de jours analysés"
    )


def verifier_api(ressources: dict) -> None:
    """L'autoriseur JWT vit dans le corps OpenAPI, pas dans une ressource dédiée."""
    corps = _unique(ressources, "AWS::ApiGatewayV2::Api")["Properties"]["Body"]

    schemas = corps["components"]["securitySchemes"]
    autoriseur = schemas["AutorisateurCognito"]["x-amazon-apigateway-authorizer"]
    assert autoriseur["type"] == "jwt"
    assert autoriseur["jwtConfiguration"]["audience"], "audience Cognito absente"
    assert autoriseur["identitySource"] == "$request.header.Authorization"

    assert corps.get("x-amazon-apigateway-cors"), (
        "sans CORS, le dashboard servi depuis S3 ne peut pas appeler l'API"
    )

    # Le point critique : aucune route ne doit être exposée sans authentification.
    for chemin, methodes in corps["paths"].items():
        for methode, definition in methodes.items():
            assert definition.get("security"), f"route non protégée : {methode} {chemin}"


def verifier_index_dynamodb(ressources: dict) -> None:
    """Sans index secondaire, l'agrégation retomberait sur un Scan intégral."""
    tables = [d for d in ressources.values() if d["Type"] == "AWS::DynamoDB::Table"]
    index = {
        i["IndexName"]
        for t in tables
        for i in t["Properties"].get("GlobalSecondaryIndexes", [])
    }
    assert index == {"avis-par-mois", "rapports-par-date"}, f"index inattendus : {index}"


if __name__ == "__main__":
    sys.exit(main())
