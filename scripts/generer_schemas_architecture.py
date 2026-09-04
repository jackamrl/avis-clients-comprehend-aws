"""Génère les schémas PNG des deux chaînes (temps réel et périodique)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RACINE = Path(__file__).resolve().parents[1]
SORTIE = RACINE / "docs"

BG = "#F6F7F9"
INK = "#1A1D23"
MUTED = "#5C6570"
LINE = "#3D4654"
BOX = "#FFFFFF"
BORDER = "#C9CFD6"

ORANGE = "#C45C12"
BLUE = "#2B4FA8"
PURPLE = "#5B3D8F"
TEAL = "#1F6F64"
ROSE = "#9B2F4A"
SLATE = "#3E4754"

W, H = 3360, 1560
S = 2  # coordonnées logiques × 2


def L(x: int) -> int:
    return x * S


@dataclass
class Boite:
    x: int
    y: int
    w: int
    h: int
    titre: str
    sous: str
    accent: str

    @property
    def cx(self) -> int:
        return L(self.x + self.w // 2)

    @property
    def cy(self) -> int:
        return L(self.y + self.h // 2)

    @property
    def droite(self) -> tuple[int, int]:
        return L(self.x + self.w), self.cy

    @property
    def gauche(self) -> tuple[int, int]:
        return L(self.x), self.cy

    @property
    def bas(self) -> tuple[int, int]:
        return self.cx, L(self.y + self.h)

    @property
    def haut(self) -> tuple[int, int]:
        return self.cx, L(self.y)


def fonts() -> dict[str, ImageFont.FreeTypeFont]:
    d = Path(r"C:\Windows\Fonts")
    return {
        "h1": ImageFont.truetype(str(d / "segoeuib.ttf"), 68),
        "lead": ImageFont.truetype(str(d / "segoeui.ttf"), 34),
        "titre": ImageFont.truetype(str(d / "segoeuib.ttf"), 34),
        "sous": ImageFont.truetype(str(d / "segoeui.ttf"), 28),
        "label": ImageFont.truetype(str(d / "segoeui.ttf"), 26),
    }


def dessiner_boite(draw: ImageDraw.ImageDraw, b: Boite, f: dict) -> None:
    x, y, w, h = L(b.x), L(b.y), L(b.w), L(b.h)
    draw.rounded_rectangle((x, y, x + w, y + h), radius=20, fill=BOX, outline=BORDER, width=3)
    draw.rectangle((x, y + 14, x + 16, y + h - 14), fill=b.accent)
    tx, ty = x + 44, y + 48
    draw.text((tx, ty), b.titre, font=f["titre"], fill=INK)
    for i, ligne in enumerate(b.sous.split("\n")):
        draw.text((tx, ty + 56 + i * 40), ligne, font=f["sous"], fill=MUTED)


def triangle(draw: ImageDraw.ImageDraw, tip: tuple[int, int], dx: float, dy: float) -> None:
    longueur = (dx * dx + dy * dy) ** 0.5 or 1
    ux, uy = dx / longueur, dy / longueur
    px, py = -uy, ux
    taille = 22
    p1 = (tip[0] - ux * taille + px * 12, tip[1] - uy * taille + py * 12)
    p2 = (tip[0] - ux * taille - px * 12, tip[1] - uy * taille - py * 12)
    draw.polygon([tip, p1, p2], fill=LINE)


def fleche(
    draw: ImageDraw.ImageDraw,
    a: tuple[int, int],
    b: tuple[int, int],
    f: dict,
    *,
    dashed: bool = False,
    label: str | None = None,
    label_dy: int = -36,
    bi: bool = False,
) -> None:
    x1, y1 = a
    x2, y2 = b
    dist = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
    if dist == 0:
        return
    ux, uy = (x2 - x1) / dist, (y2 - y1) / dist

    if dashed:
        pos, dash, gap = 0.0, 22.0, 16.0
        while pos < dist - 30:
            xa, ya = x1 + ux * pos, y1 + uy * pos
            xb, yb = x1 + ux * min(pos + dash, dist - 30), y1 + uy * min(pos + dash, dist - 30)
            draw.line((xa, ya, xb, yb), fill=LINE, width=4)
            pos += dash + gap
    else:
        draw.line((x1, y1, x2, y2), fill=LINE, width=4)

    triangle(draw, (x2, y2), x2 - x1, y2 - y1)
    if bi:
        triangle(draw, (x1, y1), x1 - x2, y1 - y2)

    if label:
        mx, my = (x1 + x2) // 2, (y1 + y2) // 2 + L(label_dy // 2)
        bbox = f["label"].getbbox(label)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        pad_x, pad_y = 14, 8
        rx1 = mx - tw // 2 - pad_x
        ry1 = my - th // 2 - pad_y
        draw.rounded_rectangle(
            (rx1, ry1, rx1 + tw + 2 * pad_x, ry1 + th + 2 * pad_y),
            radius=8,
            fill=BG,
            outline=BORDER,
            width=2,
        )
        draw.text((rx1 + pad_x, ry1 + pad_y - 2), label, font=f["label"], fill=MUTED)


def composer(titre: str, sous: str, boites: list[Boite], fleches: list[dict], chemin: Path) -> None:
    f = fonts()
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    draw.text((L(56), L(36)), titre, font=f["h1"], fill=INK)
    draw.text((L(56), L(82)), sous, font=f["lead"], fill=MUTED)
    draw.line((L(56), L(118), L(1624), L(118)), fill=BORDER, width=2)
    for spec in fleches:
        fleche(
            draw,
            spec["a"],
            spec["b"],
            f,
            dashed=spec.get("dashed", False),
            label=spec.get("label"),
            label_dy=spec.get("label_dy", -36),
            bi=spec.get("bi", False),
        )
    for b in boites:
        dessiner_boite(draw, b, f)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    img.save(chemin, "PNG", optimize=True)
    print(f"écrit {chemin} ({img.width}x{img.height})")


def schema_temps_reel() -> None:
    sources = Boite(56, 200, 250, 140, "Sources", "CRM / formulaire web\nmarketplace", SLATE)
    s3 = Boite(380, 200, 250, 140, "S3 — avis", "préfixe incoming/\nfichiers .txt", ORANGE)
    lam = Boite(704, 200, 280, 140, "Lambda", "traiter-avis\nPython 3.12 · arm64", ORANGE)
    cmp = Boite(1060, 200, 300, 140, "Amazon Comprehend", "detect_sentiment\ndetect_key_phrases", PURPLE)
    ddb = Boite(704, 500, 280, 140, "DynamoDB Avis", "put_item\nGSI avis-par-mois", BLUE)
    dlq = Boite(1060, 500, 300, 140, "SQS — DLQ", "échecs après réessais\nalarme CloudWatch", ROSE)

    fleches = [
        {"a": sources.droite, "b": (s3.gauche[0] - 4, s3.cy), "label": "dépôt .txt"},
        {"a": s3.droite, "b": (lam.gauche[0] - 4, lam.cy), "label": "ObjectCreated"},
        {"a": lam.droite, "b": (cmp.gauche[0] - 4, cmp.cy), "label": "2 appels / avis", "bi": True},
        {"a": (lam.cx, lam.bas[1] + 4), "b": (ddb.cx, ddb.haut[1] - 4), "label": "put_item", "label_dy": 0},
        {
            "a": (L(lam.x + lam.w - 36), lam.bas[1] + 4),
            "b": (L(dlq.x + 36), dlq.haut[1] - 4),
            "dashed": True,
            "label": "échec transitoire",
            "label_dy": 8,
        },
    ]
    composer(
        "Chaîne temps réel — à chaque avis",
        "Analyse unitaire : un fichier déposé sur S3 déclenche Comprehend, puis l’écriture dans DynamoDB.",
        [sources, s3, lam, cmp, ddb, dlq],
        fleches,
        SORTIE / "architecture-temps-reel.png",
    )


def schema_periodique() -> None:
    evb = Boite(56, 200, 280, 140, "EventBridge", "Scheduler\ncron lundi 08h00 Paris", TEAL)
    lam = Boite(430, 200, 340, 140, "Lambda", "generer-rapport-hebdo\nfenêtre glissante 7 jours", ORANGE)
    rap = Boite(870, 200, 300, 140, "DynamoDB Rapports", "PK semaine_id\nGSI rapports-par-date", BLUE)
    avis = Boite(430, 500, 340, 140, "DynamoDB Avis", "Query index avis-par-mois\njamais de Scan", BLUE)
    ses = Boite(870, 500, 300, 140, "Amazon SES", "e-mail HTML + texte\nstatut d’envoi persisté", TEAL)
    mgr = Boite(1260, 500, 250, 140, "Manager", "synthèse hebdo\ndans la boîte mail", SLATE)

    fleches = [
        {"a": evb.droite, "b": (lam.gauche[0] - 4, lam.cy), "label": "invoke"},
        {
            "a": (avis.cx, avis.haut[1] - 4),
            "b": (lam.cx, lam.bas[1] + 4),
            "label": "Query 7 jours",
            "label_dy": 0,
        },
        {"a": lam.droite, "b": (rap.gauche[0] - 4, rap.cy), "label": "put_item"},
        {
            "a": (L(lam.x + lam.w - 48), lam.bas[1] + 4),
            "b": (L(ses.x + 48), ses.haut[1] - 4),
            "label": "send_email",
            "label_dy": 8,
        },
        {"a": ses.droite, "b": (mgr.gauche[0] - 4, mgr.cy)},
    ]
    composer(
        "Chaîne périodique — chaque lundi 08h00",
        "Agrégation rejouable : statistiques, thèmes récurrents, persistance DynamoDB et e-mail de synthèse.",
        [evb, lam, rap, avis, ses, mgr],
        fleches,
        SORTIE / "architecture-periodique.png",
    )


if __name__ == "__main__":
    schema_temps_reel()
    schema_periodique()
