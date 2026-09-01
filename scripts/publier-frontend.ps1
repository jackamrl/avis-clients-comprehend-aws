<#
.SYNOPSIS
Génère frontend/config.js depuis les sorties CloudFormation, puis publie le
tableau de bord sur le bucket S3 configuré en hébergement statique.
#>
param(
    [string]$Pile = "nordichome",
    [string]$Region = "eu-west-1"
)

. "$PSScriptRoot\_commun.ps1"

$racine = Split-Path $PSScriptRoot -Parent
$sorties = Obtenir-SortiesPile -Pile $Pile -Region $Region

Ecrire-Etape "Génération de frontend/config.js"

$configuration = @"
/* Fichier généré par scripts/publier-frontend.ps1 — ne pas modifier à la main. */
window.CONFIG_NORDICHOME = {
  region: "$($sorties['Region'])",
  clientCognito: "$($sorties['ClientPoolUtilisateursId'])",
  urlApi: "$($sorties['UrlApi'])",
};
"@

$chemin = Join-Path $racine "frontend\config.js"
# Sans BOM : certains navigateurs le rendent visible en tête de fichier servi par S3.
[System.IO.File]::WriteAllText($chemin, $configuration, [System.Text.UTF8Encoding]::new($false))
Ecrire-Succes $chemin

Ecrire-Etape "Publication sur s3://$($sorties['BucketSiteWeb'])"
aws s3 sync (Join-Path $racine "frontend") "s3://$($sorties['BucketSiteWeb'])" `
    --region $Region `
    --exclude "config.example.js" `
    --delete
if ($LASTEXITCODE -ne 0) { throw "La synchronisation S3 a échoué." }

# Le type MIME par défaut deviné par S3 pour .js n'est pas toujours correct :
# on le force pour éviter un blocage par le navigateur.
aws s3 cp "s3://$($sorties['BucketSiteWeb'])/app.js" "s3://$($sorties['BucketSiteWeb'])/app.js" `
    --region $Region --content-type "application/javascript" --metadata-directive REPLACE | Out-Null
aws s3 cp "s3://$($sorties['BucketSiteWeb'])/config.js" "s3://$($sorties['BucketSiteWeb'])/config.js" `
    --region $Region --content-type "application/javascript" --metadata-directive REPLACE | Out-Null

Write-Host ""
Ecrire-Succes "Tableau de bord en ligne : $($sorties['UrlDashboard'])"
