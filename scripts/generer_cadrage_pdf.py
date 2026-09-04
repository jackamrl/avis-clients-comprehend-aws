"""Génère le document de cadrage PDF (6 pages A4 maximum)."""

from __future__ import annotations

from pathlib import Path

from reportlab.lib.colors import Color, HexColor, white
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.platypus import (
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

RACINE = Path(__file__).resolve().parents[1]
SORTIE = RACINE / "docs" / "cadrage.pdf"
IMG_TR = RACINE / "docs" / "architecture-temps-reel.png"
IMG_PER = RACINE / "docs" / "architecture-periodique.png"

INK = HexColor("#1A1D23")
MUTED = HexColor("#5C6570")
LINE = HexColor("#C9CFD6")
FILL = HexColor("#F6F7F9")
ACCENT = HexColor("#C45C12")
BLUE = HexColor("#2B4FA8")
TEAL = HexColor("#1F6F64")

FONTS = Path(r"C:\Windows\Fonts")
pdfmetrics.registerFont(TTFont("Segoe", str(FONTS / "segoeui.ttf")))
pdfmetrics.registerFont(TTFont("Segoe-Bold", str(FONTS / "segoeuib.ttf")))
pdfmetrics.registerFont(TTFont("Segoe-Italic", str(FONTS / "segoeuii.ttf")))


def styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    s = {
        "kicker": ParagraphStyle(
            "kicker",
            parent=base["Normal"],
            fontName="Segoe-Bold",
            fontSize=8,
            textColor=ACCENT,
            spaceAfter=2 * mm,
        ),
        "title": ParagraphStyle(
            "title",
            parent=base["Normal"],
            fontName="Segoe-Bold",
            fontSize=16.5,
            leading=21,
            textColor=INK,
            spaceAfter=3 * mm,
        ),
        "meta": ParagraphStyle(
            "meta",
            parent=base["Normal"],
            fontName="Segoe",
            fontSize=8.5,
            leading=12,
            textColor=MUTED,
            spaceAfter=4 * mm,
        ),
        "h1": ParagraphStyle(
            "h1",
            parent=base["Normal"],
            fontName="Segoe-Bold",
            fontSize=11.5,
            leading=15,
            textColor=INK,
            spaceBefore=3.2 * mm,
            spaceAfter=2.2 * mm,
        ),
        "h2": ParagraphStyle(
            "h2",
            parent=base["Normal"],
            fontName="Segoe-Bold",
            fontSize=10,
            leading=13,
            textColor=BLUE,
            spaceBefore=2.4 * mm,
            spaceAfter=1.6 * mm,
        ),
        "body": ParagraphStyle(
            "body",
            parent=base["Normal"],
            fontName="Segoe",
            fontSize=9,
            leading=12.2,
            textColor=INK,
            alignment=TA_JUSTIFY,
            spaceAfter=2.1 * mm,
        ),
        "quote": ParagraphStyle(
            "quote",
            parent=base["Normal"],
            fontName="Segoe-Italic",
            fontSize=9.5,
            leading=13,
            textColor=INK,
            leftIndent=3 * mm,
            rightIndent=2 * mm,
            spaceBefore=1 * mm,
            spaceAfter=2.4 * mm,
        ),
        "caption": ParagraphStyle(
            "caption",
            parent=base["Normal"],
            fontName="Segoe-Italic",
            fontSize=7.5,
            leading=10,
            textColor=MUTED,
            spaceBefore=0.8 * mm,
            spaceAfter=2.5 * mm,
        ),
        "cell": ParagraphStyle(
            "cell",
            parent=base["Normal"],
            fontName="Segoe",
            fontSize=7.6,
            leading=10,
            textColor=INK,
        ),
        "cellb": ParagraphStyle(
            "cellb",
            parent=base["Normal"],
            fontName="Segoe-Bold",
            fontSize=7.6,
            leading=10,
            textColor=INK,
        ),
        "th": ParagraphStyle(
            "th",
            parent=base["Normal"],
            fontName="Segoe-Bold",
            fontSize=7.4,
            leading=10,
            textColor=white,
        ),
        "bullet": ParagraphStyle(
            "bullet",
            parent=base["Normal"],
            fontName="Segoe",
            fontSize=9,
            leading=12,
            textColor=INK,
            leftIndent=2 * mm,
        ),
        "footer": ParagraphStyle(
            "footer",
            parent=base["Normal"],
            fontName="Segoe",
            fontSize=7.5,
            textColor=MUTED,
        ),
    }
    return s


def P(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text, style)


def table(headers: list[str], rows: list[list], col_widths: list[float], s: dict) -> Table:
    data = [[P(h, s["th"]) for h in headers]]
    for row in rows:
        data.append([P(c, s["cell"] if i else s["cellb"]) for i, c in enumerate(row)])
    t = Table(data, colWidths=col_widths, repeatRows=1)
    cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), INK),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3.2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3.2),
        ("TOPPADDING", (0, 0), (-1, -1), 2.6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.6),
        ("GRID", (0, 0), (-1, -1), 0.3, LINE),
        ("BACKGROUND", (0, 1), (-1, -1), white),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            cmds.append(("BACKGROUND", (0, i), (-1, i), FILL))
    t.setStyle(TableStyle(cmds))
    return t


