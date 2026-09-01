"""Lambda #2 — generer-rapport-hebdo.

Déclenchée chaque lundi à 08h00 (Europe/Paris) par EventBridge Scheduler.
Agrège les avis des 7 derniers jours, calcule la répartition des sentiments,
fait ressortir les thèmes récurrents positifs et négatifs, stocke le rapport
dans DynamoDB « Rapports » et envoie la synthèse par e-mail via SES.

C'est ici que se joue la valeur du projet : l'analyse avis par avis n'est qu'une
étape intermédiaire, le livrable métier est cette synthèse périodique.

Le calcul lui-même vit dans `nordichome.agregation` (couche partagée) ; ce
module ne gère que les entrées-sorties AWS.

Déclenchement manuel pour la démonstration :
    {"date_fin": "2026-08-23", "jours": 7, "envoyer_email": true}
"""

from __future__ import annotations

import json
import logging
import os
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key

from nordichome import agregation

logger = logging.getLogger()
logger.setLevel(os.environ.get("NIVEAU_LOG", "INFO"))

dynamodb = boto3.resource("dynamodb")
table_avis = dynamodb.Table(os.environ["TABLE_AVIS"])
table_rapports = dynamodb.Table(os.environ["TABLE_RAPPORTS"])
ses = boto3.client("ses")

INDEX_PAR_MOIS = os.environ.get("INDEX_AVIS_PAR_MOIS", "avis-par-mois")
EXPEDITEUR = os.environ.get("EXPEDITEUR_SES", "")
DESTINATAIRES = [
    adresse.strip()
    for adresse in os.environ.get("DESTINATAIRES_SES", "").split(",")
    if adresse.strip()
]
URL_DASHBOARD = os.environ.get("URL_DASHBOARD", "")
FUSEAU = os.environ.get("FUSEAU_HORAIRE", "Europe/Paris")


# --------------------------------------------------------------------------- #
# Lecture DynamoDB
# --------------------------------------------------------------------------- #

def lire_avis(debut: date, fin: date) -> list[dict]:
    """Query sur l'index secondaire plutôt qu'un Scan de la table entière.

    Le Scan lit tout l'historique à chaque exécution : son coût et sa latence
    croissent indéfiniment, alors que la fenêtre analysée reste de 7 jours.
    """
    avis: list[dict] = []
    for mois in agregation.seaux_mensuels(debut, fin):
        jeton = None
        while True:
            parametres = {
                "IndexName": INDEX_PAR_MOIS,
                "KeyConditionExpression": Key("mois").eq(mois)
                & Key("date").between(debut.isoformat(), fin.isoformat()),
            }
            if jeton:
                parametres["ExclusiveStartKey"] = jeton

            reponse = table_avis.query(**parametres)
            avis.extend(reponse.get("Items", []))

            jeton = reponse.get("LastEvaluatedKey")
            if not jeton:
                break

    logger.info("%d avis lus entre %s et %s", len(avis), debut, fin)
    return avis


def comparer_semaine_precedente(rapport: dict, debut: date) -> dict | None:
    precedent_id = agregation.identifiant_semaine(debut - timedelta(days=7))
    precedent = table_rapports.get_item(Key={"semaine_id": precedent_id}).get("Item")
    if not precedent:
        return None

    def delta(champ: str) -> Decimal:
        ecart = float(rapport[champ]) - float(precedent.get(champ, 0))
        return Decimal(str(round(ecart, 1)))

    return {
        "semaine_id": precedent_id,
        "delta_pct_positif": delta("pct_positif"),
        "delta_pct_negatif": delta("pct_negatif"),
        "delta_nb_avis": int(rapport["nb_avis"]) - int(precedent.get("nb_avis", 0)),
    }


# --------------------------------------------------------------------------- #
# Mise en forme de l'e-mail
# --------------------------------------------------------------------------- #

LIBELLES_TENDANCE = {
    "positive": ("Tendance positive", "#16a34a"),
    "negative": ("Tendance négative", "#dc2626"),
    "mitigee": ("Tendance mitigée", "#d97706"),
    "indeterminee": ("Données insuffisantes", "#6b7280"),
}


