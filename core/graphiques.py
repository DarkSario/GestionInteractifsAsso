"""Graphiques reportlab pour les exports PDF — Phase 21.

Utilise uniquement reportlab (pas de matplotlib).
"""

from __future__ import annotations

import math
from typing import Sequence

from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.units import cm

from utils.logger import get_logger

logger = get_logger(__name__)

# Palette de couleurs par défaut pour les graphiques
_PALETTE = [
    colors.HexColor("#1f6aa5"),
    colors.HexColor("#e74c3c"),
    colors.HexColor("#2ecc71"),
    colors.HexColor("#f39c12"),
    colors.HexColor("#9b59b6"),
    colors.HexColor("#1abc9c"),
    colors.HexColor("#e67e22"),
    colors.HexColor("#34495e"),
]


def _hex_to_color(hex_str: str) -> colors.Color:
    """Convertit une couleur hex en objet reportlab."""
    try:
        return colors.HexColor(hex_str)
    except Exception:
        return colors.HexColor("#1f6aa5")


def graphique_camembert_rl(
    donnees: list[tuple[str, float]],
    titre: str,
    couleur_principale: str = "#1f6aa5",
    largeur: float = 10 * cm,
    hauteur: float = 7 * cm,
) -> Drawing:
    """Crée un graphique camembert avec reportlab.

    Args:
        donnees: Liste de tuples (libellé, valeur).
        titre: Titre affiché au-dessus du graphique.
        couleur_principale: Couleur principale (hex) pour la palette.
        largeur: Largeur du dessin.
        hauteur: Hauteur du dessin.

    Returns:
        Objet Drawing reportlab.
    """
    drawing = Drawing(largeur, hauteur)

    # Titre
    titre_str = String(largeur / 2, hauteur - 14, titre, textAnchor="middle",
                       fontSize=10, fontName="Helvetica-Bold")
    drawing.add(titre_str)

    if not donnees:
        msg = String(largeur / 2, hauteur / 2, "Aucune donnée", textAnchor="middle",
                     fontSize=9, fontName="Helvetica")
        drawing.add(msg)
        return drawing

    # Filtrer les valeurs positives
    donnees_valides = [(lib, val) for lib, val in donnees if val > 0]
    if not donnees_valides:
        msg = String(largeur / 2, hauteur / 2, "Aucune donnée positive", textAnchor="middle",
                     fontSize=9, fontName="Helvetica")
        drawing.add(msg)
        return drawing

    couleur_princ = _hex_to_color(couleur_principale)
    palette = [couleur_princ] + _PALETTE[1:]

    pie = Pie()
    pie.x = 20
    pie.y = 20
    pie.width = min(largeur * 0.45, hauteur - 40)
    pie.height = pie.width
    pie.data = [val for _, val in donnees_valides]
    pie.labels = None

    for i, (_, _) in enumerate(donnees_valides):
        pie.slices[i].fillColor = palette[i % len(palette)]
        pie.slices[i].strokeColor = colors.white
        pie.slices[i].strokeWidth = 1

    drawing.add(pie)

    # Légende
    total = sum(val for _, val in donnees_valides)
    legend_x = pie.x + pie.width + 15
    legend_y = pie.y + pie.height
    line_h = 14

    for i, (lib, val) in enumerate(donnees_valides):
        y_pos = legend_y - i * line_h
        if y_pos < 10:
            break
        couleur = palette[i % len(palette)]
        rect = Rect(legend_x, y_pos - 8, 10, 10, fillColor=couleur, strokeColor=None)
        drawing.add(rect)
        pct = f"{val / total * 100:.1f}%" if total > 0 else ""
        label_text = f"{lib[:20]} ({pct})" if len(lib) > 20 else f"{lib} ({pct})"
        lbl = String(legend_x + 14, y_pos - 7, label_text,
                     fontSize=7, fontName="Helvetica")
        drawing.add(lbl)

    return drawing


