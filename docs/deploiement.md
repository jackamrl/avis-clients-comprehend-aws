# Guide de déploiement

Toutes les commandes sont données pour **PowerShell sous Windows**, depuis la
racine du projet.

---

## 1. Prérequis

### 1.1 Outils

| Outil | Vérification | Installation |
|---|---|---|
| Python 3.12+ | `python --version` | [python.org](https://www.python.org/downloads/) |
| AWS CLI v2 | `aws --version` | `winget install Amazon.AWSCLI` |
| AWS SAM CLI | `sam --version` | `winget install Amazon.SAM-CLI` |

> **SAM CLI n'est pas installé par défaut.** Après `winget install Amazon.SAM-CLI`,
> fermez et rouvrez le terminal pour que le `PATH` soit rechargé. En cas d'échec
> de winget, le programme d'installation MSI est disponible sur la
> [page de téléchargement AWS SAM](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html).

### 1.2 Compte AWS et région

Le projet se déploie dans **une seule région**. La valeur par défaut est
`eu-west-1` (Irlande).

> **Ne déployez pas dans `eu-west-3` (Paris).** Amazon Comprehend n'y est pas
> disponible. Les régions européennes qui le proposent sont `eu-west-1`
> (Irlande), `eu-west-2` (Londres) et `eu-central-1` (Francfort).

### 1.3 Identifiants IAM

Créez un utilisateur IAM dédié au déploiement plutôt que d'utiliser le compte
racine. Pour un bac à sable académique, la politique gérée `PowerUserAccess`
complétée des droits IAM suivants suffit :

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "iam:CreateRole", "iam:DeleteRole", "iam:GetRole", "iam:PassRole",
        "iam:AttachRolePolicy", "iam:DetachRolePolicy",
        "iam:PutRolePolicy", "iam:DeleteRolePolicy", "iam:GetRolePolicy",
        "iam:TagRole", "iam:UntagRole", "iam:ListRoleTags"
      ],
      "Resource": "*"
    }
  ]
}
```

Ces droits IAM sont nécessaires parce que SAM crée un rôle d'exécution par
fonction Lambda, avec le minimum de permissions requis.

Configurez ensuite le profil local :

```powershell
aws configure
aws sts get-caller-identity   # doit renvoyer votre compte
```

> **Cas particulier — AWS Academy Learner Lab.** Ces environnements interdisent
> la création de rôles IAM et imposent l'usage du rôle préexistant `LabRole`,
> en région `us-east-1`. Le template devrait alors être adapté pour référencer
> ce rôle (`Role: arn:aws:iam::<compte>:role/LabRole` sur chaque fonction, en
> retirant les blocs `Policies`). Un compte AWS personnel en free tier évite
> cette contrainte et reste gratuit pour ce projet.

### 1.4 Adresses e-mail

Deux adresses sont demandées au déploiement. **Elles peuvent être identiques.**

| Paramètre | Rôle |
|---|---|
| `EmailExpediteur` | expéditeur des rapports SES |
| `EmailManager` | destinataire des rapports, des alertes CloudWatch, et compte du tableau de bord |

SES reste en **bac à sable** : les deux adresses devront être vérifiées par un
clic dans un e-mail de confirmation envoyé au déploiement. Utilisez des adresses
réelles auxquelles vous avez accès.

---

## 2. Déploiement

### 2.1 Vérification préalable, sans AWS

Avant tout déploiement, la logique métier peut être validée hors ligne :

```powershell
pip install -r requirements-dev.txt
python -m pytest tests          # 41 tests
python scripts\simulation_locale.py
```

La simulation affiche le rapport hebdomadaire complet — proportions, tendance,
thèmes récurrents — calculé sur les 28 avis de test sans qu'aucune ressource AWS
n'existe.

L'infrastructure peut elle aussi être validée sans SAM CLI ni compte AWS :

```powershell
pip install --user cfn-lint
cfn-lint template.yaml
python scripts\verifier_template.py
```

Le second script applique la transformation SAM en local, dénombre les ressources
CloudFormation générées et vérifie les réglages les plus faciles à casser : fuseau
horaire du planificateur, présence de l'autoriseur JWT, absence de route exposée
sans authentification, et existence des deux index secondaires DynamoDB.

### 2.2 Déploiement de la pile

```powershell
.\scripts\deployer.ps1 `
    -EmailExpediteur rapports@votredomaine.fr `
    -EmailManager    vous@votredomaine.fr
