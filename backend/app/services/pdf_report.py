"""Branded PDF rendering for ECDAT-X reports (reportlab / platypus)."""

from __future__ import annotations

import io
from datetime import datetime
from typing import Any
from xml.sax.saxutils import escape

import networkx as nx
from reportlab.graphics.shapes import Circle, Drawing, Line, Rect, String, Wedge
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    LongTable,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

INK = colors.HexColor("#0f172a")
ACCENT = colors.HexColor("#4f46e5")
MUTED = colors.HexColor("#64748b")
BORDER = colors.HexColor("#e2e8f0")
PANEL = colors.HexColor("#f8fafc")
WHITE = colors.white

SEVERITY_COLOR = {
    "critical": colors.HexColor("#dc2626"),
    "high": colors.HexColor("#ea580c"),
    "medium": colors.HexColor("#d97706"),
    "low": colors.HexColor("#16a34a"),
}
SEVERITY_TINT = {
    "critical": colors.HexColor("#fef2f2"),
    "high": colors.HexColor("#fff7ed"),
    "medium": colors.HexColor("#fffbeb"),
    "low": colors.HexColor("#f0fdf4"),
}
NEUTRAL = colors.HexColor("#94a3b8")
WAVE_COLORS = {1: colors.HexColor("#0891b2"), 2: ACCENT, 3: colors.HexColor("#d97706")}

PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 16 * mm
CONTENT_WIDTH = PAGE_WIDTH - 2 * MARGIN

_base = getSampleStyleSheet()
BODY = ParagraphStyle(
    "body",
    parent=_base["BodyText"],
    fontName="Helvetica",
    fontSize=8.6,
    leading=11.5,
    textColor=INK,
)
SMALL = ParagraphStyle("small", parent=BODY, fontSize=7.4, leading=9.5, textColor=MUTED)
CELL = ParagraphStyle("cell", parent=BODY, fontSize=7.6, leading=9.4)
CELL_MUTED = ParagraphStyle("cellm", parent=CELL, textColor=MUTED)
H1 = ParagraphStyle(
    "h1",
    parent=BODY,
    fontName="Helvetica-Bold",
    fontSize=15,
    leading=19,
    spaceAfter=4,
    alignment=TA_LEFT,
)
H2 = ParagraphStyle(
    "h2",
    parent=BODY,
    fontName="Helvetica-Bold",
    fontSize=10.5,
    leading=13,
    textColor=INK,
    spaceBefore=10,
    spaceAfter=5,
)
EYEBROW = ParagraphStyle(
    "eyebrow", parent=SMALL, fontName="Helvetica-Bold", fontSize=6.8, textColor=MUTED, spaceAfter=2
)


def _text(value: Any) -> str:
    return escape("" if value is None else str(value))


def _fmt_date(value: str | None) -> str:
    if not value:
        return "n/a"
    try:
        return datetime.fromisoformat(value).strftime("%d %b %Y")
    except ValueError:
        return value[:10]


def _fmt_datetime(value: str | None) -> str:
    if not value:
        return "n/a"
    try:
        return datetime.fromisoformat(value).strftime("%d %b %Y, %H:%M UTC")
    except ValueError:
        return value


def _sev_color(severity: str | None) -> colors.Color:
    return SEVERITY_COLOR.get(severity or "", NEUTRAL)


def _sev_cell(score: float | None, severity: str | None) -> Paragraph:
    if score is None:
        return Paragraph("-", CELL_MUTED)
    color = _sev_color(severity).hexval()[2:]
    return Paragraph(
        f'<font color="#{color}"><b>{score:.0f}</b></font> '
        f'<font color="#{color}" size="6.4">{_text((severity or "").upper())}</font>',
        CELL,
    )


# --------------------------------------------------------------------------- page chrome


