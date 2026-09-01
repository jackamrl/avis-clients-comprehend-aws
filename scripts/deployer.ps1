<#
.SYNOPSIS
Construit et déploie la pile NordicHome.

.EXAMPLE
.\scripts\deployer.ps1 -EmailExpediteur rapports@exemple.fr -EmailManager moi@exemple.fr
#>
param(
    [Parameter(Mandatory)] [string]$EmailExpediteur,
    [Parameter(Mandatory)] [string]$EmailManager,
    [string]$Pile = "nordichome",
    # Amazon Comprehend n'est pas disponible à Paris (eu-west-3).
    [ValidateSet("eu-west-1", "eu-west-2", "eu-central-1", "us-east-1", "us-west-2")]
    [string]$Region = "eu-west-1"
)

. "$PSScriptRoot\_commun.ps1"

Tester-Outil "aws" "Installez AWS CLI v2 : https://aws.amazon.com/cli/"
Tester-Outil "sam" "Installez AWS SAM CLI : winget install Amazon.SAM-CLI"

Push-Location (Split-Path $PSScriptRoot -Parent)
try {
    Ecrire-Etape "Identité AWS utilisée"
    aws sts get-caller-identity --output table

    Ecrire-Etape "Construction du paquet SAM"
    sam build
    if ($LASTEXITCODE -ne 0) { throw "sam build a échoué." }

    Ecrire-Etape "Déploiement de la pile '$Pile' dans $Region"
    sam deploy `
        --stack-name $Pile `
        --region $Region `
        --capabilities CAPABILITY_IAM `
        --resolve-s3 `
        --no-confirm-changeset `
        --no-fail-on-empty-changeset `
        --parameter-overrides "EmailExpediteur=$EmailExpediteur" "EmailManager=$EmailManager"
    if ($LASTEXITCODE -ne 0) { throw "sam deploy a échoué." }

    $sorties = Obtenir-SortiesPile -Pile $Pile -Region $Region

    Ecrire-Etape "Pile déployée"
    foreach ($cle in $sorties.Keys | Sort-Object) {
        Write-Host ("   {0,-26} {1}" -f $cle, $sorties[$cle])
    }

    Write-Host ""
    Write-Host "À FAIRE MAINTENANT" -ForegroundColor Yellow
    Write-Host "  1. Validez les e-mails de vérification SES reçus sur :" -ForegroundColor Yellow
    Write-Host "     $EmailExpediteur et $EmailManager" -ForegroundColor Yellow
    Write-Host "     (obligatoire : SES reste en bac à sable)" -ForegroundColor Yellow
    Write-Host "  2. Confirmez l'abonnement SNS reçu sur $EmailManager (alertes CloudWatch)." -ForegroundColor Yellow
    Write-Host "  3. Créez le compte manager   : .\scripts\creer-manager.ps1 -Email $EmailManager" -ForegroundColor Yellow
    Write-Host "  4. Publiez le tableau de bord: .\scripts\publier-frontend.ps1" -ForegroundColor Yellow
    Write-Host "  5. Lancez la démonstration   : .\scripts\demo.ps1" -ForegroundColor Yellow
}
finally {
    Pop-Location
}
