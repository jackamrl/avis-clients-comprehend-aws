/* Tableau de bord NordicHome — application statique, sans build ni dépendance.
 *
 * L'authentification interroge directement l'API Cognito Identity Provider en
 * HTTP : une page statique ne peut de toute façon dissimuler aucun secret, et
 * le flux USER_PASSWORD_AUTH tient en deux appels. Le jeton d'identité obtenu
 * est présenté à API Gateway, qui le valide via son autoriseur JWT.
 */

const CONFIG = window.CONFIG_NORDICHOME || {};
const CLE_JETON = "nordichome.idToken";

const $ = (id) => document.getElementById(id);

const etat = {
  jeton: null,
  email: null,
  rapports: [],
  rapportCourant: null,
  filtreSentiment: "",
  graphiques: {},
};

/* ---------------------------------------------------------------------- */
/* Cognito                                                                 */
/* ---------------------------------------------------------------------- */

async function appelCognito(cible, corps) {
  const reponse = await fetch(`https://cognito-idp.${CONFIG.region}.amazonaws.com/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-amz-json-1.1",
      "X-Amz-Target": `AWSCognitoIdentityProviderService.${cible}`,
    },
    body: JSON.stringify(corps),
  });

  const donnees = await reponse.json();
  if (!reponse.ok) {
    throw new Error(traduireErreurCognito(donnees));
  }
  return donnees;
}

function traduireErreurCognito(donnees) {
  const type = (donnees.__type || "").split("#").pop();
  const messages = {
    NotAuthorizedException: "Identifiants incorrects.",
    UserNotFoundException: "Identifiants incorrects.",
    InvalidPasswordException:
      "Mot de passe trop faible : 12 caractères minimum, avec majuscule et chiffre.",
    PasswordResetRequiredException: "Réinitialisation du mot de passe requise.",
    TooManyRequestsException: "Trop de tentatives, patientez un instant.",
    InvalidParameterException: donnees.message || "Paramètre invalide.",
  };
  return messages[type] || donnees.message || "Échec de la connexion.";
}

function decoderJeton(jeton) {
  let charge = jeton.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
  charge += "=".repeat((4 - (charge.length % 4)) % 4);
  const octets = Uint8Array.from(atob(charge), (c) => c.charCodeAt(0));
  return JSON.parse(new TextDecoder("utf-8").decode(octets));
}

function jetonValide(jeton) {
  try {
    return decoderJeton(jeton).exp * 1000 > Date.now() + 30_000;
  } catch {
    return false;
  }
}

async function seConnecter(email, motDePasse, nouveauMotDePasse) {
  let reponse = await appelCognito("InitiateAuth", {
    AuthFlow: "USER_PASSWORD_AUTH",
    ClientId: CONFIG.clientCognito,
    AuthParameters: { USERNAME: email, PASSWORD: motDePasse },
  });

  // Les comptes créés par un administrateur arrivent avec un mot de passe
  // temporaire : Cognito impose de le remplacer avant de délivrer un jeton.
  if (reponse.ChallengeName === "NEW_PASSWORD_REQUIRED") {
    if (!nouveauMotDePasse) {
      const erreur = new Error("Définissez un nouveau mot de passe pour continuer.");
      erreur.nouveauMotDePasseRequis = true;
      throw erreur;
    }
    reponse = await appelCognito("RespondToAuthChallenge", {
      ChallengeName: "NEW_PASSWORD_REQUIRED",
      ClientId: CONFIG.clientCognito,
      Session: reponse.Session,
      ChallengeResponses: { USERNAME: email, NEW_PASSWORD: nouveauMotDePasse },
    });
  }

  if (!reponse.AuthenticationResult) {
    throw new Error("Réponse Cognito inattendue.");
  }
  return reponse.AuthenticationResult.IdToken;
}

/* ---------------------------------------------------------------------- */
/* API                                                                     */
/* ---------------------------------------------------------------------- */

async function appelApi(chemin) {
  const reponse = await fetch(`${CONFIG.urlApi}${chemin}`, {
    headers: { Authorization: `Bearer ${etat.jeton}` },
  });

  if (reponse.status === 401 || reponse.status === 403) {
    deconnecter("Session expirée, reconnectez-vous.");
    throw new Error("non authentifié");
  }
  if (!reponse.ok) {
    throw new Error(`API ${reponse.status}`);
  }
  return reponse.json();
}

/* ---------------------------------------------------------------------- */
/* Rendu                                                                   */
/* ---------------------------------------------------------------------- */

const LIBELLES_TENDANCE = {
  positive: "Tendance positive",
  negative: "Tendance négative",
  mitigee: "Tendance mitigée",
  indeterminee: "Données insuffisantes",
};

function formaterDate(iso) {
  return new Date(`${iso}T12:00:00`).toLocaleDateString("fr-FR", {
    day: "numeric",
    month: "long",
  });
}

function jourCourt(iso) {
  return new Date(`${iso}T12:00:00`).toLocaleDateString("fr-FR", {
    weekday: "short",
    day: "numeric",
  });
}

function afficherRapport(rapport) {
  etat.rapportCourant = rapport;

  $("titre-semaine").textContent = `Semaine ${rapport.semaine_id}`;
  $("sous-titre-semaine").textContent =
    `Du ${formaterDate(rapport.periode_debut)} au ${formaterDate(rapport.periode_fin)}`;

  const badge = $("badge-tendance");
  badge.textContent = LIBELLES_TENDANCE[rapport.tendance] || rapport.tendance;
  badge.className = `badge ${rapport.tendance}`;

  const comparaison = rapport.comparaison_semaine_precedente;
  $("comparaison").textContent = comparaison
    ? `${comparaison.delta_pct_positif >= 0 ? "+" : ""}${comparaison.delta_pct_positif} pts ` +
      `d'avis positifs vs ${comparaison.semaine_id}`
    : "Pas de semaine précédente pour comparer";

  $("kpi-total").textContent = rapport.nb_avis;
  $("kpi-total-detail").textContent =
    `Score de confiance moyen : ${Math.round((rapport.score_confiance_moyen || 0) * 100)} %`;

  const kpis = [
    ["positif", rapport.pct_positif, rapport.nb_positif],
    ["negatif", rapport.pct_negatif, rapport.nb_negatif],
  ];
  kpis.forEach(([cle, pct, nb]) => {
    $(`kpi-${cle}`).textContent = `${pct} %`;
    $(`kpi-${cle}-detail`).textContent = `${nb} avis`;
  });

  const nbNeutres = (rapport.nb_neutre || 0) + (rapport.nb_mixte || 0);
  const pctNeutres = Math.round(((rapport.pct_neutre || 0) + (rapport.pct_mixte || 0)) * 10) / 10;
  $("kpi-neutre").textContent = `${pctNeutres} %`;
  $("kpi-neutre-detail").textContent = `${nbNeutres} avis`;

  dessinerRepartition(rapport);
  dessinerVolume(rapport);
  dessinerEvolution();

  afficherThemes("themes-negatifs", rapport.top_negatifs, "rouge");
  afficherThemes("themes-positifs", rapport.top_positifs, "verte");

  chargerAvis();
}

function afficherThemes(idConteneur, themes, couleur) {
  const conteneur = $(idConteneur);
  conteneur.innerHTML = "";

  if (!themes || themes.length === 0) {
    conteneur.innerHTML =
      "<p class='vide'>Aucun thème récurrent identifié sur cette période.</p>";
    return;
  }

  const maximum = Math.max(...themes.map((t) => t.occurrences));

  themes.forEach((theme) => {
    const bloc = document.createElement("div");
    bloc.className = "theme";

    const citations = (theme.exemples || [])
      .map((e) => `<p class="citation">« ${echapper(e.extrait)} »</p>`)
      .join("");

    bloc.innerHTML = `
      <div class="theme-entete">
        <span class="theme-titre">${echapper(theme.libelle)}</span>
        <span class="theme-compte">${theme.occurrences} avis · ${theme.part} %</span>
      </div>
      <div class="jauge ${couleur}">
        <span style="width:${Math.round((theme.occurrences / maximum) * 100)}%"></span>
      </div>
      ${citations}`;
    conteneur.appendChild(bloc);
  });
}

function echapper(valeur) {
  const noeud = document.createElement("div");
  noeud.textContent = valeur ?? "";
  return noeud.innerHTML;
}

/* ---------------------------------------------------------------------- */
/* Graphiques                                                              */
/* ---------------------------------------------------------------------- */

Chart.defaults.font.family = "Inter, sans-serif";
Chart.defaults.color = "#6b7280";

function remplacerGraphique(cle, canvasId, configuration) {
  etat.graphiques[cle]?.destroy();
  etat.graphiques[cle] = new Chart($(canvasId), configuration);
}

function dessinerRepartition(rapport) {
  remplacerGraphique("repartition", "graphique-repartition", {
    type: "doughnut",
    data: {
      labels: ["Positifs", "Négatifs", "Neutres", "Mitigés"],
      datasets: [{
        data: [rapport.nb_positif, rapport.nb_negatif, rapport.nb_neutre, rapport.nb_mixte],
        backgroundColor: ["#15a34a", "#dc2626", "#94a3b8", "#f59e0b"],
        borderWidth: 0,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "62%",
      plugins: { legend: { position: "right", labels: { boxWidth: 10, padding: 14 } } },
    },
  });
}

function dessinerVolume(rapport) {
  const jours = rapport.volume_par_jour || [];
  remplacerGraphique("volume", "graphique-volume", {
    type: "bar",
    data: {
      labels: jours.map((j) => jourCourt(j.date)),
      datasets: [{
        data: jours.map((j) => j.nb_avis),
        backgroundColor: "#111827",
        borderRadius: 5,
        maxBarThickness: 34,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: "#f1f2f4" } },
        x: { grid: { display: false } },
      },
    },
  });
}

function dessinerEvolution() {
  // Les rapports arrivent du plus récent au plus ancien : on inverse pour lire
  // la courbe dans le sens du temps.
  const series = [...etat.rapports].reverse();
  remplacerGraphique("evolution", "graphique-evolution", {
    type: "line",
    data: {
      labels: series.map((r) => r.semaine_id),
      datasets: [
        {
          label: "% positifs",
          data: series.map((r) => r.pct_positif),
          borderColor: "#15a34a",
          backgroundColor: "rgba(21,163,74,.08)",
          fill: true,
          tension: .35,
        },
        {
          label: "% négatifs",
          data: series.map((r) => r.pct_negatif),
          borderColor: "#dc2626",
          backgroundColor: "rgba(220,38,38,.06)",
          fill: true,
          tension: .35,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: "bottom", labels: { boxWidth: 10, padding: 14 } } },
      scales: {
        y: { beginAtZero: true, max: 100, grid: { color: "#f1f2f4" } },
        x: { grid: { display: false } },
      },
    },
  });
}

/* ---------------------------------------------------------------------- */
/* Avis unitaires                                                          */
/* ---------------------------------------------------------------------- */

async function chargerAvis() {
  const rapport = etat.rapportCourant;
  const conteneur = $("liste-avis");
  conteneur.innerHTML = "<p class='vide'>Chargement…</p>";

  const parametres = new URLSearchParams({
    debut: rapport.periode_debut,
    fin: rapport.periode_fin,
  });
  if (etat.filtreSentiment) parametres.set("sentiment", etat.filtreSentiment);

  try {
    const donnees = await appelApi(`/avis?${parametres}`);
    conteneur.innerHTML = "";

    if (donnees.nb === 0) {
      conteneur.innerHTML = "<p class='vide'>Aucun avis pour ce filtre.</p>";
      return;
    }

    donnees.avis.forEach((avis) => {
      const ligne = document.createElement("article");
      ligne.className = "avis";
      const mots = (avis.mots_cles || [])
        .slice(0, 6)
        .map((m) => `<span class="mot">${echapper(m)}</span>`)
        .join("");

      ligne.innerHTML = `
        <div class="avis-meta">
          <strong>${echapper(avis.avis_id)}</strong>
          ${formaterDate(avis.date)}<br>${echapper(avis.client_id)}
        </div>
        <div>
          <p class="avis-texte">${echapper(avis.texte)}</p>
          <div class="avis-mots">${mots}</div>
        </div>
        <span class="etiquette ${echapper(avis.sentiment)}">
          ${echapper(avis.sentiment)} · ${Math.round((avis.score_confiance || 0) * 100)} %
        </span>`;
      conteneur.appendChild(ligne);
    });
  } catch (erreur) {
    conteneur.innerHTML = `<p class='erreur'>Impossible de charger les avis : ${echapper(erreur.message)}</p>`;
  }
}

/* ---------------------------------------------------------------------- */
/* Orchestration                                                           */
/* ---------------------------------------------------------------------- */

async function chargerTableauDeBord() {
  const donnees = await appelApi("/rapports?limite=12");
  etat.rapports = donnees.rapports || [];

  const selecteur = $("selecteur-semaine");
  selecteur.innerHTML = "";

  if (etat.rapports.length === 0) {
    $("bandeau-vide").classList.remove("masque");
    return;
  }
  $("bandeau-vide").classList.add("masque");

  etat.rapports.forEach((rapport) => {
    const option = document.createElement("option");
    option.value = rapport.semaine_id;
    option.textContent = `Semaine ${rapport.semaine_id} (${rapport.nb_avis} avis)`;
    selecteur.appendChild(option);
  });

  afficherRapport(etat.rapports[0]);
}

function ouvrirApplication(jeton) {
  etat.jeton = jeton;
  etat.email = decoderJeton(jeton).email || "";
  sessionStorage.setItem(CLE_JETON, jeton);

  $("ecran-connexion").classList.add("masque");
  $("application").classList.remove("masque");
  $("utilisateur-connecte").textContent = etat.email;

  chargerTableauDeBord().catch((erreur) => {
    $("bandeau-vide").textContent = `Erreur de chargement : ${erreur.message}`;
    $("bandeau-vide").classList.remove("masque");
  });
}

function deconnecter(message) {
  sessionStorage.removeItem(CLE_JETON);
  etat.jeton = null;
  $("application").classList.add("masque");
  $("ecran-connexion").classList.remove("masque");
  if (message) {
    $("erreur-connexion").textContent = message;
    $("erreur-connexion").classList.remove("masque");
  }
}

/* ---------------------------------------------------------------------- */
/* Événements                                                              */
/* ---------------------------------------------------------------------- */

$("formulaire-connexion").addEventListener("submit", async (evenement) => {
  evenement.preventDefault();
  const bouton = $("bouton-connexion");
  const erreur = $("erreur-connexion");

  erreur.classList.add("masque");
  bouton.disabled = true;
  bouton.textContent = "Connexion…";

  try {
    const jeton = await seConnecter(
      $("champ-email").value.trim(),
      $("champ-motdepasse").value,
      $("champ-nouveau-motdepasse").value || null,
    );
    ouvrirApplication(jeton);
  } catch (souci) {
    if (souci.nouveauMotDePasseRequis) {
      $("bloc-nouveau-motdepasse").classList.remove("masque");
      $("champ-nouveau-motdepasse").focus();
    }
    erreur.textContent = souci.message;
    erreur.classList.remove("masque");
  } finally {
    bouton.disabled = false;
    bouton.textContent = "Se connecter";
  }
});

$("selecteur-semaine").addEventListener("change", (evenement) => {
  const rapport = etat.rapports.find((r) => r.semaine_id === evenement.target.value);
  if (rapport) afficherRapport(rapport);
});

$("bouton-deconnexion").addEventListener("click", () => deconnecter());

$("filtres-sentiment").addEventListener("click", (evenement) => {
  const bouton = evenement.target.closest(".filtre");
  if (!bouton) return;
  document.querySelectorAll(".filtre").forEach((b) => b.classList.remove("actif"));
  bouton.classList.add("actif");
  etat.filtreSentiment = bouton.dataset.sentiment;
  chargerAvis();
});

/* ---------------------------------------------------------------------- */
/* Démarrage                                                               */
/* ---------------------------------------------------------------------- */

(function demarrer() {
  if (!CONFIG.urlApi || !CONFIG.clientCognito) {
    $("erreur-connexion").textContent =
      "config.js absent ou incomplet. Lancez scripts/publier-frontend.ps1 après le déploiement.";
    $("erreur-connexion").classList.remove("masque");
    return;
  }

  const jetonMemorise = sessionStorage.getItem(CLE_JETON);
  if (jetonMemorise && jetonValide(jetonMemorise)) {
    ouvrirApplication(jetonMemorise);
  }
})();