```

Le script enchaîne `sam build` puis `sam deploy`, et affiche les sorties de la
pile. Comptez trois à cinq minutes la première fois — Cognito et DynamoDB sont
les ressources les plus lentes à créer.

Options disponibles : `-Region`, `-Pile` (nom de la pile, `nordichome` par
défaut).

### 2.3 Confirmations manuelles

Trois actions ne peuvent pas être automatisées, pour des raisons de sécurité.

1. **Vérification SES.** Un e-mail *« Amazon Web Services – Email Address
   Verification Request »* arrive sur chacune des deux adresses. Cliquez le lien
   dans les 24 heures. Sans cela, l'envoi du rapport échouera — le rapport sera
   tout de même généré et stocké, avec `statut_email = "echec"`.

2. **Abonnement SNS.** Un e-mail *« AWS Notification – Subscription
   Confirmation »* arrive sur `EmailManager`. Cliquez *Confirm subscription*
   pour recevoir les alarmes CloudWatch.

3. **Vérification de l'état SES** (facultatif) :

```powershell
aws ses get-identity-verification-attributes `
    --identities vous@votredomaine.fr --region eu-west-1
```

### 2.4 Création du compte manager

```powershell
.\scripts\creer-manager.ps1 -Email vous@votredomaine.fr
```

Le script affiche le mot de passe temporaire. Le pool Cognito interdisant
l'auto-inscription, c'est la seule façon de créer un compte.

### 2.5 Publication du tableau de bord

```powershell
.\scripts\publier-frontend.ps1
```

