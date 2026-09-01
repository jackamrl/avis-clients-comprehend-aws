# Soutenance : support, vidéo et questions anticipées

---

## 1. Plan du support PowerPoint

14 diapositives pour 12 à 15 minutes. Le fil conducteur tient en une phrase :
**la valeur n'est pas dans l'analyse d'un avis, elle est dans l'agrégation de la
semaine.** Chaque diapositive doit servir ce fil.

### Diapositive 1 — Titre

Analyse automatique de la satisfaction client par agrégation hebdomadaire.
Noms, module, date. Un visuel sobre.

### Diapositive 2 — Le problème, vu du dirigeant

Une PME reçoit quelques dizaines d'avis par semaine. Trop pour les lire tous,
trop peu pour recruter un data scientist. Résultat : ils dorment dans un tableur.

*À dire :* « Un problème de transporteur qui s'installe sur trois semaines passe
inaperçu jusqu'à ce qu'il se voie dans le chiffre d'affaires. »

### Diapositive 3 — Problématique

Afficher la question en toutes lettres, puis souligner les trois exigences :
**automatiquement** / **sur une période donnée** / **identifier ce qui a marché
et ce qui a coincé**.

### Diapositive 4 — Ce que le projet n'est pas

Trois barrés :

- ~~un classifieur de sentiment~~ → c'est un moyen, pas la finalité
- ~~un outil de réponse aux avis~~ → l'objet est le pilotage
- ~~un entraînement de modèle~~ → le ML est consommé comme un service

*C'est la diapositive qui protège de la question « donc vous avez juste appelé
une API de sentiment ? ». Prenez-la de vitesse.*

### Diapositive 5 — Le résultat, avant l'architecture

Montrer l'e-mail hebdomadaire reçu, ou une capture du tableau de bord. Le
livrable d'abord, la mécanique ensuite.

*À dire :* « Voilà ce que le responsable reçoit le lundi matin, sans avoir rien
fait. Tendance mitigée, 46 % de négatifs, motif dominant : les retards de
livraison. »

### Diapositive 6 — Architecture générale

Le schéma de [`architecture.md`](architecture.md), avec les **deux chaînes
visuellement séparées** : temps réel en haut, périodique en bas.

### Diapositive 7 — Chaîne temps réel

S3 → Lambda → Comprehend → DynamoDB. Deux appels par avis :
`detect_sentiment` et `detect_key_phrases`.

*À dire :* « Le résultat de cette chaîne, pris isolément, n'a presque aucune
valeur métier. C'est un état intermédiaire. »

### Diapositive 8 — Chaîne périodique (le cœur)

EventBridge Scheduler → Lambda → statistiques + thèmes → DynamoDB + SES.

**Insister sur la conséquence économique de la séparation :** rejouer
l'agrégation est gratuit, rejouer l'analyse ne l'est pas. Donc on peut faire
évoluer le vocabulaire métier et réinterpréter tout l'historique sans repayer
un seul appel Comprehend.

### Diapositive 9 — Comment on passe des mots aux thèmes

La diapositive la plus technique, et la plus intéressante.

Montrer la transformation :

```
Comprehend renvoie :   « le colis », « la porte cassée », « une charnière arrachée »
Normalisation :        colis, porte cassee, charniere arrachee
Projection :           → thème « Colis et produits endommagés »
```

*À dire :* « Trois formulations, un seul problème métier. Sans cette étape, le
rapport serait une liste plate de cinquante phrases clés, et surtout deux
semaines ne seraient pas comparables entre elles. »

### Diapositive 10 — Une décision de conception à défendre

Le sentiment détecté fait autorité sur la polarité déclarée du thème.

Un avis négatif qui parle de qualité produit fait remonter « Qualité des
produits » **côté négatif**. Ce n'est pas un bug : c'est le signal qu'une force
de l'entreprise se dégrade.

