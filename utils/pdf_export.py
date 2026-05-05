"""
PDF report generator.
Uses reportlab (Platypus) for layout and kaleido (via plotly) for chart images.
"""
from __future__ import annotations

import io
import os
from datetime import date

import pandas as pd
from reportlab.lib import colors

import brand as _brand

_C = _brand.COLOURS  # shorthand
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from analysis.decay_engine import QCParams
from components.charts import (
    plot_ach_by_building,
    plot_ach_distribution,
    plot_ach_vs_decay_rate,
    plot_co2_timeline,
)
from translations import t

# ── Page geometry ─────────────────────────────────────────────────────────────
_W, _H = A4
_MARGIN = 2 * cm
_CW = _W - 2 * _MARGIN   # usable content width ≈ 461 pt


# ── Font registration ─────────────────────────────────────────────────────────
# Try to register a Unicode-capable system font (needed for μ, ², ⁻¹ etc.)
# Falls back to Helvetica (ASCII-only) if no system font is found.

def _register_fonts() -> tuple[str, str]:
    candidates = [
        ("RIAQNormal", "RIAQBold", "arial.ttf",      "arialbd.ttf"),
        ("RIAQNormal", "RIAQBold", "DejaVuSans.ttf",  "DejaVuSans-Bold.ttf"),
        ("RIAQNormal", "RIAQBold", "LiberationSans-Regular.ttf", "LiberationSans-Bold.ttf"),
    ]
    search_dirs = [
        r"C:\Windows\Fonts",
        "/usr/share/fonts/truetype/dejavu",
        "/usr/share/fonts/truetype/liberation",
        "/System/Library/Fonts",
        "/Library/Fonts",
    ]
    for norm_name, bold_name, norm_file, bold_file in candidates:
        for d in search_dirs:
            norm_path = os.path.join(d, norm_file)
            bold_path = os.path.join(d, bold_file)
            if os.path.exists(norm_path):
                try:
                    pdfmetrics.registerFont(TTFont(norm_name, norm_path))
                    if os.path.exists(bold_path):
                        pdfmetrics.registerFont(TTFont(bold_name, bold_path))
                    else:
                        bold_name = norm_name
                    return norm_name, bold_name
                except Exception:
                    continue
    return "Helvetica", "Helvetica-Bold"


_FONT, _FONT_BOLD = _register_fonts()


# ── Styles ────────────────────────────────────────────────────────────────────

def _styles() -> dict:
    base = getSampleStyleSheet()

    def add(name, **kw):
        kw.setdefault("fontName", _FONT)
        base.add(ParagraphStyle(name, **kw))

    add("RTitle",    fontSize=26, fontName=_FONT_BOLD, spaceAfter=4, leading=30,
        textColor=colors.HexColor(_C["dark_green"]))
    add("RSubtitle", fontSize=12, textColor=colors.HexColor(_C["text_secondary"]), spaceAfter=4)
    add("RH1",       fontSize=13, fontName=_FONT_BOLD, spaceBefore=10, spaceAfter=5,
        textColor=colors.HexColor(_C["dark_green"]))
    add("RH2",       fontSize=11, fontName=_FONT_BOLD, spaceBefore=6,  spaceAfter=3,
        textColor=colors.HexColor(_C["dark_green"]))
    add("RBody",     fontSize=10, spaceAfter=3)
    add("RSmall",    fontSize=8,  textColor=colors.HexColor(_C["text_secondary"]))

    return base


# ── Chart helpers ─────────────────────────────────────────────────────────────

def _fig_png(fig, width_px: int = 900, height_px: int = 420) -> io.BytesIO:
    """Render a Plotly figure to PNG bytes via kaleido."""
    png = fig.to_image(format="png", width=width_px, height=height_px, scale=2)
    buf = io.BytesIO(png)
    buf.seek(0)
    return buf


