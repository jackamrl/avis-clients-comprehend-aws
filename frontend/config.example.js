/* Modèle de configuration du tableau de bord.
 *
 * Ne pas modifier ce fichier : `scripts/publier-frontend.ps1` génère
 * automatiquement `config.js` à partir des sorties de la pile CloudFormation.
 * Il est reproduit ici pour documenter les valeurs attendues et permettre un
 * test en local (`python -m http.server` depuis le dossier frontend/).
 */

window.CONFIG_NORDICHOME = {
  region: "eu-west-1",
  clientCognito: "REMPLACER_PAR_ClientPoolUtilisateursId",
  urlApi: "https://REMPLACER.execute-api.eu-west-1.amazonaws.com/v1",
};