### Diapositive 11 — Choix techniques et justifications

Un tableau court, trois ou quatre lignes maximum :

| Choix | Alternative | Raison |
|---|---|---|
| Index secondaire DynamoDB | `Scan` | le `Scan` lit tout l'historique à chaque exécution |
| HTTP API | REST API | ~70 % moins cher, autoriseur JWT natif |
| EventBridge Scheduler | règle EventBridge | gère les fuseaux et l'heure d'été |
| `eu-west-1` | `eu-west-3` (Paris) | Comprehend n'existe pas à Paris |

### Diapositive 12 — Validation

- 41 tests automatisés
- rappel de 100 % sur les 31 thèmes injectés volontairement
- concordance mesurée entre Comprehend et l'annotation manuelle
- coût réel : quelques dizaines de centimes par mois hors free tier

### Diapositive 13 — Limites, assumées

- le lexique ne comprend pas la négation (« aucun retard » active « retard »)
- 28 avis démontrent le mécanisme, ne mesurent pas une performance
- couplage fort à AWS
- SES en bac à sable

*Énoncer ses limites soi-même vaut mieux que se les faire énoncer.*

### Diapositive 14 — Conclusion

Les trois exigences de la problématique sont satisfaites. La pertinence tient
moins à la sophistication des briques qu'à leur agencement : la séparation entre
analyse unitaire et synthèse périodique est ce qui rend le système économiquement
viable et évolutif.

---

## 2. Déroulé de la vidéo de démonstration

**Durée cible : 5 à 6 minutes.** Enregistrer en 1080p minimum, police du terminal
agrandie à 16 pt ou plus.

### Préparation, avant d'enregistrer

```powershell
# Repartir d'un état propre
aws dynamodb scan --table-name nordichome-Avis --region eu-west-1 `
    --projection-expression "avis_id" --output json > avis-existants.json
# (ou simplement redéployer une pile neuve)