def _chart_image(fig, height_frac: float = 0.48) -> Image:
    """Return a reportlab Image scaled to content width."""
    buf = _fig_png(fig, width_px=round(_CW / cm * 37.8), height_px=round(_CW / cm * 37.8 * height_frac))
    img = Image(buf, width=_CW, height=_CW * height_frac)
    img._buf = buf   # keep reference so BytesIO isn't GC'd during build
    return img


# ── Table builders ────────────────────────────────────────────────────────────

_CELL_STYLE = [
    ("FONTNAME",      (0, 0), (-1, -1), _FONT),
    ("FONTSIZE",      (0, 0), (-1, -1), 10),
    ("TOPPADDING",    (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ("LEFTPADDING",   (0, 0), (-1, -1), 8),
    ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
]


def _kpi_table(results: pd.DataFrame, rejected: pd.DataFrame, lang: str) -> Table:
    total = len(results) + len(rejected)
    pct = f"{len(results) / total * 100:.1f}%" if total else "—"
    purges = int(results["IsPurge"].sum()) if len(results) else 0

    rows = [
        [t("mean_ach", lang),       f"{results['ACH_per_hour'].mean():.3f} h-1"],
        [t("accepted", lang),       str(len(results))],
        [t("rejected_label", lang), str(len(rejected))],
        [t("pct_accepted", lang),   pct],
        [t("purge_events", lang),   str(purges)],
    ]

    tbl = Table(rows, colWidths=[_CW * 0.5, _CW * 0.5])
    tbl.setStyle(TableStyle([
        *_CELL_STYLE,
        ("FONTNAME",       (0, 0), (0, -1), _FONT_BOLD),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.HexColor(_C["surface"]), colors.white]),
        ("GRID",           (0, 0), (-1, -1), 0.4, colors.HexColor(_C["border"])),
    ]))
    return tbl


def _results_table(results: pd.DataFrame, lang: str) -> Table:
    headers = [
        t("pdf_col_building",   lang),
        t("pdf_col_date",       lang),
        t("pdf_col_event",      lang),
        t("pdf_col_c0",         lang),
        t("pdf_col_ach",        lang),
        t("pdf_col_r2",         lang),
        t("pdf_col_decay_frac", lang),
        t("pdf_col_purge",      lang),
    ]
    col_fracs = [0.19, 0.13, 0.06, 0.11, 0.12, 0.10, 0.13, 0.08]
    col_widths = [_CW * f / sum(col_fracs) for f in col_fracs]

    rows = [headers]
    for _, row in results.sort_values(["HouseNo", "Date", "DecayEvent"]).iterrows():
        rows.append([
            str(row["HouseNo"]),
            str(row["Date"]),
            str(int(row["DecayEvent"])),
            f"{row['C0_ppm']:.0f}",
            f"{row['ACH_per_hour']:.3f}",
            f"{row['R_squared']:.3f}",
            f"{row['DecayFraction']:.2f}",
            "Y" if row["IsPurge"] else "",
        ])

    tbl = Table(rows, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(TableStyle([
        # Header row
        ("BACKGROUND",    (0, 0), (-1, 0),  colors.HexColor(_C["dark_green"])),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.white),
        ("FONTNAME",      (0, 0), (-1, 0),  _FONT_BOLD),
        ("FONTSIZE",      (0, 0), (-1, 0),  8),
        ("ALIGN",         (0, 0), (-1, 0),  "CENTER"),
        # Body
        ("FONTNAME",      (0, 1), (-1, -1), _FONT),
        ("FONTSIZE",      (0, 1), (-1, -1), 8),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, colors.HexColor(_C["surface"])]),
        ("GRID",          (0, 0), (-1, -1), 0.3, colors.HexColor(_C["border"])),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
        ("ALIGN",         (2, 1), (2, -1),  "CENTER"),
        ("ALIGN",         (7, 1), (7, -1),  "CENTER"),
    ]))
    return tbl


# ── Main entry point ──────────────────────────────────────────────────────────

