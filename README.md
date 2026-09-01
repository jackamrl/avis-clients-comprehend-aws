# NordicHome — Reporting hebdomadaire de satisfaction client

Chaîne AWS *serverless* qui transforme des avis clients en texte libre en une
**synthèse hebdomadaire actionnable** : proportion d'avis positifs et négatifs,
tendance, et surtout **thèmes récurrents** de ce qui a bien fonctionné et de ce
qui a posé problème.

> Projet académique — module cloud avancé avec apprentissage automatique.
> Cas d'étude : *NordicHome*, e-commerce de mobilier (entreprise fictive).

---

## Le point clé

Le projet **ne se limite pas à une analyse de sentiment avis par avis**. Savoir
qu'un client donné est mécontent n'aide personne à décider. L'objet est
l'**agrégation périodique** : la question du dirigeant n'est pas « que pense ce
client ? » mais « comment s'est passée la semaine, et pourquoi ? ».

D'où deux chaînes distinctes :

| | Chaîne temps réel | Chaîne périodique |
|---|---|---|
| Déclencheur | dépôt d'un fichier sur S3 | EventBridge Scheduler, lundi 08h00 |
| Traitement | Comprehend → DynamoDB | statistiques + thèmes récurrents |
| Rejouable | non (coûterait un appel Comprehend) | **oui, gratuitement** |

Cette séparation n'est pas cosmétique : elle permet de faire évoluer le
vocabulaire métier et de **réinterpréter tout l'historique sans repayer un seul
appel Comprehend**.

## Architecture

```
                        ┌──────────── chaîne temps réel ────────────┐
  avis .txt  ──▶  S3  ──▶  Lambda  ──▶  Amazon Comprehend
                          traiter-avis      ├─ detect_sentiment
                                │           └─ detect_key_phrases
                                ▼
                        DynamoDB « Avis »  ──┐
                                             │
                        ┌──────────── chaîne périodique ────────────┐
  EventBridge Scheduler ──▶  Lambda generer-rapport-hebdo  ◀────────┘
     cron(0 8 ? * MON *)         │
                                 ├──▶  DynamoDB « Rapports »
                                 └──▶  SES  ──▶  e-mail au manager

                        ┌──────────── restitution ──────────────────┐
  Manager ──▶ Cognito ──▶ API Gateway (JWT) ──▶ Lambda api-rapports
          └──▶ S3 static website (tableau de bord)

  CloudWatch : journaux, métriques, alarmes ──▶ SNS ──▶ e-mail
```

Schéma détaillé et justification de chaque choix :
**[`docs/architecture.md`](docs/architecture.md)**.

## Démarrage rapide

### Sans compte AWS — validation de la logique métier

```powershell
pip install -r requirements-dev.txt
python -m pytest tests                  # 41 tests
python scripts\simulation_locale.py     # rapport complet sur les 28 avis
```

La simulation produit le rapport hebdomadaire — proportions, tendance, thèmes
récurrents avec citations — sans qu'aucune ressource AWS n'existe.

L'infrastructure se valide de la même façon, sans SAM CLI :

```powershell
pip install --user cfn-lint
cfn-lint template.yaml
python scripts\verifier_template.py   # transformation SAM + garde-fous
```

### Avec un compte AWS

```powershell
.\scripts\deployer.ps1 -EmailExpediteur vous@exemple.fr -EmailManager vous@exemple.fr
# valider les e-mails SES et l'abonnement SNS reçus
.\scripts\creer-manager.ps1  -Email vous@exemple.fr
.\scripts\publier-frontend.ps1
.\scripts\demo.ps1
```

Détail, prérequis et dépannage : **[`docs/deploiement.md`](docs/deploiement.md)**.

> **Région.** Le déploiement vise `eu-west-1` (Irlande).
> **Amazon Comprehend n'est pas disponible à Paris (`eu-west-3`).**

## Structure du dépôt