# Vérifier que SES est validé et le dashboard publié
.\scripts\publier-frontend.ps1
```

Préparer trois fenêtres : l'explorateur de fichiers sur `data/incoming/`, un
terminal PowerShell, un navigateur avec la console AWS.

### 0:00 — 0:40 · Le problème

Montrer le dossier des 28 fichiers `.txt`. En ouvrir deux ou trois.

*« Voilà la matière première : du texte libre, écrit par des clients. 28 avis
sur une semaine. Personne ne va lire ça tous les lundis. »*

### 0:40 — 1:30 · L'architecture en 40 secondes

Le schéma à l'écran. Suivre le trajet d'un avis du doigt : S3, Lambda,
Comprehend, DynamoDB. Puis montrer la seconde chaîne.

*« Deux chaînes. L'une analyse chaque avis à l'arrivée. L'autre synthétise la
semaine. C'est la deuxième qui produit la valeur. »*

### 1:30 — 2:30 · Ingestion en direct

```powershell
.\scripts\charger-avis.ps1 -Cadence 1
```

Dans un second terminal, en simultané :

```powershell
aws logs tail /aws/lambda/nordichome-traiter-avis --follow --region eu-west-1
```

Les lignes `avis AV001 traité : POSITIVE (0.99)` défilent.

*« Chaque dépôt déclenche une Lambda. Aucun serveur ne tournait avant, aucun ne
tournera après. »*

### 2:30 — 3:00 · Les données analysées

Console AWS → DynamoDB → table `Avis`. Ouvrir un élément : `sentiment`,
`score_confiance`, `mots_cles`.

*« Le sentiment et les phrases clés viennent de Comprehend. À ce stade, on n'a
encore rien répondu à la question du dirigeant. »*

### 3:00 — 4:00 · L'agrégation

```powershell
.\scripts\lancer-rapport.ps1 -DateFin 2026-08-23
```

Le rapport s'affiche dans la console avec les histogrammes.

*« En production, EventBridge Scheduler déclenche ça tous les lundis à 8h. Ici
je l'invoque à la main pour ne pas attendre. C'est la même charge utile, le même
code. »*

Montrer ensuite la planification :

```powershell
aws scheduler get-schedule --name nordichome-rapport-hebdo --region eu-west-1
```

### 4:00 — 4:40 · L'e-mail

Ouvrir la boîte de réception. Le rapport HTML : pourcentages, tendance, thèmes,
citations.

*« Voilà ce que reçoit le responsable. Il n'a rien installé, rien lancé. »*

### 4:40 — 5:40 · Le tableau de bord

Ouvrir l'URL S3. **Montrer l'écran de connexion Cognito** — insister une seconde
sur le fait que l'accès est restreint. Se connecter.

Parcourir : indicateurs, camembert, volume par jour, les deux colonnes de thèmes
avec leurs citations. Filtrer les avis par sentiment.

*« Le manager peut creuser : derrière « retards de livraison, 6 avis », il y a
les avis eux-mêmes. »*

### 5:40 — 6:00 · Clôture

*« Toute l'infrastructure est décrite dans un fichier de 500 lignes, déployable
en une commande, et coûte quelques centimes par mois. »*

---

## 3. Questions anticipées

### Sur la valeur du projet

**« Vous avez juste appelé une API de sentiment, où est votre travail ? »**

L'appel à Comprehend fait deux lignes. Le travail est ailleurs : dans la
séparation des deux chaînes, dans la normalisation du français, dans la
projection des phrases clés sur un lexique métier, dans le choix de recalculer
les thèmes à l'agrégation plutôt qu'à l'ingestion, et dans le modèle de données
DynamoDB qui évite le `Scan`. Comprehend est un composant, pas le projet.

**« Pourquoi ne pas simplement afficher les phrases clés les plus fréquentes ? »**

Parce que Comprehend renvoie « le colis », « la porte cassée », « une charnière
arrachée » : trois formulations d'un même problème. Un classement direct donne
une liste plate de cinquante entrées, illisible. Surtout, les formulations
changent d'une semaine à l'autre : deux rapports ne seraient pas comparables. Or
la comparabilité est l'objet même du livrable.

**« Pourquoi une agrégation hebdomadaire plutôt qu'un tableau de bord temps réel ? »**

Parce que la question du dirigeant est hebdomadaire. Un tableau de bord temps
réel affiche du bruit : trois avis négatifs un mardi ne signifient rien. La
semaine est le grain auquel une tendance devient interprétable et une décision
possible. Rien n'empêche par ailleurs de consulter le dashboard quand on veut.

### Sur le machine learning

**« Vous n'avez entraîné aucun modèle. Est-ce vraiment un projet ML ? »**

Le ML est consommé comme un service managé, et c'est un choix assumé, directement
issu de la problématique : *sans expertise data science*. Entraîner un CamemBERT
demanderait un corpus annoté de plusieurs milliers d'avis, une infrastructure
d'inférence et une compétence que la PME visée n'a pas. Le travail ML du projet
consiste à choisir le bon service, à en exploiter correctement les deux sorties,
et à mesurer sa concordance avec une annotation de référence.

**« Comment savez-vous que Comprehend ne se trompe pas ? »**

C'est précisément l'objet du champ `sentiment_attendu` du jeu de données : une
annotation manuelle de référence. `scripts/simulation_locale.py --comprehend`
appelle réellement le service et affiche le taux de concordance ainsi que le
détail des désaccords. C'est une mesure, pas une intuition.

**« Pourquoi pas Comprehend Custom Classification ? »**

Cela permettrait de spécialiser un modèle sur le vocabulaire du mobilier, mais
exige un corpus annoté de plusieurs centaines d'avis et un entraînement facturé.
Contradictoire avec l'hypothèse de départ. C'est la bonne piste au-delà de
quelques milliers d'avis par mois.

**« Pourquoi pas du topic modeling non supervisé, LDA par exemple ? »**

Sur 28 avis, LDA produit des groupes instables, sans nom lisible, différents à
chaque exécution. Un manager ne peut rien faire d'un « topic 3 ». Et surtout, les
groupes changeraient d'une semaine à l'autre, ce qui interdit tout suivi de
tendance. Le lexique donne six thèmes stables, nommés et comparables.

### Sur l'architecture

**« Pourquoi serverless plutôt qu'une EC2 avec un cron ? »**

Le profil de charge : quelques dizaines d'avis par semaine, une exécution
hebdomadaire. Une EC2 même minimale est facturée 168 heures par semaine pour
quelques secondes de calcul utile. Avec Lambda, l'absence d'avis coûte
exactement zéro. S'y ajoutent la haute disponibilité multi-AZ et le passage à
l'échelle sans configuration.

**« Pourquoi DynamoDB et pas RDS ? »**

Le schéma d'accès est simple et connu à l'avance : écriture par `avis_id`,
lecture sur une plage de dates. Aucune jointure, aucune requête ad hoc. DynamoDB
en mode à la demande n'a aucune capacité à provisionner et ne facture rien au
repos, là où RDS facture une instance en continu. Sur un accès aussi simple, le
relationnel n'apporte rien.

**« Pourquoi un index secondaire ? Un `Scan` ne suffirait pas pour 28 avis ? »**

Pour 28 avis, si. Mais un `Scan` lit toute la table à chaque exécution : son
coût et sa latence croissent avec l'historique, alors que la fenêtre analysée
reste de sept jours. Au bout de deux ans, l'agrégation lirait plus de 5 000 avis
pour en exploiter 30. L'index rend le coût proportionnel à ce qu'on lit vraiment.

**« Pourquoi partitionner l'index par mois et pas une clé constante ? »**

Une clé constante concentre toutes les écritures sur une seule partition
physique, plafonnée à 1 000 unités d'écriture par seconde. Le seau mensuel
répartit la charge. Le prix à payer est qu'une semaine à cheval sur deux mois
demande deux requêtes au lieu d'une — c'est géré, et explicitement testé.

**« Pourquoi HTTP API plutôt que REST API ? »**

Environ 70 % moins cher, latence plus faible, et surtout un autoriseur JWT natif :
la passerelle valide elle-même la signature, l'émetteur et l'expiration du jeton
Cognito. Aucune Lambda d'autorisation à écrire ni à payer. Les fonctionnalités
manquantes de REST API — plans d'usage, transformations de requêtes — ne sont pas
nécessaires ici.

**« Pourquoi EventBridge Scheduler et pas une règle EventBridge classique ? »**

Le Scheduler gère nativement les fuseaux horaires, y compris le passage à
l'heure d'été. Une règle `cron` classique s'exprime obligatoirement en UTC : le
rapport arriverait à 9h en été et 8h en hiver.

**« Pourquoi eu-west-1 et pas Paris ? »**

Amazon Comprehend n'est pas disponible à Paris (`eu-west-3`). Les régions
européennes qui le proposent sont Irlande, Londres et Francfort. Irlande est la
plus complète et la moins chère. C'est une contrainte de disponibilité de
service, pas une préférence.

**« Votre bucket S3 est public, n'est-ce pas une faille ? »**

Le bucket du **dashboard** est public, celui des **avis** ne l'est pas. Et le
dashboard ne contient aucune donnée : c'est du HTML, du CSS et du JavaScript. Les
données sont derrière l'API, qui exige un jeton Cognito valide. Ce qui est public,
c'est le code de la page, comme n'importe quel site web. En production on
mettrait CloudFront avec Origin Access Control devant, pour avoir HTTPS et un
bucket privé.

**« Que se passe-t-il si Comprehend est indisponible ? »**

L'erreur est propagée, Lambda réessaie automatiquement, et après épuisement des
réessais le message part en file SQS de lettres mortes. Une alarme CloudWatch
surveille cette file et notifie par e-mail. Les avis ne sont jamais perdus : le
fichier reste dans S3 et peut être redéposé.

**« Et si un fichier est mal nommé ? »**

C'est traité différemment, et volontairement. Un nom non conforme est une erreur
définitive : réessayer donnerait le même résultat. Le fichier est journalisé et
ignoré, sans faire échouer le lot ni bloquer les avis valides. Seules les erreurs
transitoires déclenchent des réessais.

### Sur les limites

**« Que se passe-t-il avec la négation ? »**

C'est la limite principale, et on l'assume. « Aucun retard de livraison »
active le motif « retard ». Le filtrage par sentiment limite les dégâts : un
avis positif ne peut pas remonter dans le palmarès négatif. Mais un avis
franchement négatif contenant « pas de retard » serait mal classé. La piste de
correction est `detect_syntax`, qui donnerait les portées de négation, au prix
d'un appel Comprehend supplémentaire par avis.

**« 28 avis, ce n'est pas un peu léger ? »**

Pour démontrer le mécanisme, c'est suffisant et c'était le but : chaque thème est
injecté volontairement avec des formulations variées, ce qui permet de vérifier
que l'agrégation les regroupe. Pour mesurer une performance, non — un rappel
calculé sur 31 occurrences a un intervalle de confiance très large. Nous
présentons le rappel comme une validation fonctionnelle, pas comme une métrique
statistique.

**« Comment passeriez-vous à 100 000 avis par mois ? »**

L'architecture tient sans modification : Lambda parallélise, DynamoDB à la
demande absorbe, l'index par mois évite la partition chaude. Deux ajustements
seraient utiles. D'abord grouper les appels Comprehend avec
`batch_detect_sentiment`, qui traite 25 documents par appel et réduit le coût.
Ensuite basculer l'extraction de thèmes vers Comprehend Topic Modeling, qui
devient pertinent à ce volume. Le poste de coût dominant resterait Comprehend.

**« Combien ça coûte réellement ? »**

Nul pendant le projet grâce au free tier. Au-delà, pour 500 avis par mois :
de l'ordre de quelques dizaines de centimes. Le détail poste par poste est en
section 5 de [`architecture.md`](architecture.md). Le seul poste qui croît
vraiment est Comprehend, facturé par tranche de 100 caractères — d'où l'intérêt
de ne jamais rejouer l'analyse unitaire.

---

## 4. Répartition entre les deux membres du binôme

Une suggestion, à ajuster.

| | Membre A | Membre B |
|---|---|---|
| Support | diapositives 1 à 5, 13, 14 | diapositives 6 à 12 |
| Angle | problématique, valeur métier, limites | architecture, choix techniques, validation |
| Démo | pilote le terminal | commente ce qui se passe |

**Chacun doit pouvoir répondre à toutes les questions.** Les jurys interrogent
souvent celui qui n'a pas présenté la partie concernée.

---

## 5. Vérifications la veille

- [ ] Les identités SES sont vérifiées et un e-mail de test est bien reçu
- [ ] Le compte manager fonctionne, mot de passe définitif défini (ne pas
      découvrir l'écran « nouveau mot de passe » en direct)
- [ ] `python -m pytest tests` : 41 tests au vert
- [ ] `python scripts\simulation_locale.py` fonctionne — **filet de sécurité si
      le réseau tombe pendant la soutenance**
- [ ] La vidéo est enregistrée et lisible hors ligne, au cas où la démo live échoue
- [ ] Le tableau de bord est publié et l'URL fonctionne depuis un autre réseau
- [ ] `budget AWS` : une alerte de facturation est configurée
- [ ] Un jeu d'avis redatés sur la semaine en cours est prêt, si vous voulez
      montrer un déclenchement automatique réel
