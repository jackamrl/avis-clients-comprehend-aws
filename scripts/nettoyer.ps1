<#
.SYNOPSIS
Supprime intégralement la pile et les données, pour ne rien laisser tourner
après la soutenance.

.DESCRIPTION
CloudFormation refuse de supprimer un bucket non vide : les deux buckets sont
donc purgés au préalable.
#>
param(
    [string]$Pile = "nordichome",
    [string]$Region = "eu-west-1",
    [switch]$Force
)

. "$PSScriptRoot\_commun.ps1"

if (-not $Force) {
    $reponse = Read-Host "Supprimer la pile '$Pile' dans $Region et toutes ses données ? (oui/non)"
    if ($reponse -ne "oui") { Write-Host "Annulé."; exit 0 }
}

$sorties = Obtenir-SortiesPile -Pile $Pile -Region $Region

foreach ($cle in @("BucketAvis", "BucketSiteWeb")) {
    $bucket = $sorties[$cle]
    if ($bucket) {
        Ecrire-Etape "Purge de s3://$bucket"
        aws s3 rm "s3://$bucket" --recursive --region $Region --only-show-errors
    }
}

Ecrire-Etape "Suppression de la pile $Pile"
if (Get-Command sam -ErrorAction SilentlyContinue) {
    sam delete --stack-name $Pile --region $Region --no-prompts
}
else {
    aws cloudformation delete-stack --stack-name $Pile --region $Region
    aws cloudformation wait stack-delete-complete --stack-name $Pile --region $Region
}

Ecrire-Succes "Pile supprimée."
Ecrire-Info "Les identités SES vérifiées restent dans le compte : supprimez-les depuis la console si besoin."
