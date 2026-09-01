# Fonctions partagées par les scripts de déploiement et de démonstration.
# Chargé via : . "$PSScriptRoot\_commun.ps1"

$ErrorActionPreference = "Stop"

# Un terminal ouvert avant `winget install Amazon.SAM-CLI` n'a pas le PATH à jour.
# On recharge le PATH Machine+User, puis on ajoute l'emplacement d'installation connu.
$env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
            [Environment]::GetEnvironmentVariable("Path", "User")
$dossierSam = "C:\Program Files\Amazon\AWSSAMCLI\bin"
if ((Test-Path $dossierSam) -and ($env:Path -notlike "*$dossierSam*")) {
    $env:Path = "$dossierSam;$env:Path"
}

function Ecrire-Etape([string]$Message) {
    Write-Host ""
    Write-Host "== $Message" -ForegroundColor Cyan
}

function Ecrire-Succes([string]$Message) {
    Write-Host "   $Message" -ForegroundColor Green
}

function Ecrire-Info([string]$Message) {
    Write-Host "   $Message" -ForegroundColor DarkGray
}

function Tester-Outil([string]$Nom, [string]$Aide) {
    if (-not (Get-Command $Nom -ErrorAction SilentlyContinue)) {
        throw "$Nom est introuvable. $Aide"
    }
}

<#
.SYNOPSIS
Récupère les sorties de la pile CloudFormation sous forme de table de hachage.
#>
function Obtenir-SortiesPile {
    param(
        [Parameter(Mandatory)] [string]$Pile,
        [Parameter(Mandatory)] [string]$Region
    )

    $brut = aws cloudformation describe-stacks `
        --stack-name $Pile --region $Region `
        --query "Stacks[0].Outputs" --output json 2>$null

    if ($LASTEXITCODE -ne 0 -or -not $brut) {
        throw "Pile '$Pile' introuvable dans la région $Region. Déployez-la d'abord (scripts\deployer.ps1)."
    }

    $sorties = @{}
    foreach ($entree in ($brut | ConvertFrom-Json)) {
        $sorties[$entree.OutputKey] = $entree.OutputValue
    }
    return $sorties
}