```
template.yaml                 infrastructure complète (AWS SAM)
samconfig.toml                paramètres de déploiement

src/
  couche_commune/python/nordichome/
    texte.py                  normalisation du français
    themes.py                 lexique métier des 6 thèmes
    fichiers.py               convention de nommage des fichiers S3
    agregation.py             calcul du rapport (sans dépendance AWS)
  traiter_avis/app.py         Lambda #1 — S3 → Comprehend → DynamoDB
  generer_rapport_hebdo/app.py Lambda #2 — agrégation + SES
  api_rapports/app.py         Lambda #3 — backend du tableau de bord

frontend/                     tableau de bord statique (aucune étape de build)
data/avis_test.json           28 avis annotés
scripts/                      déploiement, démonstration, simulation locale
tests/                        41 tests
docs/                         cadrage, architecture, déploiement, soutenance
```

## Des mots aux thèmes

L'étape qui distingue ce projet d'une simple analyse de sentiment.

```
Comprehend renvoie   « le colis », « la porte cassée », « une charnière arrachée »
Normalisation        colis, porte cassee, charniere arrachee
Projection           → thème « Colis et produits endommagés »
```

Sans cette projection, le rapport serait une liste plate de phrases clés, et
surtout deux semaines ne seraient pas comparables — les clients ne reformulant
jamais deux fois de la même façon.

Six thèmes, chacun défini par une liste de motifs :

| Négatif | Positif |
|---|---|
| Retards de livraison | Accueil en boutique |
| Colis et produits endommagés | Réactivité du service client |
| Service après-vente difficile à joindre | Qualité des produits |

**La polarité indiquée ci-dessus ne sert qu'à l'affichage.** Le rangement d'un
thème dans le palmarès positif ou négatif suit exclusivement le sentiment
détecté par Comprehend pour l'avis qui le porte. Un avis négatif parlant de
qualité produit fera remonter « Qualité des produits » côté négatif — c'est le
signal qu'une force se dégrade.

## Jeu de données

28 avis synthétiques en français, du lundi 17 au dimanche 23 août 2026
(semaine ISO `2026-W34`), quatre par jour.

| Polarité annotée | Nombre |
|---|---|
| Négatif | 13 (46 %) |
| Positif | 11 (39 %) |
| Neutre | 3 (11 %) |
| Mitigé | 1 (4 %) |

Proportions choisies pour produire une **semaine dégradée mais non
catastrophique** : la tendance ressort « mitigée », ce qui oblige à regarder les
thèmes pour comprendre — exactement le cas d'usage à démontrer.

Chaque avis porte un champ `themes_attendus`, annotation manuelle servant de
référence. Ce champ n'est jamais envoyé à AWS.

```powershell
python scripts\generer_fichiers_avis.py   # → 28 .txt + avis_incoming.zip
```

## Validation

```
Thèmes injectés volontairement  : 31
Thèmes retrouvés par le lexique : 31   (rappel 100 %)
Thèmes détectés en plus         : 2    (sur un avis neutre, sans effet)
```

41 tests couvrent la normalisation du français, la détection de chaque thème,
les fenêtres temporelles à cheval sur deux mois, le calcul de la tendance, le
corpus vide, la convention de nommage et la troncature UTF-8 aux limites de
Comprehend.

Pour mesurer la concordance réelle entre Comprehend et l'annotation manuelle :

```powershell
python scripts\simulation_locale.py --comprehend --region eu-west-1
```

## Coût

Nul pendant la durée du projet grâce au free tier. Au-delà, pour 500 avis par
mois : de l'ordre de quelques dizaines de centimes. Détail poste par poste en
section 5 de [`docs/architecture.md`](docs/architecture.md).

Suppression complète des ressources :

```powershell
.\scripts\nettoyer.ps1
```

## Documentation

| Document | Contenu |
|---|---|
| [`docs/cadrage.md`](docs/cadrage.md) | contexte, problématique, pertinence de l'approche, limites |
| [`docs/architecture.md`](docs/architecture.md) | schéma, rôle de chaque service, justifications, coûts |
| [`docs/deploiement.md`](docs/deploiement.md) | prérequis, IAM, déploiement, démonstration, dépannage |
| [`docs/soutenance.md`](docs/soutenance.md) | plan du support, déroulé vidéo, questions anticipées |
