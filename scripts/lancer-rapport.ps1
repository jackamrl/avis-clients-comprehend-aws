<#
.SYNOPSIS
Déclenche manuellement la Lambda d'agrégation hebdomadaire.

.DESCRIPTION
En production, EventBridge Scheduler invoque cette Lambda chaque lundi à 08h00.
Pour la démonstration on l'invoque directement, avec une date de fin choisie
afin de tomber sur la semaine du jeu de données (17 -> 23 août 2026).

.EXAMPLE
.\scripts\lancer-rapport.ps1 -DateFin 2026-08-23
#>
param(
    [string]$DateFin = "2026-08-23",
    [int]$Jours = 7,
    [switch]$SansEmail,
    [string]$Pile = "nordichome",
    [string]$Region = "eu-west-1"
)

. "$PSScriptRoot\_commun.ps1"

$sorties = Obtenir-SortiesPile -Pile $Pile -Region $Region
$fonction = $sorties["FonctionRapportHebdo"]

$charge = @{
    date_fin       = $DateFin
    jours          = $Jours
    envoyer_email  = (-not $SansEmail.IsPresent)
} | ConvertTo-Json -Compress

$fichierCharge = New-TemporaryFile
[System.IO.File]::WriteAllText($fichierCharge.FullName, $charge, [System.Text.UTF8Encoding]::new($false))
$fichierReponse = New-TemporaryFile

Ecrire-Etape "Invocation de $fonction"
Ecrire-Info "Charge : $charge"

aws lambda invoke `
    --function-name $fonction `
    --region $Region `
    --cli-binary-format raw-in-base64-out `
    --payload "file://$($fichierCharge.FullName)" `
    $fichierReponse.FullName --output json | Out-Null

if ($LASTEXITCODE -ne 0) { throw "L'invocation a échoué." }

$rapport = Get-Content $fichierReponse.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
Remove-Item $fichierCharge, $fichierReponse -ErrorAction SilentlyContinue

if ($rapport.errorMessage) {
    Write-Host "   Erreur Lambda : $($rapport.errorMessage)" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "  Rapport $($rapport.semaine_id)" -ForegroundColor White
Write-Host "  Période        : $($rapport.periode_debut) -> $($rapport.periode_fin)"
Write-Host "  Avis analysés  : $($rapport.nb_avis)"
Write-Host "  Tendance       : $($rapport.tendance)"
Write-Host ("  Positifs       : {0} % ({1})" -f $rapport.pct_positif, $rapport.nb_positif) -ForegroundColor Green
Write-Host ("  Négatifs       : {0} % ({1})" -f $rapport.pct_negatif, $rapport.nb_negatif) -ForegroundColor Red
Write-Host ("  Neutres        : {0} % ({1})" -f $rapport.pct_neutre, $rapport.nb_neutre) -ForegroundColor DarkGray
Write-Host "  E-mail SES     : $($rapport.statut_email)"

Write-Host ""
Write-Host "  Ce qui a posé problème" -ForegroundColor Red
foreach ($theme in $rapport.top_negatifs) {
    Write-Host ("    - {0,-42} {1} avis ({2} %)" -f $theme.libelle, $theme.occurrences, $theme.part)
}

Write-Host ""
Write-Host "  Ce qui a bien fonctionné" -ForegroundColor Green
foreach ($theme in $rapport.top_positifs) {
    Write-Host ("    - {0,-42} {1} avis ({2} %)" -f $theme.libelle, $theme.occurrences, $theme.part)
}
Write-Host ""