def liste_html(themes_classes: list[dict], couleur: str) -> str:
    if not themes_classes:
        return "<p style='color:#6b7280;margin:0'>Aucun thème récurrent identifié.</p>"

    lignes = []
    for entree in themes_classes:
        exemple = entree["exemples"][0]["extrait"] if entree["exemples"] else ""
        lignes.append(
            f"<li style='margin-bottom:10px'>"
            f"<strong style='color:{couleur}'>{entree['libelle']}</strong> "
            f"<span style='color:#6b7280'>— {entree['occurrences']} avis "
            f"({entree['part']} %)</span>"
            f"<br><em style='color:#4b5563;font-size:13px'>« {exemple} »</em>"
            f"</li>"
        )
    return f"<ul style='padding-left:18px;margin:0'>{''.join(lignes)}</ul>"


def corps_html(rapport: dict) -> str:
    titre_tendance, couleur_tendance = LIBELLES_TENDANCE[rapport["tendance"]]

    comparaison = rapport.get("comparaison_semaine_precedente")
    if comparaison:
        ecart = float(comparaison["delta_pct_positif"])
        signe = "+" if ecart >= 0 else ""
        bloc_comparaison = (
            f"<p style='color:#4b5563;margin:4px 0 0'>Avis positifs : "
            f"<strong>{signe}{ecart} pts</strong> par rapport à la semaine "
            f"{comparaison['semaine_id']}.</p>"
        )
    else:
        bloc_comparaison = ""

    lien = (
        f"<p style='margin-top:24px'><a href='{URL_DASHBOARD}' "
        f"style='background:#111827;color:#fff;padding:10px 18px;border-radius:6px;"
        f"text-decoration:none;font-size:14px'>Ouvrir le tableau de bord</a></p>"
        if URL_DASHBOARD
        else ""
    )

    return f"""<html><body style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;
background:#f9fafb;padding:24px;color:#111827">
<div style="max-width:640px;margin:auto;background:#fff;border-radius:12px;
padding:28px;border:1px solid #e5e7eb">
  <p style="margin:0;color:#6b7280;font-size:13px;letter-spacing:.05em;
  text-transform:uppercase">NordicHome · Satisfaction client</p>
  <h1 style="margin:6px 0 2px;font-size:22px">Semaine {rapport['semaine_id']}</h1>
  <p style="margin:0;color:#6b7280;font-size:14px">
    Du {rapport['periode_debut']} au {rapport['periode_fin']} ·
    {rapport['nb_avis']} avis analysés
  </p>

  <p style="margin:18px 0 0;font-size:17px;font-weight:600;color:{couleur_tendance}">
    {titre_tendance}
  </p>
  {bloc_comparaison}

  <table style="width:100%;margin:20px 0;border-collapse:separate;border-spacing:8px 0">
    <tr>
      <td style="background:#f0fdf4;border-radius:8px;padding:14px;text-align:center">
        <div style="font-size:26px;font-weight:700;color:#16a34a">{rapport['pct_positif']} %</div>
        <div style="font-size:12px;color:#6b7280">Positifs ({rapport['nb_positif']})</div>
      </td>
      <td style="background:#fef2f2;border-radius:8px;padding:14px;text-align:center">
        <div style="font-size:26px;font-weight:700;color:#dc2626">{rapport['pct_negatif']} %</div>
        <div style="font-size:12px;color:#6b7280">Négatifs ({rapport['nb_negatif']})</div>
      </td>
      <td style="background:#f3f4f6;border-radius:8px;padding:14px;text-align:center">
        <div style="font-size:26px;font-weight:700;color:#4b5563">{rapport['pct_neutre']} %</div>
        <div style="font-size:12px;color:#6b7280">Neutres ({rapport['nb_neutre']})</div>
      </td>
    </tr>
  </table>

  <h2 style="font-size:15px;margin:22px 0 8px">Ce qui a posé problème</h2>
  {liste_html(rapport['top_negatifs'], '#dc2626')}

  <h2 style="font-size:15px;margin:22px 0 8px">Ce qui a bien fonctionné</h2>
  {liste_html(rapport['top_positifs'], '#16a34a')}

  {lien}
  <p style="margin-top:24px;color:#9ca3af;font-size:12px">
    Rapport généré automatiquement le {rapport['date_generation']} —
    analyse Amazon Comprehend, agrégation AWS Lambda.
  </p>
</div></body></html>"""


