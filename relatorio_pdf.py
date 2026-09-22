"""Geração do relatório gerencial em PDF do Indicador Operacional Mediatorie."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    PageBreak,
    KeepTogether,
)


VERDE = "#86BC25"
VERDE_ESCURO = "#5F8E16"
VERMELHO = "#D64545"
GRAFITE = "#4B4F4D"
CINZA = "#7A847D"
FUNDO = "#F5F7F2"


def _numero(valor: int | float) -> str:
    try:
        return f"{int(valor):,}".replace(",", ".")
    except Exception:
        return "0"


def _percentual(valor: float) -> str:
    return f"{float(valor):.2f}%".replace(".", ",")


def _styles():
    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="MediatorieTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=27,
            textColor=colors.HexColor(GRAFITE),
            alignment=TA_CENTER,
            spaceAfter=10,
        )
    )

    styles.add(
        ParagraphStyle(
            name="MediatorieSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10.5,
            leading=15,
            textColor=colors.HexColor(CINZA),
            alignment=TA_CENTER,
            spaceAfter=8,
        )
    )

    styles.add(
        ParagraphStyle(
            name="Section",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=19,
            textColor=colors.HexColor(VERDE_ESCURO),
            spaceBefore=8,
            spaceAfter=8,
        )
    )

    styles.add(
        ParagraphStyle(
            name="Small",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor(CINZA),
        )
    )

    styles.add(
        ParagraphStyle(
            name="BodyMediatorie",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=14,
            textColor=colors.HexColor(GRAFITE),
            spaceAfter=5,
        )
    )
    return styles


def _fig_para_imagem(fig, largura_mm: float = 175) -> Image:
    buffer = BytesIO()
    fig.savefig(
        buffer,
        format="png",
        dpi=155,
        bbox_inches="tight",
        facecolor="white",
    )
    plt.close(fig)
    buffer.seek(0)

    img = Image(buffer)
    proporcao = img.imageHeight / img.imageWidth
    img.drawWidth = largura_mm * mm
    img.drawHeight = largura_mm * proporcao * mm
    return img


def _grafico_percentual(mensal: pd.DataFrame, titulo: str, meta: float):
    fig, ax = plt.subplots(figsize=(10.8, 4.6))

    if mensal.empty:
        ax.text(0.5, 0.5, "Sem dados para o período", ha="center", va="center")
        ax.axis("off")
        return fig

    comp = mensal["Comp"].astype(str).tolist()
    dentro = mensal["Percentual_Dentro"].astype(float).to_numpy()
    fora = mensal["Percentual_Fora"].astype(float).to_numpy()
    x = np.arange(len(comp))

    ax.bar(x, dentro, label="Dentro do SLA", color=VERDE)
    ax.bar(x, fora, bottom=dentro, label="Fora do SLA", color=VERMELHO)

    for i, (d, f) in enumerate(zip(dentro, fora)):
        if d >= 5:
            ax.text(i, d / 2, f"{d:.1f}%", ha="center", va="center", fontsize=8)
        if f >= 5:
            ax.text(i, d + f / 2, f"{f:.1f}%", ha="center", va="center", fontsize=8)

    ax.axhline(meta, color=GRAFITE, linestyle="--", linewidth=1.5, label=f"Meta {meta:.0f}%")
    ax.set_ylim(0, 100)
    ax.set_ylabel("Percentual")
    ax.set_title(titulo, loc="left", fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(comp, rotation=35, ha="right")
    ax.grid(axis="y", alpha=0.18)
    ax.legend(ncol=3, frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.15))
    fig.tight_layout()
    return fig


def _grafico_quantidade_efetivacao(mensal: pd.DataFrame, titulo: str):
    fig, ax = plt.subplots(figsize=(10.8, 4.4))

    if mensal.empty:
        ax.text(0.5, 0.5, "Sem dados para o período", ha="center", va="center")
        ax.axis("off")
        return fig

    comp = mensal["Comp"].astype(str).tolist()
    dentro = mensal["Dentro"].astype(int).to_numpy()
    fora = mensal["Fora"].astype(int).to_numpy()
    x = np.arange(len(comp))

    ax.bar(x, dentro, label="Dentro do SLA", color=VERDE)
    ax.bar(x, fora, bottom=dentro, label="Fora do SLA", color=VERMELHO)

    for i, (d, f) in enumerate(zip(dentro, fora)):
        if d > 0:
            ax.text(i, d / 2, str(d), ha="center", va="center", fontsize=8)
        if f > 0:
            ax.text(i, d + f / 2, str(f), ha="center", va="center", fontsize=8)

    ax.set_ylabel("Quantidade")
    ax.set_title(titulo, loc="left", fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(comp, rotation=35, ha="right")
    ax.grid(axis="y", alpha=0.18)
    ax.legend(ncol=2, frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.12))
    fig.tight_layout()
    return fig


def _grafico_ranking(ranking: pd.DataFrame, titulo: str):
    fig, ax = plt.subplots(figsize=(10.8, 4.8))

    ranking = ranking.copy()
    if ranking.empty or not ranking["Fora"].gt(0).any():
        ax.text(0.5, 0.5, "Nenhum produto fora do SLA", ha="center", va="center")
        ax.axis("off")
        return fig

    ranking = ranking.loc[ranking["Fora"].gt(0)].copy()
    ranking = ranking.sort_values("Fora", ascending=True)

    nomes = ranking.iloc[:, 0].astype(str).map(
        lambda x: x if len(x) <= 45 else x[:42] + "..."
    )

    ax.barh(nomes, ranking["Fora"], color=VERMELHO)
    for i, valor in enumerate(ranking["Fora"]):
        ax.text(valor, i, f" {int(valor)}", va="center", fontsize=8)

    ax.set_xlabel("Quantidade fora do SLA")
    ax.set_title(titulo, loc="left", fontweight="bold")
    ax.grid(axis="x", alpha=0.18)
    fig.tight_layout()
    return fig


def _grafico_movimentacoes(mensal: pd.DataFrame, percentual: bool, meta: float):
    fig, ax = plt.subplots(figsize=(10.8, 4.6))

    if mensal.empty:
        ax.text(0.5, 0.5, "Sem dados para o período", ha="center", va="center")
        ax.axis("off")
        return fig

    comp = mensal["Competencia"].astype(str).tolist()
    x = np.arange(len(comp))

    if percentual:
        dentro = mensal["Percentual_Dentro"].astype(float).to_numpy()
        fora = mensal["Percentual_Fora"].astype(float).to_numpy()
        ax.bar(x, dentro, label="Dentro do prazo", color=VERDE)
        ax.bar(x, fora, bottom=dentro, label="Fora do prazo", color=VERMELHO)
        ax.axhline(meta, color=GRAFITE, linestyle="--", linewidth=1.5, label=f"Meta {meta:.0f}%")
        ax.set_ylim(0, 100)
        ax.set_ylabel("Percentual")
        titulo = "Movimentações - cumprimento por competência"
    else:
        dentro = mensal["Quantidade_Dentro"].astype(int).to_numpy()
        fora = mensal["Quantidade_Fora"].astype(int).to_numpy()
        ax.bar(x, dentro, label="Dentro do prazo", color=VERDE)
        ax.bar(x, fora, bottom=dentro, label="Fora do prazo", color=VERMELHO)
        ax.set_ylabel("Quantidade")
        titulo = "Movimentações - volume por competência"

    ax.set_title(titulo, loc="left", fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(comp, rotation=35, ha="right")
    ax.grid(axis="y", alpha=0.18)
    ax.legend(ncol=3, frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.15))
    fig.tight_layout()
    return fig


def _kpi_table(resumo: dict, labels: list[tuple[str, str]]):
    dados = []
    cabecalho = []
    for rotulo, chave in labels:
        cabecalho.append(rotulo)
        valor = resumo.get(chave, 0)
        if "percentual" in chave:
            dados.append(_percentual(valor))
        else:
            dados.append(_numero(valor))

    tabela = Table([cabecalho, dados], colWidths=[43 * mm] * len(cabecalho))
    tabela.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF5E5")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor(VERDE_ESCURO)),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D9E3D2")),
                ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#E1E8DD")),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return tabela


def _table_mensal_efetivacao(mensal: pd.DataFrame):
    if mensal.empty:
        return None

    linhas = [["Competência", "Dentro", "Fora", "Total", "% Dentro", "% Fora"]]
    for _, row in mensal.iterrows():
        linhas.append(
            [
                str(row["Comp"]),
                _numero(row["Dentro"]),
                _numero(row["Fora"]),
                _numero(row["Total"]),
                _percentual(row["Percentual_Dentro"]),
                _percentual(row["Percentual_Fora"]),
            ]
        )

    tabela = Table(linhas, repeatRows=1, colWidths=[28, 24, 24, 24, 30, 30])
    tabela._argW = [30*mm, 24*mm, 24*mm, 24*mm, 30*mm, 30*mm]
    tabela.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(VERDE)),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ALIGN", (1, 1), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#DCE4D7")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F9F5")]),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return tabela


def _table_mensal_movimentacoes(mensal: pd.DataFrame):
    if mensal.empty:
        return None

    linhas = [["Competência", "Dentro", "Fora", "Total", "% Dentro", "% Fora"]]
    for _, row in mensal.iterrows():
        linhas.append(
            [
                str(row["Competencia"]),
                _numero(row["Quantidade_Dentro"]),
                _numero(row["Quantidade_Fora"]),
                _numero(row["Total"]),
                _percentual(row["Percentual_Dentro"]),
                _percentual(row["Percentual_Fora"]),
            ]
        )

    tabela = Table(linhas, repeatRows=1)
    tabela._argW = [30*mm, 24*mm, 24*mm, 24*mm, 30*mm, 30*mm]
    tabela.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(VERDE)),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ALIGN", (1, 1), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#DCE4D7")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F9F5")]),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return tabela


def gerar_relatorio_pdf(
    *,
    secoes_efetivacao: list[dict],
    movimentacoes: dict,
    meta_sla: float,
    sla_movimentacao_dias: int,
    filtros: dict,
    origem_efetivacao: str | None = None,
    origem_movimentacoes: str | None = None,
    logo_path: str | Path | None = None,
) -> bytes:
    """Gera o relatório gerencial completo em PDF e devolve os bytes."""

    buffer = BytesIO()
    styles = _styles()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=17 * mm,
        bottomMargin=16 * mm,
        title="Relatório Gerencial - Indicador Operacional Mediatorie",
        author="Mediatorie Administradora de Benefícios",
    )

    story = []

    logo = Path(logo_path) if logo_path else None
    if logo and logo.exists():
        img = Image(str(logo))
        proporcao = img.imageHeight / img.imageWidth
        img.drawWidth = 56 * mm
        img.drawHeight = 56 * proporcao * mm
        story += [img, Spacer(1, 5 * mm)]

    story.append(Paragraph("Relatório Gerencial - Indicador Operacional", styles["MediatorieTitle"]))
    story.append(
        Paragraph(
            "Acompanhamento de efetivações de Saúde e Odonto e do indicador de Movimentações.",
            styles["MediatorieSubtitle"],
        )
    )
    story.append(Spacer(1, 4 * mm))

    gerado_em = datetime.now().strftime("%d/%m/%Y %H:%M")
    capa_dados = [
        ["Gerado em", gerado_em],
        ["Meta de cumprimento", _percentual(meta_sla)],
        ["SLA Efetivação", "Até 1 dia útil"],
        ["SLA Movimentações", f"Até {int(sla_movimentacao_dias)} dia(s) útil(eis)"],
        ["Segmento(s)", ", ".join(map(str, filtros.get("tipos", []))) or "Todos"],
        ["Competência(s)", ", ".join(map(str, filtros.get("competencias", []))) or "Todas"],
        ["Base de efetivações", origem_efetivacao or "Upload"],
        ["Base de movimentações", origem_movimentacoes or "Upload"],
    ]
    tabela_capa = Table(capa_dados, colWidths=[48 * mm, 116 * mm])
    tabela_capa.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EEF5E5")),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor(VERDE_ESCURO)),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#DCE4D7")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story += [tabela_capa, Spacer(1, 6 * mm)]

    story.append(
        Paragraph(
            "Este relatório utiliza o mesmo recorte e as mesmas regras exibidas no dashboard no momento da geração.",
            styles["BodyMediatorie"],
        )
    )
    story.append(PageBreak())

    # Efetivação: visão geral, Saúde e Odonto.
    for indice, secao in enumerate(secoes_efetivacao):
        titulo = secao["titulo"]
        resumo = secao["resumo"]
        mensal = secao["mensal"]
        ranking = secao["ranking"]

        story.append(Paragraph(f"Efetivação - {titulo}", styles["Section"]))
        story.append(
            _kpi_table(
                resumo,
                [
                    ("Efetivações", "total"),
                    ("Dentro do SLA", "dentro"),
                    ("Fora do SLA", "fora"),
                    ("Cumprimento", "percentual_dentro"),
                ],
            )
        )
        story.append(Spacer(1, 4 * mm))

        if resumo.get("sem_data", 0):
            story.append(
                Paragraph(
                    f"Registros sem uma das datas obrigatórias: {_numero(resumo['sem_data'])}. "
                    "Eles não entram no cálculo do SLA.",
                    styles["Small"],
                )
            )
            story.append(Spacer(1, 2 * mm))

        story.append(_fig_para_imagem(
            _grafico_percentual(mensal, f"Cumprimento do SLA - {titulo}", meta_sla)
        ))
        story.append(Spacer(1, 3 * mm))
        story.append(_fig_para_imagem(
            _grafico_quantidade_efetivacao(mensal, f"Volume mensal - {titulo}")
        ))
        story.append(Spacer(1, 3 * mm))
        story.append(_fig_para_imagem(
            _grafico_ranking(ranking, f"Produtos com mais efetivações fora do SLA - {titulo}")
        ))
        story.append(Spacer(1, 3 * mm))

        tabela_mensal = _table_mensal_efetivacao(mensal)
        if tabela_mensal is not None:
            story.append(Paragraph("Consolidação mensal", styles["BodyMediatorie"]))
            story.append(tabela_mensal)

        if indice < len(secoes_efetivacao) - 1:
            story.append(PageBreak())

    story.append(PageBreak())

    # Movimentações.
    story.append(Paragraph("Indicador de Movimentações", styles["Section"]))
    resumo_mov = movimentacoes["resumo"]
    mensal_mov = movimentacoes["mensal"]

    story.append(
        _kpi_table(
            resumo_mov,
            [
                ("Movimentações", "total"),
                ("Dentro do prazo", "dentro"),
                ("Fora do prazo", "fora"),
                ("Cumprimento", "percentual_dentro"),
            ],
        )
    )
    story.append(Spacer(1, 4 * mm))

    verificar = int(resumo_mov.get("verificar", 0))
    if verificar:
        story.append(
            Paragraph(
                f"Registros sem uma das datas obrigatórias: {_numero(verificar)}. "
                "Eles ficam como Verificar e não entram nos gráficos.",
                styles["Small"],
            )
        )
        story.append(Spacer(1, 2 * mm))

    story.append(_fig_para_imagem(
        _grafico_movimentacoes(mensal_mov, percentual=False, meta=meta_sla)
    ))
    story.append(Spacer(1, 3 * mm))
    story.append(_fig_para_imagem(
        _grafico_movimentacoes(mensal_mov, percentual=True, meta=meta_sla)
    ))
    story.append(Spacer(1, 3 * mm))

    tabela_mov = _table_mensal_movimentacoes(mensal_mov)
    if tabela_mov is not None:
        story.append(Paragraph("Consolidação mensal", styles["BodyMediatorie"]))
        story.append(tabela_mov)

    story.append(PageBreak())

    # Regras.
    story.append(Paragraph("Regras utilizadas no relatório", styles["Section"]))
    regras = [
        ["Indicador", "Regra"],
        ["Efetivação", "Vigência Inicio x Data Efetivação em dias úteis."],
        ["Prazo de Efetivação", "Até 1 dia útil = Dentro do SLA; acima de 1 dia útil = Fora do SLA."],
        ["Competência de Efetivação", "Definida pela Vigência Inicio."],
        ["Saúde / Odonto", "Segmentação conforme a classificação de produtos do processamento oficial."],
        ["Movimentações", "Dt.Modificação x Dt.Entrada SAP em dias úteis."],
        ["Prazo de Movimentações", f"Até {int(sla_movimentacao_dias)} dia(s) útil(eis) = Dentro; acima = Fora."],
        ["Período de Movimentações", "Gráficos consideram competências a partir de 01/2026."],
        ["Meta visual", f"{_percentual(meta_sla)} de cumprimento."],
    ]
    tabela_regras = Table(regras, colWidths=[48 * mm, 116 * mm], repeatRows=1)
    tabela_regras.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(VERDE)),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#DCE4D7")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F9F5")]),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(tabela_regras)

    def _pagina(canvas, doc_obj):
        canvas.saveState()
        largura, altura = A4
        canvas.setStrokeColor(colors.HexColor(VERDE))
        canvas.setLineWidth(1.2)
        canvas.line(16 * mm, altura - 11 * mm, largura - 16 * mm, altura - 11 * mm)

        canvas.setFont("Helvetica-Bold", 7.5)
        canvas.setFillColor(colors.HexColor(VERDE_ESCURO))
        canvas.drawString(16 * mm, altura - 8.5 * mm, "MEDIATORIE | INDICADOR OPERACIONAL")

        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor(CINZA))
        canvas.drawRightString(
            largura - 16 * mm,
            9 * mm,
            f"Página {doc_obj.page}",
        )
        canvas.drawString(
            16 * mm,
            9 * mm,
            "Mediatorie Administradora de Benefícios",
        )
        canvas.restoreState()

    doc.build(story, onFirstPage=_pagina, onLaterPages=_pagina)
    buffer.seek(0)
    return buffer.getvalue()