Ce script génère `frontend/config.js` à partir des sorties CloudFormation
(région, identifiant du client Cognito, URL de l'API), synchronise le dossier
`frontend/` vers le bucket S3 et corrige les types MIME des fichiers JavaScript.

Il affiche l'URL publique du tableau de bord.

---

## 3. Démonstration

### 3.1 Déroulé complet en une commande

```powershell
.\scripts\demo.ps1 -Cadence 0.5
```

Le script :

1. dépose les 28 avis dans `s3://<bucket>/incoming/`, un toutes les
   0,5 seconde — le rythme rend les invocations visibles dans CloudWatch, ce qui
   est utile pour une démonstration filmée ;
2. interroge DynamoDB jusqu'à ce que les 28 avis soient analysés ;
3. invoque la Lambda d'agrégation sur la semaine du 17 au 23 août 2026 ;
4. affiche le rapport dans la console et ouvre le tableau de bord.

### 3.2 Étape par étape

Pour maîtriser le rythme pendant une démonstration en direct :

```powershell
# Dépôt des avis
.\scripts\charger-avis.ps1 -Cadence 1

# Suivi des analyses en direct (dans un second terminal)
aws logs tail /aws/lambda/nordichome-traiter-avis --follow --region eu-west-1

# Contenu de la table Avis
aws dynamodb scan --table-name nordichome-Avis --region eu-west-1 `
    --projection-expression "avis_id,sentiment,score_confiance" `
    --max-items 5 --output table

# Génération du rapport
.\scripts\lancer-rapport.ps1 -DateFin 2026-08-23

# Rapport stocké
aws dynamodb get-item --table-name nordichome-Rapports --region eu-west-1 `
    --key '{\"semaine_id\":{\"S\":\"2026-W34\"}}' --output json
```

### 3.3 Vérifier la planification hebdomadaire

Pour montrer que le déclenchement automatique existe réellement :

```powershell
aws scheduler get-schedule --name nordichome-rapport-hebdo --region eu-west-1
```

Pour provoquer un déclenchement pendant la soutenance, reprogrammez la
planification quelques minutes plus tard :

```powershell
aws cloudformation update-stack --stack-name nordichome --use-previous-template `
    --capabilities CAPABILITY_IAM --region eu-west-1 `
    --parameters ParameterKey=ExpressionPlanification,ParameterValue="cron(35 14 * * ? *)" `
                 ParameterKey=EmailExpediteur,UsePreviousValue=true `
                 ParameterKey=EmailManager,UsePreviousValue=true `
                 ParameterKey=FuseauPlanification,UsePreviousValue=true `
                 ParameterKey=RetentionLogsJours,UsePreviousValue=true
```

> Attention : ce déclenchement calcule la fenêtre sur les 7 derniers jours
> **réels**, pas sur août 2026. Le rapport sera vide si aucun avis récent n'a été
> déposé. Pour une démonstration convaincante, redatez quelques fichiers d'avis
> sur la semaine en cours avant de les déposer.

### 3.4 Mesurer la concordance avec Comprehend

```powershell
python scripts\simulation_locale.py --comprehend --region eu-west-1
```

Appelle réellement Comprehend sur les 28 avis et compare ses prédictions à
l'annotation manuelle. Coût : 56 appels, très en deçà du free tier.

---

## 4. Dépannage

| Symptôme | Cause | Résolution |
|---|---|---|
| `sam : terme non reconnu` | SAM CLI absent du `PATH` | `winget install Amazon.SAM-CLI` puis rouvrir le terminal |
| `Could not connect to the endpoint URL ... comprehend.eu-west-3` | Comprehend absent à Paris | redéployer en `eu-west-1` |
| `statut_email = "echec"` | adresse SES non vérifiée | cliquer le lien de vérification, puis relancer `lancer-rapport.ps1` |
| `Email address is not verified` dans les logs | idem, côté destinataire | vérifier **les deux** adresses |
| Le tableau de bord affiche « config.js absent » | frontend publié sans `config.js` | relancer `publier-frontend.ps1` |
| `401 Unauthorized` sur l'API | jeton expiré (60 min) | se reconnecter |
| Connexion refusée avec le bon mot de passe | mot de passe temporaire jamais remplacé | le champ « nouveau mot de passe » apparaît automatiquement ; 12 caractères, 1 majuscule, 1 chiffre |
| Le rapport indique 0 avis | fenêtre temporelle sans données | préciser `-DateFin 2026-08-23` |
| Avis absents de DynamoDB | nom de fichier non conforme | `aws logs tail /aws/lambda/nordichome-traiter-avis --region eu-west-1` ; format attendu `{avis_id}_{AAAA-MM-JJ}_{client_id}.txt` |
| `ROLLBACK_COMPLETE` au premier déploiement | pile en échec à supprimer | `aws cloudformation delete-stack --stack-name nordichome --region eu-west-1` puis redéployer |
| `Bucket already exists` | nom global déjà pris | changer `-Pile` pour un autre nom |

### Journaux

```powershell
aws logs tail /aws/lambda/nordichome-traiter-avis          --follow --region eu-west-1
aws logs tail /aws/lambda/nordichome-generer-rapport-hebdo --follow --region eu-west-1
aws logs tail /aws/lambda/nordichome-api-rapports          --follow --region eu-west-1
```

### Avis en échec définitif

```powershell
aws sqs receive-message --region eu-west-1 `
    --queue-url (aws sqs get-queue-url --queue-name nordichome-traiter-avis-dlq `
                 --region eu-west-1 --query QueueUrl --output text)
```

---

## 5. Suppression

```powershell
.\scripts\nettoyer.ps1
```

Purge les deux buckets — CloudFormation refuse de supprimer un bucket non vide —
puis supprime la pile.

Restent dans le compte, à supprimer manuellement depuis la console si besoin :

- les **identités SES vérifiées** (console SES → Verified identities) ;
- le **bucket de déploiement SAM** `aws-sam-cli-managed-default-*`, réutilisable
  pour d'autres projets.