def corps_texte(rapport: dict) -> str:
    def palmares(themes_classes: list[dict]) -> list[str]:
        if not themes_classes:
            return ["  - aucun thème récurrent"]
        return [f"  - {e['libelle']} ({e['occurrences']} avis)" for e in themes_classes]

    lignes = [
        f"NordicHome — Satisfaction client, semaine {rapport['semaine_id']}",
        f"Période : {rapport['periode_debut']} au {rapport['periode_fin']}",
        f"{rapport['nb_avis']} avis analysés — tendance {rapport['tendance']}",
        "",
        f"Positifs : {rapport['pct_positif']} % ({rapport['nb_positif']})",
        f"Négatifs : {rapport['pct_negatif']} % ({rapport['nb_negatif']})",
        f"Neutres  : {rapport['pct_neutre']} % ({rapport['nb_neutre']})",
        "",
        "Ce qui a posé problème :",
        *palmares(rapport["top_negatifs"]),
        "",
        "Ce qui a bien fonctionné :",
        *palmares(rapport["top_positifs"]),
    ]
    if URL_DASHBOARD:
        lignes += ["", f"Tableau de bord : {URL_DASHBOARD}"]
    return "\n".join(lignes)


def envoyer_email(rapport: dict) -> str:
    if not EXPEDITEUR or not DESTINATAIRES:
        logger.warning("SES non configuré (expéditeur ou destinataires manquants)")
        return "non_configure"

    sujet = (
        f"[NordicHome] Satisfaction semaine {rapport['semaine_id']} — "
        f"{rapport['pct_positif']} % positifs, {rapport['pct_negatif']} % négatifs"
    )
    try:
        ses.send_email(
            Source=EXPEDITEUR,
            Destination={"ToAddresses": DESTINATAIRES},
            Message={
                "Subject": {"Data": sujet, "Charset": "UTF-8"},
                "Body": {
                    "Text": {"Data": corps_texte(rapport), "Charset": "UTF-8"},
                    "Html": {"Data": corps_html(rapport), "Charset": "UTF-8"},
                },
            },
        )
        return "envoye"
    except Exception:
        # En bac à sable SES, une adresse non vérifiée fait échouer l'envoi.
        # Le rapport est déjà persisté : inutile de faire échouer l'exécution.
        logger.exception("échec de l'envoi SES")
        return "echec"


# --------------------------------------------------------------------------- #
# Point d'entrée
# --------------------------------------------------------------------------- #

def lambda_handler(event, context):  # noqa: ARG001 - signature imposée par Lambda
    evenement = event if isinstance(event, dict) else {}
    debut, fin = agregation.calculer_fenetre(evenement, FUSEAU)

    rapport = agregation.agreger(lire_avis(debut, fin), debut, fin)

    comparaison = comparer_semaine_precedente(rapport, debut)
    if comparaison:
        rapport["comparaison_semaine_precedente"] = comparaison

    rapport["date_generation"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    # Attribut constant : clé de partition de l'index qui permet de lister les
    # rapports par ordre chronologique sans Scan.
    rapport["type"] = "RAPPORT_HEBDO"

    table_rapports.put_item(Item=rapport)
    logger.info("rapport %s enregistré (%d avis)", rapport["semaine_id"], rapport["nb_avis"])

    if evenement.get("envoyer_email", True):
        rapport["statut_email"] = envoyer_email(rapport)
        table_rapports.update_item(
            Key={"semaine_id": rapport["semaine_id"]},
            UpdateExpression="SET statut_email = :s",
            ExpressionAttributeValues={":s": rapport["statut_email"]},
        )
    else:
        rapport["statut_email"] = "desactive"

    return json.loads(json.dumps(rapport, default=float, ensure_ascii=False))