def graphique_barres_rl(
    donnees: list[tuple[str, float, float]],
    titre: str,
    couleur_principale: str = "#1f6aa5",
    largeur: float = 14 * cm,
    hauteur: float = 8 * cm,
    label1: str = "Recettes",
    label2: str = "Dépenses",
) -> Drawing:
    """Crée un histogramme à barres groupées avec reportlab.

    Args:
        donnees: Liste de tuples (libellé, valeur1, valeur2).
        titre: Titre affiché au-dessus du graphique.
        couleur_principale: Couleur principale (hex).
        largeur: Largeur du dessin.
        hauteur: Hauteur du dessin.
        label1: Légende série 1.
        label2: Légende série 2.

    Returns:
        Objet Drawing reportlab.
    """
    drawing = Drawing(largeur, hauteur)

    titre_str = String(largeur / 2, hauteur - 14, titre, textAnchor="middle",
                       fontSize=10, fontName="Helvetica-Bold")
    drawing.add(titre_str)

    if not donnees:
        msg = String(largeur / 2, hauteur / 2, "Aucune donnée", textAnchor="middle",
                     fontSize=9, fontName="Helvetica")
        drawing.add(msg)
        return drawing

    couleur1 = _hex_to_color(couleur_principale)
    couleur2 = colors.HexColor("#e74c3c")

    bc = VerticalBarChart()
    bc.x = 40
    bc.y = 40
    bc.height = hauteur - 70
    bc.width = largeur - 60
    bc.data = [
        [v1 for _, v1, _ in donnees],
        [v2 for _, _, v2 in donnees],
    ]
    bc.categoryAxis.categoryNames = [str(lib)[:10] for lib, _, _ in donnees]
    bc.categoryAxis.labels.fontSize = 7
    bc.categoryAxis.labels.angle = 30 if len(donnees) > 6 else 0
    bc.valueAxis.labels.fontSize = 7
    bc.groupSpacing = 5
    bc.bars[0].fillColor = couleur1
    bc.bars[1].fillColor = couleur2

    drawing.add(bc)

    # Légende
    legend = Legend()
    legend.x = bc.x
    legend.y = 10
    legend.columnMaximum = 1
    legend.dx = 10
    legend.dy = 8
    legend.deltax = 80
    legend.deltay = 0
    legend.fontSize = 8
    legend.fontName = "Helvetica"
    legend.colorNamePairs = [(couleur1, label1), (couleur2, label2)]
    drawing.add(legend)

    return drawing


def graphique_courbe_rl(
    donnees: list[tuple[str, float]],
    titre: str,
    couleur_principale: str = "#1f6aa5",
    largeur: float = 14 * cm,
    hauteur: float = 7 * cm,
) -> Drawing:
    """Crée un graphique en courbe avec reportlab.

    Args:
        donnees: Liste de tuples (libellé, valeur).
        titre: Titre affiché au-dessus du graphique.
        couleur_principale: Couleur principale (hex).
        largeur: Largeur du dessin.
        hauteur: Hauteur du dessin.

    Returns:
        Objet Drawing reportlab.
    """
    from reportlab.graphics.charts.lineplots import LinePlot
    from reportlab.graphics.widgets.markers import makeMarker

    drawing = Drawing(largeur, hauteur)

    titre_str = String(largeur / 2, hauteur - 14, titre, textAnchor="middle",
                       fontSize=10, fontName="Helvetica-Bold")
    drawing.add(titre_str)

    if not donnees:
        msg = String(largeur / 2, hauteur / 2, "Aucune donnée", textAnchor="middle",
                     fontSize=9, fontName="Helvetica")
        drawing.add(msg)
        return drawing

    couleur = _hex_to_color(couleur_principale)
    valeurs = [val for _, val in donnees]

    lp = LinePlot()
    lp.x = 40
    lp.y = 30
    lp.height = hauteur - 60
    lp.width = largeur - 60
    lp.data = [list(enumerate(valeurs))]
    lp.lines[0].strokeColor = couleur
    lp.lines[0].strokeWidth = 2
    try:
        lp.lines[0].symbol = makeMarker("FilledCircle")
        lp.lines[0].symbol.size = 4
        lp.lines[0].symbol.fillColor = couleur
    except Exception:
        pass

    lp.xValueAxis.labels.fontSize = 7
    lp.yValueAxis.labels.fontSize = 7
    lp.xValueAxis.valueMin = 0
    lp.xValueAxis.valueMax = max(len(valeurs) - 1, 1)
    lp.xValueAxis.valueStep = max(1, len(valeurs) // 6)

    drawing.add(lp)

    # Labels axe X
    if donnees:
        step = max(1, len(donnees) // 8)
        for i, (lib, _) in enumerate(donnees):
            if i % step == 0:
                x_pos = lp.x + (i / max(len(donnees) - 1, 1)) * lp.width
                label = String(x_pos, lp.y - 12, str(lib)[:8],
                               textAnchor="middle", fontSize=6, fontName="Helvetica")
                drawing.add(label)

    return drawing