def generate_pdf(
    results: pd.DataFrame,
    rejected: pd.DataFrame,
    df: pd.DataFrame,
    params: QCParams,
    lang: str,
) -> bytes:
    """
    Generate a PDF report and return it as bytes.

    Parameters
    ----------
    results   : accepted decay events from run_analysis()
    rejected  : rejected events from run_analysis()
    df        : normalised raw DataFrame (for CO2 timeline charts)
    params    : QCParams used for the analysis
    lang      : "en" or "is"
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=_MARGIN, rightMargin=_MARGIN,
        topMargin=_MARGIN,  bottomMargin=_MARGIN,
        title="RIAQ PWA — Ventilation Report",
    )
    S = _styles()
    story: list = []

    # ── Cover ─────────────────────────────────────────────────────────────────
    story.append(Paragraph("RIAQ PWA", S["RTitle"]))
    story.append(Paragraph(t("pdf_report", lang), S["RSubtitle"]))
    story.append(Spacer(1, 0.3 * cm))
    story.append(HRFlowable(width=_CW, thickness=1.5, color=colors.HexColor(_C["dark_green"])))
    story.append(Spacer(1, 0.4 * cm))

    buildings_str = ", ".join(sorted(results["HouseNo"].unique()))
    cover_rows = [
        [t("pdf_export_date",    lang), str(date.today())],
        [t("buildings_detected", lang), buildings_str],
        [t("date_range",         lang), f"{results['Date'].min()} — {results['Date'].max()}"],
    ]
    cover_tbl = Table(cover_rows, colWidths=[_CW * 0.32, _CW * 0.68])
    cover_tbl.setStyle(TableStyle([
        ("FONTNAME",    (0, 0), (0, -1), _FONT_BOLD),
        ("FONTNAME",    (1, 0), (1, -1), _FONT),
        ("FONTSIZE",    (0, 0), (-1, -1), 11),
        ("TOPPADDING",  (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0),(-1, -1), 5),
        ("LINEBELOW",   (0, -1),(-1, -1), 0.5, colors.HexColor("#cccccc")),
    ]))
    story.append(cover_tbl)
    story.append(Spacer(1, 0.7 * cm))

    # ── KPI summary ───────────────────────────────────────────────────────────
    story.append(Paragraph(t("pdf_kpi_summary", lang), S["RH1"]))
    story.append(_kpi_table(results, rejected, lang))
    story.append(PageBreak())

    # ── Chart 1: ACH Distribution ─────────────────────────────────────────────
    story.append(Paragraph(t("ach_distribution", lang), S["RH1"]))
    story.append(_chart_image(plot_ach_distribution(results, params, lang)))
    story.append(Spacer(1, 0.5 * cm))

    # ── Chart 2: ACH by Building ──────────────────────────────────────────────
    story.append(Paragraph(t("ach_by_building", lang), S["RH1"]))
    story.append(_chart_image(plot_ach_by_building(results, params, lang)))
    story.append(PageBreak())

    # ── Chart 3: ACH vs Decay Rate ────────────────────────────────────────────
    story.append(Paragraph(t("ach_vs_decay_rate", lang), S["RH1"]))
    story.append(_chart_image(plot_ach_vs_decay_rate(results, params, lang)))
    story.append(PageBreak())

    # ── Chart 4: CO2 Timelines (2 per page) ──────────────────────────────────
    story.append(Paragraph(t("pdf_co2_timelines", lang), S["RH1"]))
    houses = sorted(results["HouseNo"].unique())
    for i, house in enumerate(houses):
        story.append(Paragraph(house, S["RH2"]))
        story.append(_chart_image(
            plot_co2_timeline(df, house, results, lang),
            height_frac=0.36,
        ))
        # Page break after every 2 timelines (except the very last)
        if (i + 1) % 2 == 0 and i < len(houses) - 1:
            story.append(PageBreak())
        else:
            story.append(Spacer(1, 0.4 * cm))
    story.append(PageBreak())

    # ── Results table ─────────────────────────────────────────────────────────
    story.append(Paragraph(t("pdf_results_table", lang), S["RH1"]))
    story.append(Spacer(1, 0.2 * cm))
    story.append(_results_table(results, lang))

    doc.build(story)
    return buf.getvalue()