def barre(couleur: Color, texte: str, s: dict) -> Table:
    inner = P(texte, s["body"])
    t = Table([["", inner]], colWidths=[2.4 * mm, 172.6 * mm])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), couleur),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (1, 0), (1, 0), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                ("BACKGROUND", (1, 0), (1, 0), FILL),
            ]
        )
    )
    return t


def schema(path: Path, caption: str, s: dict, height_mm: float = 58) -> list:
    w = 175 * mm
    h = height_mm * mm
    img = Image(str(path), width=w, height=h, kind="proportional")
    img.hAlign = "CENTER"
    return [img, P(caption, s["caption"])]


class NumberedCanvas(pdfcanvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states: list[dict] = []

    def showPage(self) -> None:
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        total = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._bandeau(total)
            super().showPage()
        super().save()

    def _bandeau(self, total: int) -> None:
        w, h = A4
        self.setFillColor(ACCENT)
        self.rect(0, h - 3.2 * mm, w, 3.2 * mm, fill=1, stroke=0)
        self.setFillColor(MUTED)
        self.setFont("Segoe", 7.5)
        self.drawString(18 * mm, 10 * mm, "NordicHome  ·  Document de cadrage")
        self.drawRightString(w - 16 * mm, 10 * mm, f"{self._pageNumber} / {total}")
        self.setStrokeColor(LINE)
        self.setLineWidth(0.4)
        self.line(18 * mm, 13.5 * mm, w - 16 * mm, 13.5 * mm)


def build() -> None:
    s = styles()
    story = []

    story.append(P("DOCUMENT DE CADRAGE  ·  MODULE CLOUD AVANCÉ AVEC APPRENTISSAGE AUTOMATIQUE", s["kicker"]))
    story.append(
        P(
            "Analyse automatique de la satisfaction client<br/>par agrégation hebdomadaire d’avis textuels",
            s["title"],
        )
    )
    story.append(
        P(
            "Cas d’étude : <b>NordicHome</b>, e-commerce de mobilier (entreprise fictive). "
            "Architecture AWS serverless, région <b>eu-west-1</b>. "
            "Infrastructure : AWS SAM (<font face='Courier'>template.yaml</font>).",
            s["meta"],
        )
    )

    # --- 1 Contexte ---
    story.append(P("1. Analyse du contexte", s["h1"]))
    story.append(
        P(
            "Une PME du commerce en ligne reçoit des avis en continu : formulaires après-achat, "
            "marketplaces, tickets de support. Quelques dizaines par semaine, quelques centaines "
            "par mois. Volume trop élevé pour être lu intégralement, trop faible pour justifier "
            "un data scientist ou une plateforme d’analyse spécialisée. Les avis finissent dans "
            "un tableur. On les consulte quand un client se plaint fort, ou au bilan trimestriel. "
            "Un problème de transporteur qui s’installe sur trois semaines peut passer inaperçu "
            "jusqu’à se lire dans le chiffre d’affaires.",
            s["body"],
        )
    )
    story.append(
        P(
            "<b>Constat 1 — un avis isolé a peu de valeur.</b> Savoir qu’un client est mécontent "
            "permet au mieux de traiter son cas. Savoir que 46&nbsp;% des avis de la semaine sont "
            "négatifs et que le motif dominant est le retard de livraison, c’est une information "
            "actionnable : appeler le transporteur, renforcer une équipe, ajuster les délais.",
            s["body"],
        )
    )
    story.append(
        P(
            "<b>Constat 2 — le coût d’entrée dans l’analyse de texte a chuté.</b> Un service managé "
            "comme Amazon Comprehend fournit sentiment et phrases clés par appel d’API, sans modèle "
            "à entraîner, sans corpus annoté, sans GPU. Ce qui était un projet de plusieurs mois "
            "est devenu une brique d’infrastructure.",
            s["body"],
        )
    )

    # --- 2 Problématique ---
    story.append(P("2. Problématique", s["h1"]))
    story.append(
        P(
            "Comment une PME sans data scientist ni infrastructure dédiée peut-elle savoir, "
            "chaque semaine, si ses clients ont été satisfaits — et pourquoi ?",
            s["quote"],
        )
    )
    story.append(
        P(
            "Trois exigences structurent le projet. <b>Automatiquement</b> : aucune intervention "
            "entre l’arrivée d’un avis et la synthèse. <b>Sur une période</b> : le livrable n’est "
            "pas l’avis unitaire, c’est « comment s’est passée la semaine ? ». <b>Identifier les "
            "causes</b> : palmarès des thèmes récurrents, séparément pour le positif et le négatif. "
            "Un pourcentage dit qu’il y a un problème ; il ne dit pas lequel.",
            s["body"],
        )
    )
    story.append(
        P(
            "Le projet n’est <b>pas</b> un classifieur de sentiment (moyen, pas fin), <b>pas</b> un "
            "outil de réponse au client (pilotage, pas relation individuelle), <b>pas</b> un "
            "entraînement de modèle. Le ML est consommé comme un service ; le travail original "
            "est l’agrégation périodique.",
            s["body"],
        )
    )

    # --- 3 Réponse ---
    story.append(P("3. Réponse apportée : deux chaînes distinctes", s["h1"]))
    story.append(
        P(
            "Chaîne entièrement serverless sur AWS, organisée en deux traitements de nature "
            "différente. Les confondre est l’erreur classique sur ce type de sujet.",
            s["body"],
        )
    )
    story.append(
        P(
            "<b>Temps réel — analyser.</b> Chaque fichier déposé sous <font face='Courier'>incoming/</font> "
            "déclenche la Lambda <font face='Courier'>traiter-avis</font>. Deux appels Comprehend "
            "(<font face='Courier'>detect_sentiment</font>, <font face='Courier'>detect_key_phrases</font>), "
            "puis écriture dans DynamoDB Avis. Résultat unitaire : un état intermédiaire, presque "
            "sans valeur métier pris isolément.",
            s["body"],
        )
    )
    story.append(
        P(
            "<b>Périodique — synthétiser.</b> Chaque lundi à 08h00 (Europe/Paris), "
            "<font face='Courier'>generer-rapport-hebdo</font> relit les sept jours écoulés et "
            "produit proportions, tendance, volume quotidien, comparaison à la semaine précédente, "
            "et surtout le palmarès des thèmes, illustré d’extraits d’avis. Le rapport est persisté "
            "puis envoyé par e-mail (SES).",
            s["body"],
        )
    )
    story.append(
        barre(
            ACCENT,
            "<b>Pourquoi séparer.</b> Le rejeu de l’agrégation est quasi gratuit (lectures DynamoDB) ; "
            "celui de l’analyse ne l’est pas (Comprehend facturé à l’appel). Les thèmes sont donc "
            "détectés à l’agrégation, pas à l’ingestion. On change une expression régulière, on "
            "relance la Lambda hebdomadaire, et tout l’historique est réinterprété sans un seul "
            "nouvel appel ML.",
            s,
        )
    )
    story.append(Spacer(1, 2.2 * mm))
    story.append(
        table(
            ["", "Chaîne temps réel", "Chaîne périodique"],
            [
                ["Déclencheur", "S3 ObjectCreated sur incoming/*.txt", "EventBridge Scheduler, lundi 08h00"],
                ["Fréquence", "À chaque avis", "Une fois par semaine"],
                ["Coût dominant", "Appels Comprehend", "Lectures DynamoDB (négligeables)"],
                ["Rejouable ?", "Non (nouvel appel facturé)", "Oui, gratuitement"],
                ["Livrable", "Avis analysé (état intermédiaire)", "Synthèse actionnable"],
            ],
            [32 * mm, 71.5 * mm, 71.5 * mm],
            s,
        )
    )

    # --- 4 Architecture ---
    story.append(P("4. Architecture détaillée", s["h1"]))
    story.append(
        P(
            "Région unique <b>eu-west-1</b> (Irlande) : Comprehend n’est pas disponible à Paris. "
            "Runtime Python 3.12 sur arm64 (Graviton). Aucune dépendance tierce : boto3 est fourni "
            "par Lambda ; la logique métier vit dans la couche partagée <font face='Courier'>nordichome</font>, "
            "testable hors ligne. IAM au plus juste : la Lambda d’ingestion n’a qu’un droit "
            "d’écriture sur Avis.",
            s["body"],
        )
    )
    story.append(
        table(
            ["Étape", "Service", "Rôle"],
            [
                ["Dépôt", "S3 (incoming/)", "Réception des avis bruts .txt ; cycle de vie 90 jours"],
                ["Analyse", "Lambda traiter-avis", "Orchestration S3 → Comprehend → DynamoDB"],
                ["ML", "Amazon Comprehend", "Sentiment + phrases clés, français natif"],
                ["Stockage unitaire", "DynamoDB Avis", "PK avis_id ; GSI avis-par-mois (mois, date)"],
                ["File d’échec", "SQS DLQ", "Uniquement après épuisement des réessais Lambda"],
                ["Planification", "EventBridge Scheduler", "cron(0 8 ? * MON *), fuseau Paris"],
                ["Agrégation", "Lambda generer-rapport-hebdo", "Stats, thèmes, comparaison N-1"],
                ["Stockage synthèse", "DynamoDB Rapports", "PK semaine_id (ISO) ; GSI par date"],
                ["Notification", "SES", "E-mail HTML + texte ; échec SES ≠ échec rapport"],
                ["API", "HTTP API + JWT Cognito", "GET /rapports, GET /avis ; anonyme = 0 invocation"],
                ["Interface", "S3 site statique", "Dashboard ; les données restent derrière l’API"],
                ["Supervision", "CloudWatch + SNS", "3 alarmes e-mail vers le manager"],
            ],
            [36 * mm, 48 * mm, 91 * mm],
            s,
        )
    )

    story.append(P("4.1 Chaîne temps réel", s["h2"]))
    story.extend(
        schema(
            IMG_TR,
            "Figure 1 — Chaîne temps réel. Le chemin SQS est un chemin d’échec, pas le flux métier.",
            s,
            62,
        )
    )
    story.append(
        P(
            "Convention de fichier : <font face='Courier'>AV001_2026-08-17_CLI-1042.txt</font> "
            "(avis_id, date, client_id). Le corps est du texte brut : n’importe quel système amont "
            "peut alimenter le pipeline. Le filtre S3 (préfixe + suffixe) est posé côté événement : "
            "une Lambda non invoquée coûte zéro.",
            s["body"],
        )
    )
    story.append(
        P(
            "<b>Erreurs à deux vitesses.</b> Définitive (nom invalide, fichier vide) : journalisée "
            "et ignorée — réessayer donnerait le même résultat. Transitoire (throttling Comprehend, "
            "indisponibilité DynamoDB) : l’exception remonte, Lambda réessaie (invocation asynchrone "
            "S3, 2 retries), puis l’événement bascule en DLQ. CloudWatch alarme si ≥ 1 erreur Lambda "
            "ou ≥ 1 message visible en file, sur 5 minutes ; SNS notifie le manager. "
            "<font face='Courier'>TreatMissingData: notBreaching</font> : l’absence d’invocation n’est pas un incident.",
            s["body"],
        )
    )
    story.append(
        P(
            "L’écriture DynamoDB est un <font face='Courier'>PutItem</font> idempotent sur "
            "<font face='Courier'>avis_id</font> : re-déposer le même fichier écrase l’analyse "
            "précédente au lieu de créer un doublon. La Lambda ne lit pas la table Avis.",
            s["body"],
        )
    )

    story.append(P("4.2 Chaîne périodique", s["h2"]))
    story.extend(
        schema(
            IMG_PER,
            "Figure 2 — Chaîne périodique. Query sur l’index mensuel, jamais de Scan de la table.",
            s,
            62,
        )
    )
    story.append(
        P(
            "EventBridge <b>Scheduler</b> (pas une règle classique) pour gérer le fuseau Paris, "
            "y compris l’heure d’été. Charge utile identique à une invocation manuelle de démo : "
            "<font face='Courier'>{« jours »: 7, « envoyer_email »: true}</font>. Trois étapes : "
            "(1) collecte des 7 jours s’arrêtant la veille, via le GSI <font face='Courier'>avis-par-mois</font> "
            "(une semaine traverse au plus deux mois) ; (2) statistiques et tendance "
            "(<font face='Courier'>positive</font> / <font face='Courier'>negative</font> / "
            "<font face='Courier'>mitigee</font> si l’écart dépasse 15 points) ; (3) projection "
            "sur six thèmes stables, puis persistance + e-mail.",
            s["body"],
        )
    )
    story.append(
        P(
            "<b>Modèle de données.</b> Table Avis : partition mensuelle pour éviter la partition "
            "chaude d’une clé constante (plafond 1&nbsp;000 WCU/s) tout en bornant le Query. "
            "Table Rapports : PK <font face='Courier'>semaine_id</font> (ex. 2026-W34) ; GSI "
            "<font face='Courier'>rapports-par-date</font> pour le listing du dashboard, 52 écritures "
            "par an. Facturation à la demande : le flux d’avis est trop irrégulier pour du provisionné.",
            s["body"],
        )
    )

    story.append(P("4.3 Restitution et observabilité", s["h2"]))
    story.append(
        P(
            "HTTP API (~70&nbsp;% moins chère qu’une REST API) avec autoriseur JWT natif Cognito : "
            "une requête non authentifiée n’atteint jamais la Lambda. Le front présente l’"
            "<b>ID token</b> (seul à porter <font face='Courier'>aud</font>). Pool "
            "<font face='Courier'>AllowAdminCreateUserOnly</font> : pas d’auto-inscription. "
            "Le bucket dashboard est public (code de la page) ; les données passent exclusivement "
            "par l’API. En production : CloudFront + OAC, bucket privé, HTTPS.",
            s["body"],
        )
    )

    # --- 5 Thèmes ---
    story.append(P("5. Des mots aux thèmes — le cœur métier", s["h1"]))
    story.append(
        P(
            "Comprehend extrait « le colis », « la porte cassée », « une charnière arrachée » : "
            "trois formulations d’un même problème. Un classement brut serait illisible et "
            "<b>incomparable d’une semaine à l’autre</b>. Le traitement se fait en deux temps : "
            "normalisation française (<font face='Courier'>nordichome.texte</font> : minuscules, "
            "accents, apostrophe, déterminants) puis projection sur un lexique de six thèmes "
            "(<font face='Courier'>nordichome.themes</font>).",
            s["body"],
        )
    )
    story.append(
        table(
            ["Thèmes à polarité attendue négative", "Thèmes à polarité attendue positive"],
            [
                ["Retards de livraison", "Accueil en boutique"],
                ["Colis et produits endommagés", "Réactivité du service client"],
                ["SAV difficile à joindre", "Qualité des produits"],
            ],
            [87.5 * mm, 87.5 * mm],
            s,
        )
    )
    story.append(Spacer(1, 1.6 * mm))
    story.append(
        P(
            "La polarité « attendue » ne sert qu’à l’affichage. Le rangement dans le palmarès "
            "suit exclusivement le sentiment Comprehend de l’avis. Un avis négatif sur la qualité "
            "produit fait remonter ce thème côté négatif : c’est le signal qu’une force se dégrade. "
            "NEUTRAL et MIXED comptent dans le volume, pas dans les palmarès. Comportement verrouillé par test.",
            s["body"],
        )
    )

    # --- 6 Données ---
    story.append(P("6. Jeu de données et validation", s["h1"]))
    story.append(
        P(
            "28 avis synthétiques en français, lundi 17 au dimanche 23 août 2026 (semaine ISO "
            "2026-W34), quatre par jour. Polarité annotée : 13 négatifs (46&nbsp;%), 11 positifs "
            "(39&nbsp;%), 3 neutres, 1 mitigé — semaine dégradée mais non catastrophique, pour "
            "forcer la lecture des thèmes. Le champ <font face='Courier'>themes_attendus</font> "
            "n’est jamais envoyé à AWS.",
            s["body"],
        )
    )
    story.append(
        P(
            "Simulation hors ligne : 31 thèmes injectés, 31 retrouvés (rappel 100&nbsp;%), "
            "2 détections supplémentaires sur un avis neutre (sans effet sur le palmarès). "
            "41 tests automatisés (normalisation, lexique, fenêtre à cheval sur deux mois, "
            "tendance, corpus vide, nommage, troncature UTF-8 Comprehend).",
            s["body"],
        )
    )

    # --- 7 Pertinence ---
    story.append(P("7. Pertinence, coût et alternatives", s["h1"]))
    story.append(
        P(
            "Le serverless colle au profil de charge : quelques dizaines d’avis par semaine, "
            "une exécution lundi matin, une poignée de consultations. Un serveur, même petit, "
            "serait facturé 168 heures pour quelques secondes utiles. Ici, l’absence d’avis "
            "coûte zéro. Le ML managé lève la barrière « sans expertise data ». Passer de 30 à "
            "3&nbsp;000 avis/semaine ne demande aucun changement d’architecture.",
            s["body"],
        )
    )
    story.append(
        table(
            ["Service", "Volume / mois (500 avis)", "Free tier", "Coût estimé"],
            [
                ["Comprehend", "1 000 unités (2 appels × 500)", "50 000 / mois × 12 mois", "0 € puis ~0,25 €"],
                ["Lambda", "~600 invocations", "1 M / mois, à vie", "0 €"],
                ["DynamoDB on-demand", "~1 500 W + 3 000 R", "25 Go stockage", "&lt; 0,01 €"],
                ["S3, HTTP API, Cognito, SES, Scheduler, Logs", "usage de démo", "largement couvert", "0 €"],
            ],
            [42 * mm, 52 * mm, 46 * mm, 35 * mm],
            s,
        )
    )
    story.append(Spacer(1, 1.4 * mm))
    story.append(
        P(
            "Total : nul pendant le projet, quelques dizaines de centimes ensuite. Le poste "
            "dominant à grande échelle est Comprehend — d’où l’intérêt de ne jamais rejouer "
            "l’analyse unitaire.",
            s["body"],
        )
    )
    story.append(
        P(
            "<b>Alternatives écartées.</b> BERT / CamemBERT : corpus et infra d’inférence, "
            "contredit « sans expertise data ». LDA / clustering : groupes instables, non nommés, "
            "incomparables d’une semaine à l’autre. Topic Modeling Comprehend : conçu pour de gros "
            "lots. QuickSight : facturé par utilisateur. ECS Fargate : facturé à la durée, sans "
            "intérêt pour quelques secondes par semaine.",
            s["body"],
        )
    )

    # --- 8 Périmètre ---
    story.append(P("8. Périmètre, organisation du code et limites", s["h1"]))
    story.append(
        table(
            ["Dans le périmètre", "Hors périmètre"],
            [
                [
                    "Ingestion d’avis texte, analyse de sentiment, thèmes hebdo, e-mail, dashboard manager",
                    "Réponse automatique au client, modération, scoring individuel CRM",
                ],
                [
                    "Authentification managers (Cognito, comptes créés par un admin)",
                    "Auto-inscription, multi-tenant, multi-langue",
                ],
                [
                    "Supervision (logs 14 jours, 3 alarmes SNS)",
                    "Détection d’anomalie temps réel, CloudFront / certificat (écarté pour le bac à sable)",
                ],
            ],
            [87.5 * mm, 87.5 * mm],
            s,
        )
    )
    story.append(Spacer(1, 2 * mm))
    story.append(
        P(
            "<b>Couche partagée.</b> <font face='Courier'>nordichome.texte</font>, "
            "<font face='Courier'>.themes</font>, <font face='Courier'>.fichiers</font> et "
            "<font face='Courier'>.agregation</font> sont montés en Lambda Layer "
            "(<font face='Courier'>/opt/python</font>). L’agrégation ne connaît ni boto3 ni les "
            "variables d’environnement : <font face='Courier'>scripts/simulation_locale.py</font> "
            "produit le rapport complet sans aucune ressource AWS. Le nom du bucket avis est "
            "calculé (<font face='Courier'>!Sub</font>) pour rompre le cycle CloudFormation "
            "Bucket → Fonction → Rôle → Bucket.",
            s["body"],
        )
    )
    story.append(
        table(
            ["Chemin", "Rôle"],
            [
                ["template.yaml", "Infrastructure complète (AWS SAM)"],
                ["src/traiter_avis/", "Lambda #1 — S3 → Comprehend → DynamoDB"],
                ["src/generer_rapport_hebdo/", "Lambda #2 — synthèse + SES"],
                ["src/api_rapports/", "Lambda #3 — GET /rapports, GET /avis"],
                ["frontend/", "Dashboard statique (pas d’étape de build)"],
                ["tests/", "41 tests de la logique métier"],
            ],
            [52 * mm, 123 * mm],
            s,
        )
    )
    story.append(Spacer(1, 2 * mm))
    story.append(
        P(
            "<b>Limites assumées.</b> Lexique écrit à la main, sans négation (« pas de retard » "
            "active le motif retard) — le filtre par sentiment limite les dégâts. 28 avis "
            "démontrent le mécanisme, pas une performance statistique. Une seule langue "
            "(<font face='Courier'>fr</font>). SES en bac à sable. Dashboard en HTTP. Couplage "
            "fort à AWS, assumé pour une PME. Comprehend reste une boîte noire. Pistes : "
            "<font face='Courier'>detect_syntax</font> pour les portées de négation, Topic Modeling "
            "au-delà de quelques milliers d’avis, CloudFront + OAC en production.",
            s["body"],
        )
    )
    story.append(P("9. Conclusion", s["h1"]))
    story.append(
        P(
            "Les trois exigences sont tenues : automatisation, agrégation périodique, thèmes dans "
            "les deux polarités. Sur le corpus de démo, 28 avis produisent sans intervention un "
            "rapport à tendance mitigée (46&nbsp;% de négatifs), dominé par les retards, tandis que "
            "qualité produit et accueil boutique ressortent du côté positif. Ce qui fait la solution "
            "n’est pas la sophistication d’une brique, c’est la <b>séparation analyse unitaire / "
            "synthèse périodique</b>, qui rend le rejeu métier gratuit. Pour une PME à quelques "
            "centaines d’avis par mois, sans équipe technique ni budget d’outillage, le rapport "
            "valeur / coût d’exploitation fonde la pertinence de l’approche.",
            s["body"],
        )
    )

    doc = SimpleDocTemplate(
        str(SORTIE),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=17 * mm,
        topMargin=12 * mm,
        bottomMargin=16 * mm,
        title="NordicHome — Document de cadrage",
        author="Projet ml-with-aws",
        subject="Cadrage et architecture — reporting hebdomadaire de satisfaction client",
    )
    doc.build(story, canvasmaker=NumberedCanvas)
    reader_pages = None
    try:
        import pymupdf

        reader_pages = pymupdf.open(str(SORTIE)).page_count
    except Exception:
        reader_pages = "n/d"
    print(f"écrit {SORTIE} — {reader_pages} page(s)")
    if isinstance(reader_pages, int) and reader_pages > 6:
        raise SystemExit(f"Le document dépasse 6 pages ({reader_pages}). Resserrer le contenu.")


if __name__ == "__main__":
    build()
