<#
.SYNOPSIS
Déroulé complet de la démonstration : dépôt des avis, attente du traitement,
génération du rapport hebdomadaire, ouverture du tableau de bord.

.EXAMPLE
.\scripts\demo.ps1 -Cadence 0.5
#>
param(
    [double]$Cadence = 0.5,
    [string]$DateFin = "2026-08-23",
    [int]$DelaiMaxSecondes = 180,
    [switch]$SansOuvrirNavigateur,
    [string]$Pile = "nordichome",
    [string]$Region = "eu-west-1"
)

. "$PSScriptRoot\_commun.ps1"

$sorties = Obtenir-SortiesPile -Pile $Pile -Region $Region
$tableAvis = $sorties["TableAvis"]

# --------------------------------------------------------------------------
& "$PSScriptRoot\charger-avis.ps1" -Cadence $Cadence -Pile $Pile -Region $Region

# --------------------------------------------------------------------------
Ecrire-Etape "Attente du traitement des avis par Comprehend"

$attendu = (Get-ChildItem (Join-Path (Split-Path $PSScriptRoot -Parent) "data\incoming") -Filter *.txt).Count
$debut = Get-Date
$nombre = 0

while (((Get-Date) - $debut).TotalSeconds -lt $DelaiMaxSecondes) {
    $nombre = aws dynamodb scan --table-name $tableAvis --select COUNT `
        --region $Region --query "Count" --output text
    Write-Host "`r   $nombre / $attendu avis analysés" -NoNewline -ForegroundColor DarkGray
    if ([int]$nombre -ge $attendu) { break }
    Start-Sleep -Seconds 3
}
Write-Host ""

if ([int]$nombre -lt $attendu) {
    Write-Host "   Seuls $nombre avis sur $attendu sont arrivés en base." -ForegroundColor Yellow
    Ecrire-Info "Vérifiez : aws logs tail /aws/lambda/$Pile-traiter-avis --region $Region"
}
else {
    Ecrire-Succes "Les $attendu avis sont analysés et stockés."
}

# --------------------------------------------------------------------------
& "$PSScriptRoot\lancer-rapport.ps1" -DateFin $DateFin -Pile $Pile -Region $Region

# --------------------------------------------------------------------------
Ecrire-Etape "Restitution"
Write-Host "   Tableau de bord : $($sorties['UrlDashboard'])"
Write-Host "   E-mail de synthèse envoyé via SES (vérifiez la boîte du manager)."

if (-not $SansOuvrirNavigateur) {
    Start-Process $sorties["UrlDashboard"]
}
