<#
.SYNOPSIS
Dépose les 28 avis de test dans s3://<bucket>/incoming/, ce qui déclenche
la Lambda d'analyse pour chaque fichier.

.PARAMETER Cadence
Pause en secondes entre deux fichiers. Utile en démonstration filmée pour voir
les invocations arriver une à une dans CloudWatch. 0 = envoi groupé.

.EXAMPLE
.\scripts\charger-avis.ps1 -Cadence 1
#>
param(
    [double]$Cadence = 0,
    [string]$Pile = "nordichome",
    [string]$Region = "eu-west-1"
)

. "$PSScriptRoot\_commun.ps1"

$racine = Split-Path $PSScriptRoot -Parent
$dossier = Join-Path $racine "data\incoming"

if (-not (Test-Path $dossier)) {
    Ecrire-Etape "Génération des fichiers d'avis"
    python (Join-Path $racine "scripts\generer_fichiers_avis.py")
}

$sorties = Obtenir-SortiesPile -Pile $Pile -Region $Region
$bucket = $sorties["BucketAvis"]
$fichiers = Get-ChildItem $dossier -Filter *.txt | Sort-Object Name

Ecrire-Etape "Dépôt de $($fichiers.Count) avis dans s3://$bucket/incoming/"

if ($Cadence -le 0) {
    aws s3 sync $dossier "s3://$bucket/incoming/" --region $Region --exclude "*" --include "*.txt"
    if ($LASTEXITCODE -ne 0) { throw "L'envoi vers S3 a échoué." }
}
else {
    $index = 0
    foreach ($fichier in $fichiers) {
        $index++
        aws s3 cp $fichier.FullName "s3://$bucket/incoming/$($fichier.Name)" --region $Region --only-show-errors
        Write-Host ("   [{0,2}/{1}] {2}" -f $index, $fichiers.Count, $fichier.Name) -ForegroundColor DarkGray
        Start-Sleep -Seconds $Cadence
    }
}

Ecrire-Succes "Dépôt terminé. Les analyses Comprehend s'exécutent en arrière-plan."
Ecrire-Info "Suivi : aws logs tail /aws/lambda/$Pile-traiter-avis --follow --region $Region"
