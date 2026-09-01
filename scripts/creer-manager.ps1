<#
.SYNOPSIS
Crée le compte manager dans le pool Cognito.

.DESCRIPTION
Le pool interdit l'auto-inscription : les comptes sont créés par un
administrateur. Cognito génère un mot de passe temporaire ; le tableau de bord
demandera de le remplacer à la première connexion.

.EXAMPLE
.\scripts\creer-manager.ps1 -Email manager@exemple.fr
#>
param(
    [Parameter(Mandatory)] [string]$Email,
    [string]$MotDePasseTemporaire = "Nordic2026Temp!",
    [string]$Pile = "nordichome",
    [string]$Region = "eu-west-1"
)

. "$PSScriptRoot\_commun.ps1"

$sorties = Obtenir-SortiesPile -Pile $Pile -Region $Region
$pool = $sorties["PoolUtilisateursId"]

Ecrire-Etape "Création du compte $Email dans le pool $pool"

aws cognito-idp admin-create-user `
    --user-pool-id $pool `
    --username $Email `
    --user-attributes "Name=email,Value=$Email" "Name=email_verified,Value=true" `
    --temporary-password $MotDePasseTemporaire `
    --message-action SUPPRESS `
    --region $Region `
    --output json | Out-Null

if ($LASTEXITCODE -ne 0) {
    Write-Host "   Le compte existe peut-être déjà : réinitialisation du mot de passe temporaire." -ForegroundColor Yellow
    aws cognito-idp admin-set-user-password `
        --user-pool-id $pool --username $Email `
        --password $MotDePasseTemporaire --region $Region | Out-Null
}

Ecrire-Succes "Compte prêt."
Write-Host ""
Write-Host "   Identifiants de première connexion" -ForegroundColor Yellow
Write-Host "     Adresse          : $Email"
Write-Host "     Mot de passe     : $MotDePasseTemporaire"
Write-Host "     Tableau de bord  : $($sorties['UrlDashboard'])"
Write-Host ""
Ecrire-Info "Le nouveau mot de passe devra faire 12 caractères, avec majuscule et chiffre."