class _NumberedCanvas(canvas.Canvas):
    """Canvas that can print "Page x of y" by deferring page output."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._saved_pages: list[dict[str, Any]] = []

    def showPage(self) -> None:  # noqa: N802 - reportlab API
        self._saved_pages.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        total = len(self._saved_pages)
        for state in self._saved_pages:
            self.__dict__.update(state)
            self._draw_footer(total)
            super().showPage()
        super().save()

    def _draw_footer(self, total: int) -> None:
        self.setStrokeColor(BORDER)
        self.setLineWidth(0.5)
        self.line(MARGIN, 13 * mm, PAGE_WIDTH - MARGIN, 13 * mm)
        self.setFont("Helvetica", 7)
        self.setFillColor(MUTED)
        self.drawString(
            MARGIN,
            9 * mm,
            "ECDAT-X  |  Enterprise Cryptographic Discovery, Analysis & Transformation",
        )
        self.drawRightString(PAGE_WIDTH - MARGIN, 9 * mm, f"Page {self._pageNumber} of {total}")


def _header(subtitle: str, org: str):
    def draw(page: canvas.Canvas, _doc: Any) -> None:
        page.saveState()
        band = 15 * mm
        page.setFillColor(INK)
        page.rect(0, PAGE_HEIGHT - band, PAGE_WIDTH, band, stroke=0, fill=1)
        page.setFillColor(ACCENT)
        page.rect(0, PAGE_HEIGHT - band, 4 * mm, band, stroke=0, fill=1)
        page.setFillColor(WHITE)
        page.setFont("Helvetica-Bold", 12)
        page.drawString(MARGIN, PAGE_HEIGHT - 9.6 * mm, "ECDAT-X")
        page.setFont("Helvetica", 8)
        page.setFillColor(colors.HexColor("#cbd5e1"))
        page.drawString(MARGIN + 21 * mm, PAGE_HEIGHT - 9.4 * mm, subtitle)
        page.drawRightString(PAGE_WIDTH - MARGIN, PAGE_HEIGHT - 9.4 * mm, f"CONFIDENTIAL  |  {org}")
        page.restoreState()

    return draw


def _document(subtitle: str, org: str) -> tuple[BaseDocTemplate, io.BytesIO]:
    buffer = io.BytesIO()
    doc = BaseDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=22 * mm,
        bottomMargin=18 * mm,
        title=f"ECDAT-X {subtitle}",
        author="ECDAT-X",
        subject=subtitle,
    )
    frame = Frame(
        MARGIN,
        18 * mm,
        CONTENT_WIDTH,
        PAGE_HEIGHT - 40 * mm,
        id="body",
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
    )
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=_header(subtitle, org))])
    return doc, buffer


def _build(doc: BaseDocTemplate, buffer: io.BytesIO, story: list[Any]) -> bytes:
    doc.build(story, canvasmaker=_NumberedCanvas)
    return buffer.getvalue()


# --------------------------------------------------------------------------- drawings


def _gauge(score: float, band: str, size: float = 128) -> Drawing:
    drawing = Drawing(size, size)
    center = size / 2
    outer, inner = size / 2 - 4, size / 2 - 19
    drawing.add(
        Wedge(center, center, outer, 0, 360, radius1=inner, fillColor=BORDER, strokeColor=None)
    )
    sweep = max(0.0, min(score, 100.0)) * 3.6
    if sweep > 0:
        drawing.add(
            Wedge(
                center,
                center,
                outer,
                90 - min(sweep, 359.9),
                90,
                radius1=inner,
                fillColor=_sev_color(band),
                strokeColor=None,
            )
        )
    drawing.add(
        String(
            center,
            center - 9,
            f"{score:.0f}",
            textAnchor="middle",
            fontName="Helvetica-Bold",
            fontSize=30,
            fillColor=INK,
        )
    )
    drawing.add(
        String(
            center,
            center - 21,
            "/ 100",
            textAnchor="middle",
            fontName="Helvetica",
            fontSize=8,
            fillColor=MUTED,
        )
    )
    drawing.add(
        String(
            center,
            center + 20,
            band.upper(),
            textAnchor="middle",
            fontName="Helvetica-Bold",
            fontSize=7.5,
            fillColor=_sev_color(band),
        )
    )
    return drawing


def _bar_chart(rows: list[dict[str, Any]], width: float = CONTENT_WIDTH) -> Drawing:
    row_height = 17
    drawing = Drawing(width, row_height * len(rows) + 14)
    label_width, value_width = 78, 34
    track = width - label_width - value_width - 6
    top = row_height * len(rows) + 4
    for index, row in enumerate(rows):
        y = top - (index + 1) * row_height + 3
        score = float(row["average_score"])
        band = row["band"]
        drawing.add(
            String(
                0,
                y + 3,
                str(row["category"]).title(),
                fontName="Helvetica",
                fontSize=8,
                fillColor=INK,
            )
        )
        drawing.add(
            Rect(label_width, y, track, 9, fillColor=PANEL, strokeColor=BORDER, strokeWidth=0.4)
        )
        drawing.add(
            Rect(
                label_width, y, track * score / 100, 9, fillColor=_sev_color(band), strokeColor=None
            )
        )
        drawing.add(
            String(
                label_width + track + 6,
                y + 2,
                f"{score:.1f}",
                fontName="Helvetica-Bold",
                fontSize=8,
                fillColor=INK,
            )
        )
    return drawing


def _unit_layout(sub: nx.Graph) -> dict[Any, tuple[float, float]]:
    """Lay out one connected component inside the unit square."""
    nodes = list(sub.nodes)
    if len(nodes) == 1:
        return {nodes[0]: (0.5, 0.5)}
    if len(nodes) == 2:
        return {nodes[0]: (0.3, 0.5), nodes[1]: (0.7, 0.5)}
    hub, hub_degree = max(sub.degree, key=lambda item: item[1])
    if hub_degree >= 0.8 * (len(nodes) - 1):
        # Hub-and-spoke (one shared trust anchor and its dependents): a shell layout is
        # instant and far tidier than a force-directed one.
        raw = nx.shell_layout(sub, nlist=[[hub], [node for node in nodes if node != hub]])
    elif len(nodes) <= 40:
        raw = nx.kamada_kawai_layout(sub)
    else:
        raw = nx.spring_layout(sub, seed=7, iterations=60)
    xs = [point[0] for point in raw.values()]
    ys = [point[1] for point in raw.values()]
    span_x = (max(xs) - min(xs)) or 1
    span_y = (max(ys) - min(ys)) or 1
    return {
        node: ((point[0] - min(xs)) / span_x, (point[1] - min(ys)) / span_y)
        for node, point in raw.items()
    }


def _dependency_graph(
    graph: dict[str, Any], width: float = CONTENT_WIDTH, height: float = 262
) -> Drawing:
    legend_height = 18
    drawing = Drawing(width, height + legend_height)
    drawing.add(
        Rect(0, legend_height, width, height, fillColor=PANEL, strokeColor=BORDER, strokeWidth=0.5)
    )
    nodes, edges = graph["nodes"], graph["edges"]
    if not nodes:
        return drawing

    network = nx.Graph()
    network.add_nodes_from(range(len(nodes)))
    network.add_edges_from((edge["source"], edge["target"]) for edge in edges)
    components = sorted(nx.connected_components(network), key=len, reverse=True)

    # Largest cluster (usually the shared trust anchor and its dependents) gets the left half;
    # the rest tile into a grid so unrelated clusters stay readable instead of drifting apart.
    regions: list[tuple[set[int], float, float, float, float]] = []
    if len(components) == 1:
        regions.append((components[0], 0, legend_height, width, legend_height + height))
    else:
        main_width = width * 0.5
        regions.append((components[0], 0, legend_height, main_width, legend_height + height))
        rest = components[1:]
        columns = max(
            1, min(len(rest), round((len(rest) * (width - main_width) / height) ** 0.5) or 1)
        )
        rows = -(-len(rest) // columns)
        cell_w, cell_h = (width - main_width) / columns, height / rows
        for index, component in enumerate(rest):
            row, column = divmod(index, columns)
            regions.append(
                (
                    component,
                    main_width + column * cell_w,
                    legend_height + height - (row + 1) * cell_h,
                    main_width + (column + 1) * cell_w,
                    legend_height + height - row * cell_h,
                )
            )

    placed: dict[int, tuple[float, float]] = {}
    label_targets: list[int] = []
    for component, x0, y0, x1, y1 in regions:
        drawing.add(
            Rect(
                x0 + 3,
                y0 + 3,
                x1 - x0 - 6,
                y1 - y0 - 6,
                rx=4,
                ry=4,
                fillColor=WHITE,
                strokeColor=BORDER,
                strokeWidth=0.4,
            )
        )
        layout = _unit_layout(network.subgraph(component))
        pad_x, pad_y = 22, 16
        for node, (ux, uy) in layout.items():
            placed[node] = (
                x0 + pad_x + ux * (x1 - x0 - 2 * pad_x),
                y0 + pad_y + uy * (y1 - y0 - 2 * pad_y),
            )
        ranked = sorted(component, key=lambda item: -nodes[item]["degree"])
        label_targets += ranked[: 2 if len(component) > 3 else 1]
    label_targets += [index for index, node in enumerate(nodes) if node["severity"] == "critical"]

    for edge in edges:
        x1, y1 = placed[edge["source"]]
        x2, y2 = placed[edge["target"]]
        drawing.add(Line(x1, y1, x2, y2, strokeColor=colors.HexColor("#cbd5e1"), strokeWidth=0.4))
    for index, node in enumerate(nodes):
        x, y = placed[index]
        radius = 2.2 + min(node["degree"], 24) * 0.28
        fill = _sev_color(node["severity"]) if node["severity"] else NEUTRAL
        drawing.add(Circle(x, y, radius, fillColor=fill, strokeColor=WHITE, strokeWidth=0.6))
    for index in dict.fromkeys(label_targets):
        node = nodes[index]
        x, y = placed[index]
        radius = 2.2 + min(node["degree"], 24) * 0.28
        label = node["label"] if len(node["label"]) <= 26 else node["label"][:25] + "..."
        text_width = stringWidth(label, "Helvetica", 6.4)
        on_left = x + radius + text_width + 6 > width
        text_x = x - radius - 3 - text_width if on_left else x + radius + 3
        drawing.add(
            Rect(
                text_x - 1.5,
                y - 4,
                text_width + 3,
                9,
                fillColor=WHITE,
                fillOpacity=0.85,
                strokeColor=None,
            )
        )
        drawing.add(String(text_x, y - 2, label, fontName="Helvetica", fontSize=6.4, fillColor=INK))

    for offset, (label, color) in enumerate(
        [
            ("Critical", SEVERITY_COLOR["critical"]),
            ("High", SEVERITY_COLOR["high"]),
            ("Medium", SEVERITY_COLOR["medium"]),
            ("Low", SEVERITY_COLOR["low"]),
            ("Unscored / dependent system", NEUTRAL),
        ]
    ):
        x = 6 + offset * 52
        drawing.add(Circle(x, 7, 3, fillColor=color, strokeColor=None))
        drawing.add(String(x + 6, 4.5, label, fontName="Helvetica", fontSize=6.4, fillColor=MUTED))
    return drawing


def _severity_bar(counts: dict[str, int], width: float = CONTENT_WIDTH) -> Drawing:
    total = sum(counts.values())
    drawing = Drawing(width, 34)
    if not total:
        return drawing
    x = 0.0
    for level in ("critical", "high", "medium", "low"):
        count = counts.get(level, 0)
        if not count:
            continue
        segment = width * count / total
        drawing.add(
            Rect(
                x,
                16,
                segment,
                13,
                fillColor=SEVERITY_COLOR[level],
                strokeColor=WHITE,
                strokeWidth=0.8,
            )
        )
        if segment > 18:
            drawing.add(
                String(
                    x + segment / 2,
                    20,
                    str(count),
                    textAnchor="middle",
                    fontName="Helvetica-Bold",
                    fontSize=7.5,
                    fillColor=WHITE,
                )
            )
        x += segment
    for offset, level in enumerate(("critical", "high", "medium", "low")):
        lx = offset * 92
        drawing.add(Rect(lx, 3, 7, 7, fillColor=SEVERITY_COLOR[level], strokeColor=None))
        drawing.add(
            String(
                lx + 11,
                3.5,
                f"{level.title()}  {counts.get(level, 0)}",
                fontName="Helvetica",
                fontSize=7,
                fillColor=MUTED,
            )
        )
    return drawing


def _timeline(waves: list[dict[str, Any]], width: float = CONTENT_WIDTH) -> Drawing:
    months = 18
    row_height = 24
    drawing = Drawing(width, row_height * len(waves) + 26)
    label_width = 70
    track = width - label_width - 4
    step = track / months
    top = row_height * len(waves) + 26
    for month in range(months + 1):
        x = label_width + month * step
        drawing.add(Line(x, 0, x, top - 16, strokeColor=BORDER, strokeWidth=0.4))
    for month in (1, 3, 6, 9, 12, 15, 18):
        drawing.add(
            String(
                label_width + (month - 0.5) * step,
                top - 12,
                f"M{month}",
                fontName="Helvetica",
                fontSize=6.5,
                fillColor=MUTED,
                textAnchor="middle",
            )
        )
    for index, wave in enumerate(waves):
        y = top - 22 - (index + 1) * row_height + 8
        drawing.add(
            String(
                0,
                y + 6,
                f"Wave {wave['wave']}",
                fontName="Helvetica-Bold",
                fontSize=8,
                fillColor=INK,
            )
        )
        x = label_width + wave["start_month"] * step
        bar_width = (wave["end_month"] - wave["start_month"]) * step
        drawing.add(
            Rect(
                x,
                y,
                bar_width,
                15,
                rx=2,
                ry=2,
                fillColor=WAVE_COLORS.get(wave["wave"], NEUTRAL),
                strokeColor=None,
            )
        )
        drawing.add(
            String(
                x + 5,
                y + 4.5,
                f"{wave['assets']} assets  |  ~{wave['effort_hours']}h",
                fontName="Helvetica-Bold",
                fontSize=7,
                fillColor=WHITE,
            )
        )
    return drawing


# --------------------------------------------------------------------------- building blocks


def _table_style(header_rows: int = 1) -> TableStyle:
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, header_rows - 1), INK),
            ("TEXTCOLOR", (0, 0), (-1, header_rows - 1), WHITE),
            ("FONTNAME", (0, 0), (-1, header_rows - 1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, header_rows - 1), 7),
            ("FONTNAME", (0, header_rows), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, header_rows), (-1, -1), 7.8),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, header_rows), (-1, -1), [WHITE, PANEL]),
            ("LINEBELOW", (0, header_rows), (-1, -1), 0.3, BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 3.4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3.4),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ]
    )


def _data_table(
    header: list[str], rows: list[list[Any]], widths: list[float], repeat: bool = True
) -> LongTable:
    table = LongTable([header, *rows], colWidths=widths, repeatRows=1 if repeat else 0)
    table.setStyle(_table_style())
    return table


def _meta_block(report: dict[str, Any]) -> Table:
    cells = [
        ("ORGANIZATION", report.get("organization_name") or report.get("organization_id")),
        ("LAST SCAN", _fmt_date(report.get("scan_date"))),
        ("ANALYST", report.get("analyst") or "n/a"),
        ("GENERATED", _fmt_datetime(report.get("generated_at"))),
    ]
    table = Table(
        [
            [Paragraph(label, EYEBROW) for label, _ in cells],
            [Paragraph(f"<b>{_text(value)}</b>", BODY) for _, value in cells],
        ],
        colWidths=[
            CONTENT_WIDTH * 0.28,
            CONTENT_WIDTH * 0.2,
            CONTENT_WIDTH * 0.2,
            CONTENT_WIDTH * 0.32,
        ],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PANEL),
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
                ("LINEAFTER", (0, 0), (-2, -1), 0.5, BORDER),
                ("TOPPADDING", (0, 0), (-1, 0), 6),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 0),
                ("TOPPADDING", (0, 1), (-1, 1), 1),
                ("BOTTOMPADDING", (0, 1), (-1, 1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return table


def _metric_cards(metrics: dict[str, Any]) -> Table:
    items = [
        ("TOTAL ASSETS DISCOVERED", metrics["total_assets"], INK),
        ("CRITICAL FINDINGS", metrics["critical_findings"], SEVERITY_COLOR["critical"]),
        ("SYSTEMS AT HNDL RISK", metrics["hndl_at_risk"], SEVERITY_COLOR["high"]),
        ("QUANTUM-VULNERABLE ASSETS", metrics["quantum_vulnerable"], ACCENT),
    ]
    cells = [
        [
            Paragraph(label, EYEBROW),
            Paragraph(f'<font size="20" color="#{color.hexval()[2:]}"><b>{value}</b></font>', BODY),
        ]
        for label, value, color in items
    ]
    table = Table(
        [[cells[0], cells[1]], [cells[2], cells[3]]],
        colWidths=[(CONTENT_WIDTH - 140) / 2] * 2,
        rowHeights=[56, 56],
    )
    table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER),
                ("BACKGROUND", (0, 0), (-1, -1), WHITE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
            ]
        )
    )
    return table


def _callout(
    title: str, body: str, color: colors.Color, tint: colors.Color, formula: str | None = None
) -> Table:
    lines = [
        Paragraph(
            f'<font color="#{color.hexval()[2:]}"><b>{_text(title)}</b></font>',
            ParagraphStyle("ct", parent=BODY, fontSize=10, leading=13),
        )
    ]
    if formula:
        lines.append(
            Paragraph(f'<font name="Courier-Bold" size="8.5">{_text(formula)}</font>', BODY)
        )
    lines.append(Paragraph(_text(body), BODY))
    table = Table([[lines]], colWidths=[CONTENT_WIDTH])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), tint),
                ("LINEBEFORE", (0, 0), (0, -1), 3, color),
                ("BOX", (0, 0), (-1, -1), 0.4, BORDER),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return table


def _top_assets_table(top: list[dict[str, Any]]) -> Table:
    rows = [
        [
            Paragraph(str(index), CELL_MUTED),
            Paragraph(f"<b>{_text(item['asset'])}</b>", CELL),
            Paragraph(_text(item["algorithm"] or item["type"]), CELL),
            _sev_cell(item["score"], item["severity"]),
            Paragraph(str(item["dependent_systems"]), CELL),
            Paragraph(_text(item["recommended_algorithm"] or "-"), CELL),
        ]
        for index, item in enumerate(top, 1)
    ] or [[Paragraph("No analyzed assets", CELL_MUTED), "", "", "", "", ""]]
    return _data_table(
        ["#", "ASSET", "ALGORITHM", "RISK", "DEPENDENTS", "TARGET (PQC)"],
        rows,
        [
            14,
            CONTENT_WIDTH * 0.3,
            CONTENT_WIDTH * 0.15,
            CONTENT_WIDTH * 0.13,
            CONTENT_WIDTH * 0.11,
            CONTENT_WIDTH * 0.31 - 14,
        ],
        repeat=False,
    )


def _mosca_callout(mosca: dict[str, Any]) -> Table:
    status = mosca["status"]
    if status == "behind":
        color, tint = SEVERITY_COLOR["critical"], SEVERITY_TINT["critical"]
    elif status == "ahead":
        color, tint = SEVERITY_COLOR["low"], SEVERITY_TINT["low"]
    else:
        color, tint = MUTED, PANEL
    formula = f"Mosca: {mosca['formula']}" if mosca.get("formula") else None
    return _callout(
        f"Mosca status: {mosca['headline']}", mosca["explanation"], color, tint, formula
    )


def _executive_story(report: dict[str, Any]) -> list[Any]:
    story: list[Any] = [
        Paragraph("CRYPTOGRAPHIC RISK", EYEBROW),
        Paragraph("Executive Summary", H1),
        _meta_block(report),
        Spacer(1, 9),
    ]
    gauge_block = Table(
        [
            [
                _gauge(report["risk_score"], report["risk_band"]),
                [
                    Paragraph("OVERALL QUANTUM RISK SCORE", EYEBROW),
                    Spacer(1, 3),
                    _metric_cards(report["metrics"]),
                ],
            ]
        ],
        colWidths=[136, CONTENT_WIDTH - 136],
    )
    gauge_block.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story += [gauge_block, Paragraph("Top 5 critical assets", H2)]
    story += [
        _top_assets_table(report["top_assets"]),
        Paragraph("Severity distribution (analyzed assets)", H2),
        _severity_bar(report["severity_counts"]),
        Spacer(1, 6),
        _mosca_callout(report["mosca"]),
        Spacer(1, 7),
        _callout("Recommendation", report["recommendation"], ACCENT, colors.HexColor("#eef2ff")),
    ]
    story.append(Spacer(1, 8))
    story.append(
        Paragraph(
            "Scores use the ECDAT six-factor model (quantum vulnerability 30%, HNDL "
            "exposure 20%, dependency centrality 15%, business criticality 15%, migration "
            "complexity 10%, evidence confidence 10%). "
            "Bands: 0-30 low, 31-60 medium, 61-80 high, 81-100 critical.",
            SMALL,
        )
    )
    return story


def _technical_story(report: dict[str, Any]) -> list[Any]:
    story = _executive_story(report)
    story.append(PageBreak())

    # 1. inventory
    story += [
        Paragraph("1. Cryptographic inventory", H2),
        Paragraph(
            f"{len(report['inventory'])} cryptographic assets discovered across all scanned "
            "projects, with the ECDAT risk score where analysis is available.",
            SMALL,
        ),
        Spacer(1, 4),
    ]
    inventory_rows = [
        [
            Paragraph(_text(item["type"]), CELL_MUTED),
            Paragraph(f"<b>{_text(item['name'])}</b>", CELL),
            Paragraph(_text(item["algorithm"] or "-"), CELL),
            Paragraph(_text(item["version"] or "-"), CELL_MUTED),
            Paragraph(_text(item["location"]), CELL_MUTED),
            _sev_cell(item["score"], item["severity"]),
        ]
        for item in report["inventory"]
    ]
    story.append(
        _data_table(
            ["TYPE", "NAME", "ALGORITHM", "VERSION", "LOCATION", "RISK"],
            inventory_rows,
            [
                CONTENT_WIDTH * 0.1,
                CONTENT_WIDTH * 0.22,
                CONTENT_WIDTH * 0.13,
                CONTENT_WIDTH * 0.08,
                CONTENT_WIDTH * 0.33,
                CONTENT_WIDTH * 0.14,
            ],
        )
    )

    # 2. risk breakdown
    story.append(Paragraph("2. Risk breakdown by category", H2))
    if report["risk_by_category"]:
        story.append(_bar_chart(report["risk_by_category"]))
        story.append(Spacer(1, 4))
        rows = [
            [
                Paragraph(f"<b>{_text(item['category']).title()}</b>", CELL),
                str(item["count"]),
                f"{item['average_score']:.1f}",
                f"{item['max_score']:.1f}",
                *[
                    str(item["severity_counts"][level])
                    for level in ("critical", "high", "medium", "low")
                ],
            ]
            for item in report["risk_by_category"]
        ]
        story.append(
            _data_table(
                [
                    "CATEGORY",
                    "ASSETS",
                    "AVG SCORE",
                    "MAX SCORE",
                    "CRITICAL",
                    "HIGH",
                    "MEDIUM",
                    "LOW",
                ],
                rows,
                [CONTENT_WIDTH * 0.16, *[CONTENT_WIDTH * 0.12] * 7],
                repeat=False,
            )
        )
        classification = report.get("quantum_classification") or {}
        if classification:
            story.append(Spacer(1, 4))
            story.append(
                Paragraph(
                    "Quantum vulnerability classes: "
                    + ", ".join(
                        f"<b>{_text(name)}</b> {count}"
                        for name, count in sorted(classification.items())
                    ),
                    SMALL,
                )
            )
    else:
        story.append(Paragraph("No risk analysis available yet.", SMALL))

    # 3. dependency graph
    story.append(
        KeepTogether(
            [
                Paragraph("3. Dependency graph", H2),
                Paragraph(
                    f"{len(report['graph']['nodes'])} assets and {len(report['graph']['edges'])} "
                    "relationships. Node size reflects dependency degree; colour reflects "
                    "severity. High-degree nodes are shared trust anchors whose migration "
                    "affects many systems."
                    + (
                        f" Showing the {len(report['graph']['nodes'])} most-connected of "
                        f"{report['graph']['total_assets']} assets."
                        if report["graph"]["truncated"]
                        else ""
                    ),
                    SMALL,
                ),
                Spacer(1, 4),
                _dependency_graph(report["graph"]),
            ]
        )
    )

    # 4. roadmap
    if report["roadmap"]:
        rows = [
            [
                Paragraph(f"<b>Wave {item['wave']}</b>", CELL),
                Paragraph(_text(item["title"]), CELL),
                str(item["assets"]),
                f"{item['effort_hours']}h",
                f"M{item['start_month'] + 1}-M{item['end_month']}",
                Paragraph(_text(", ".join(item["examples"])), CELL_MUTED),
            ]
            for item in report["roadmap"]
        ]
        story.append(
            KeepTogether(
                [
                    Paragraph("4. Migration roadmap", H2),
                    Paragraph(
                        "Dependency-aware waves: trust anchors and primitives first, then "
                        "shared libraries, "
                        "then applications. Effort is an estimate from migration complexity.",
                        SMALL,
                    ),
                    Spacer(1, 4),
                    _timeline(report["roadmap"]),
                    Spacer(1, 4),
                    _data_table(
                        ["WAVE", "SCOPE", "ASSETS", "EFFORT", "WINDOW", "EXAMPLES"],
                        rows,
                        [
                            CONTENT_WIDTH * 0.09,
                            CONTENT_WIDTH * 0.27,
                            CONTENT_WIDTH * 0.08,
                            CONTENT_WIDTH * 0.09,
                            CONTENT_WIDTH * 0.11,
                            CONTENT_WIDTH * 0.36,
                        ],
                        repeat=False,
                    ),
                ]
            )
        )

    # 5. PQC matrix
    if report["pqc_matrix"]:
        rows = [
            [
                Paragraph(f"<b>{_text(item['current'])}</b>", CELL),
                Paragraph(_text(item["recommended"]), CELL),
                str(item["assets"]),
                "-" if item["wave"] is None else f"W{item['wave']}",
                Paragraph(_text(item["complexity"]), CELL),
                Paragraph(_text(item["strategy"] or "-"), CELL_MUTED),
            ]
            for item in report["pqc_matrix"]
        ]
        story += [
            Paragraph("5. PQC recommendation matrix", H2),
            _data_table(
                [
                    "CURRENT",
                    "RECOMMENDED (NIST PQC)",
                    "ASSETS",
                    "WAVE",
                    "COMPLEXITY",
                    "TRANSITION STRATEGY",
                ],
                rows,
                [
                    CONTENT_WIDTH * 0.17,
                    CONTENT_WIDTH * 0.24,
                    CONTENT_WIDTH * 0.08,
                    CONTENT_WIDTH * 0.07,
                    CONTENT_WIDTH * 0.11,
                    CONTENT_WIDTH * 0.33,
                ],
            ),
        ]

    # 6. CBOM summary
    story += [Paragraph("6. CBOM summary", H2), _cbom_summary_table(report["cbom"])]
    return story


def _cbom_summary_table(summary: dict[str, Any]) -> Table:
    by_type = ", ".join(
        f"{name}: {count}" for name, count in sorted(summary["components_by_type"].items())
    )
    rows = [
        ["Format", f"{summary['format']} {summary['spec_version']} (CBOM)"],
        ["Serial number", summary["serial_number"]],
        [
            "Components",
            f"{summary['component_total']} total, "
            f"{summary['crypto_components']} with crypto properties",
        ],
        ["Component types", by_type or "-"],
        ["Dependency edges", str(summary["dependency_edges"])],
        [
            "Risk metadata",
            f"{summary['risk_scored'] or 0} components scored, average "
            f"{summary['risk_average'] or 'n/a'}, max {summary['risk_max'] or 'n/a'}",
        ],
    ]
    table = Table(
        [
            [Paragraph(f"<b>{_text(key)}</b>", CELL), Paragraph(_text(value), CELL)]
            for key, value in rows
        ],
        colWidths=[CONTENT_WIDTH * 0.22, CONTENT_WIDTH * 0.78],
    )
    table.setStyle(
        TableStyle(
            [
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, PANEL]),
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
                ("LINEBELOW", (0, 0), (-1, -2), 0.3, BORDER),
                ("TOPPADDING", (0, 0), (-1, -1), 3.4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3.4),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    return table


def _cbom_story(report: dict[str, Any]) -> list[Any]:
    story: list[Any] = [
        Paragraph("CRYPTOGRAPHY BILL OF MATERIALS", EYEBROW),
        Paragraph("CBOM report", H1),
        _meta_block(report),
        Paragraph(
            "Human-readable companion to the machine-readable CycloneDX JSON export. "
            "Both describe the same "
            "inventory: this document is for review, the JSON is for tooling.",
            SMALL,
        ),
        Paragraph("Document", H2),
        _cbom_summary_table(report["cbom"]),
        Paragraph("Cryptographic components", H2),
    ]
    rows = [
        [
            Paragraph(f"<b>{_text(item['name'])}</b>", CELL),
            Paragraph(
                _text(item["type"].replace("cryptographic-asset", "crypto-asset")), CELL_MUTED
            ),
            Paragraph(_text(item["primitive"] or "-"), CELL),
            "-" if item["quantum_level"] is None else str(item["quantum_level"]),
            _sev_cell(
                float(item["risk_score"]) if item["risk_score"] else None, item["risk_severity"]
            ),
            Paragraph(_text(item["location"]), CELL_MUTED),
        ]
        for item in report["components"]
    ]
    story.append(
        _data_table(
            ["COMPONENT", "TYPE", "PRIMITIVE", "NIST Q-LEVEL", "RISK", "LOCATION"],
            rows,
            [
                CONTENT_WIDTH * 0.24,
                CONTENT_WIDTH * 0.15,
                CONTENT_WIDTH * 0.12,
                CONTENT_WIDTH * 0.11,
                CONTENT_WIDTH * 0.12,
                CONTENT_WIDTH * 0.26,
            ],
        )
    )
    return story


_GENERIC_SECTIONS: dict[str, tuple[str, str, list[tuple[str, str, float]]]] = {
    "inventory": (
        "Cryptographic inventory",
        "assets",
        [
            ("TYPE", "type", 0.12),
            ("NAME", "name", 0.26),
            ("ALGORITHM", "algorithm", 0.16),
            ("VERSION", "version", 0.1),
            ("LOCATION", "location", 0.28),
            ("CONF.", "confidence", 0.08),
        ],
    ),
    "quantum-risk": (
        "Quantum risk analysis",
        "risks",
        [
            ("ASSET", "asset", 0.3),
            ("ALGORITHM", "algorithm", 0.18),
            ("SCORE", "score", 0.1),
            ("SEVERITY", "severity", 0.13),
            ("HNDL", "hndl_risk", 0.13),
            ("DEPENDENTS", "dependent_systems", 0.16),
        ],
    ),
    "migration": (
        "Migration plan",
        "migration_plan",
        [
            ("ASSET", "asset", 0.3),
            ("CURRENT", "current_algorithm", 0.2),
            ("RECOMMENDED", "recommended_algorithm", 0.26),
            ("WAVE", "wave", 0.09),
            ("COMPLEXITY", "complexity", 0.15),
        ],
    ),
}


def _generic_story(report: dict[str, Any]) -> list[Any]:
    title, key, columns = _GENERIC_SECTIONS[report["report_type"]]
    rows = [
        [
            Paragraph(
                _text(
                    round(item[field], 1)
                    if isinstance(item.get(field), float)
                    else item.get(field, "")
                ),
                CELL,
            )
            for _, field, _ in columns
        ]
        for item in report.get(key, [])
    ]
    return [
        Paragraph("ENTERPRISE SECURITY REPORT", EYEBROW),
        Paragraph(title, H1),
        _meta_block(report),
        Spacer(1, 8),
        _data_table(
            [label for label, _, _ in columns],
            rows,
            [CONTENT_WIDTH * share for _, _, share in columns],
        )
        if rows
        else Paragraph("No records available.", SMALL),
    ]


_PHASE_STATUS_COLOR = {
    "complete": (SEVERITY_COLOR["low"], SEVERITY_TINT["low"]),
    "in-progress": (SEVERITY_COLOR["medium"], SEVERITY_TINT["medium"]),
    "not-started": (NEUTRAL, PANEL),
}


def _nqm_story(report: dict[str, Any]) -> list[Any]:
    sector = report["sector"]
    current_phase = report["current_phase"]
    overall_color, overall_tint = (
        SEVERITY_COLOR["low"] if report["overall_progress"] >= 95 else ACCENT,
        SEVERITY_TINT["low"] if report["overall_progress"] >= 95 else PANEL,
    )
    story: list[Any] = [
        Paragraph("INDIA NQM COMPLIANCE", EYEBROW),
        Paragraph("National Quantum Mission Compliance Report", H1),
        _meta_block(report),
        Spacer(1, 8),
        _callout(
            f"Overall progress: {report['overall_progress']}% · Currently in Phase {current_phase}",
            report["source"],
            overall_color,
            overall_tint,
        ),
        Spacer(1, 10),
    ]
    for phase in report["phases"]:
        color, tint = _PHASE_STATUS_COLOR[phase["status"]]
        headline = (
            f"Phase {phase['id']} ({phase['years']}): {phase['name']} "
            f"— {phase['progress']}% {phase['status']}"
        )
        story.append(_callout(headline, phase["description"], color, tint))
        rows = [
            [
                Paragraph("✓" if item["complete"] else "○", CELL),
                Paragraph(_text(item["label"]), CELL),
                Paragraph(f"{item['progress']}%", CELL_MUTED),
                Paragraph(_text(item["evidence"]), CELL_MUTED),
            ]
            for item in phase["requirements"]
        ]
        story.append(
            _data_table(
                ["", "REQUIREMENT", "PROGRESS", "EVIDENCE"],
                rows,
                [16, CONTENT_WIDTH * 0.34, 50, CONTENT_WIDTH * 0.66 - 66],
                repeat=False,
            )
        )
        story.append(Spacer(1, 8))
    story.append(Paragraph(f"Sector profile: {sector['name']}", H2))
    sector_row = [
        Paragraph(_text(sector["regulator"]), CELL),
        Paragraph(_text(sector["recommended_baseline"]), CELL),
    ]
    story.append(
        _data_table(
            ["REGULATOR", "RECOMMENDED BASELINE"],
            [sector_row],
            [CONTENT_WIDTH * 0.35, CONTENT_WIDTH * 0.65],
            repeat=False,
        )
    )
    story.append(Spacer(1, 4))
    story.append(Paragraph(_text(sector["guidance"]), SMALL))
    return story


def render_pdf(report: dict[str, Any]) -> bytes:
    """Render any report dict produced by ``ReportService`` into a branded PDF."""
    kind = report["report_type"]
    org = str(report.get("organization_name") or report.get("organization_id") or "")
    if kind == "executive-summary":
        doc, buffer = _document("Cryptographic Risk Executive Summary", org)
        return _build(doc, buffer, _executive_story(report))
    if kind == "technical":
        doc, buffer = _document("Technical Cryptographic Risk Report", org)
        return _build(doc, buffer, _technical_story(report))
    if kind == "cbom":
        doc, buffer = _document("Cryptography Bill of Materials", org)
        return _build(doc, buffer, _cbom_story(report))
    if kind == "nqm-compliance":
        doc, buffer = _document("India NQM Compliance Report", org)
        return _build(doc, buffer, _nqm_story(report))
    doc, buffer = _document("Enterprise Security Report", org)
    return _build(doc, buffer, _generic_story(report))
