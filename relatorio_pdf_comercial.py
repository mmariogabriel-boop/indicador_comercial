"""Relatório gerencial em PDF do Dashboard Comercial Mediatorie."""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    PageBreak,
)


VERDE = "#86BC25"
VERDE_ESCURO = "#5F8E16"
GRAFITE = "#404640"
CINZA = "#6B736D"
CINZA_CLARO = "#F3F6F1"
VERMELHO = "#D64545"


def _numero(valor) -> str:
    try:
        return f"{int(valor):,}".replace(",", ".")
    except Exception:
        return "0"


def _percentual(valor) -> str:
    try:
        return f"{float(valor):.1f}%".replace(".", ",")
    except Exception:
        return "0,0%"


def _resumir_filtro(valores, total_opcoes: int | None = None) -> str:
    valores = list(valores or [])

    if total_opcoes is not None and len(valores) == total_opcoes:
        return f"Todos ({total_opcoes})"

    if not valores:
        return "Nenhum"

    if len(valores) <= 6:
        return ", ".join(map(str, valores))

    primeiros = ", ".join(map(str, valores[:6]))
    return f"{primeiros} e mais {len(valores) - 6}"


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
            spaceAfter=8,
        )
    )

    styles.add(
        ParagraphStyle(
            name="MediatorieSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10.5,
            leading=14,
            textColor=colors.HexColor(CINZA),
            alignment=TA_CENTER,
            spaceAfter=10,
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
            spaceBefore=5,
            spaceAfter=8,
        )
    )

    styles.add(
        ParagraphStyle(
            name="BodyMediatorie",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9.2,
            leading=13,
            textColor=colors.HexColor(GRAFITE),
            spaceAfter=5,
        )
    )

    styles.add(
        ParagraphStyle(
            name="SmallMediatorie",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor(CINZA),
        )
    )

    return styles


def _table_text(texto, *, bold: bool = False, color: str = GRAFITE, size: float = 7.8):
    return Paragraph(
        str(texto),
        ParagraphStyle(
            name=f"cell_{id(texto)}_{size}_{bold}",
            fontName="Helvetica-Bold" if bold else "Helvetica",
            fontSize=size,
            leading=size + 2,
            textColor=colors.HexColor(color),
            spaceAfter=0,
            spaceBefore=0,
        ),
    )


def _fig_para_imagem(fig, largura_mm: float = 176) -> Image:
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


def _kpi_table(kpis: list[tuple[str, str]]):
    headers = [item[0] for item in kpis]
    valores = [item[1] for item in kpis]

    largura = 174 / max(len(kpis), 1)

    tabela = Table(
        [headers, valores],
        colWidths=[largura * mm] * len(kpis),
    )

    tabela.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF5E5")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor(VERDE_ESCURO)),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#DDE6D8")),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return tabela


def _grafico_competencia(saude: pd.DataFrame, odonto: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(10.8, 4.7))

    competencias = sorted(
        set(saude["Competencia"].dropna().tolist())
        | set(odonto["Competencia"].dropna().tolist())
    )

    if not competencias:
        ax.text(0.5, 0.5, "Sem dados no recorte selecionado", ha="center", va="center")
        ax.axis("off")
        return fig

    mapa_s = dict(zip(saude["Competencia"], saude["Descrição Beneficiário"]))
    mapa_o = dict(zip(odonto["Competencia"], odonto["Descrição Beneficiário"]))

    labels = [pd.Timestamp(c).strftime("%m/%Y") for c in competencias]
    valores_s = np.array([int(mapa_s.get(c, 0)) for c in competencias])
    valores_o = np.array([int(mapa_o.get(c, 0)) for c in competencias])

    x = np.arange(len(labels))
    width = 0.38

    ax.bar(x - width / 2, valores_s, width, label="Saúde", color=VERDE)
    ax.bar(x + width / 2, valores_o, width, label="Odonto", color="#6F7772")

    for i, valor in enumerate(valores_s):
        if valor:
            ax.text(i - width / 2, valor, f"{valor}", ha="center", va="bottom", fontsize=8)

    for i, valor in enumerate(valores_o):
        if valor:
            ax.text(i + width / 2, valor, f"{valor}", ha="center", va="bottom", fontsize=8)

    ax.set_title("Produção por competência", loc="left", fontweight="bold")
    ax.set_ylabel("Beneficiários")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=35, ha="right")
    ax.grid(axis="y", alpha=0.18)
    ax.legend(frameon=False, ncol=2, loc="upper center", bbox_to_anchor=(0.5, 1.12))
    fig.tight_layout()
    return fig


def _grafico_meta(comparativo: pd.DataFrame, coluna_meta: str, titulo: str):
    fig, ax = plt.subplots(figsize=(10.8, 4.6))

    if comparativo.empty:
        ax.text(0.5, 0.5, "Sem dados no recorte selecionado", ha="center", va="center")
        ax.axis("off")
        return fig

    dados = comparativo.sort_values("Competencia").copy()
    labels = dados["Competencia"].dt.strftime("%m/%Y").tolist()
    vendido = dados["Vendido"].astype(float).to_numpy()
    meta = dados[coluna_meta].astype(float).to_numpy()

    x = np.arange(len(labels))
    width = 0.38

    ax.bar(x - width / 2, meta, width, label="Meta", color="#8B908D")
    ax.bar(x + width / 2, vendido, width, label="Vendido", color=VERDE)

    for i, valor in enumerate(meta):
        ax.text(i - width / 2, valor, f"{int(valor)}", ha="center", va="bottom", fontsize=7.5)

    for i, valor in enumerate(vendido):
        ax.text(i + width / 2, valor, f"{int(valor)}", ha="center", va="bottom", fontsize=7.5)

    ax.set_title(titulo, loc="left", fontweight="bold")
    ax.set_ylabel("Quantidade")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=35, ha="right")
    ax.grid(axis="y", alpha=0.18)
    ax.legend(frameon=False, ncol=2, loc="upper center", bbox_to_anchor=(0.5, 1.12))
    fig.tight_layout()
    return fig


def _grafico_ranking(
    ranking: pd.DataFrame,
    coluna_nome: str,
    titulo: str,
    limite: int = 10,
):
    fig, ax = plt.subplots(figsize=(10.8, 5.0))

    if ranking.empty:
        ax.text(0.5, 0.5, "Sem dados no recorte selecionado", ha="center", va="center")
        ax.axis("off")
        return fig

    dados = ranking.head(limite).copy()
    dados = dados.sort_values("Quantidade", ascending=True)

    nomes = (
        dados[coluna_nome]
        .astype(str)
        .map(lambda texto: texto if len(texto) <= 48 else texto[:45] + "...")
    )
    valores = dados["Quantidade"].astype(int)

    ax.barh(nomes, valores, color=VERDE)
    for i, valor in enumerate(valores):
        ax.text(valor, i, f" {int(valor)}", va="center", fontsize=8)

    ax.set_title(titulo, loc="left", fontweight="bold")
    ax.set_xlabel("Quantidade de beneficiários")
    ax.grid(axis="x", alpha=0.18)
    fig.tight_layout()
    return fig


def _grafico_executivos(df_exec: pd.DataFrame, titulo: str):
    fig, ax = plt.subplots(figsize=(10.8, 4.9))

    if df_exec.empty:
        ax.text(0.5, 0.5, "Sem dados no recorte selecionado", ha="center", va="center")
        ax.axis("off")
        return fig

    ranking = (
        df_exec.groupby("NOME", dropna=False)["Id Corretora"]
        .sum()
        .sort_values(ascending=False)
        .head(12)
        .sort_values(ascending=True)
    )

    nomes = ranking.index.astype(str).map(
        lambda texto: texto if len(texto) <= 42 else texto[:39] + "..."
    )
    valores = ranking.astype(int)

    ax.barh(nomes, valores, color=VERDE)
    for i, valor in enumerate(valores):
        ax.text(valor, i, f" {int(valor)}", va="center", fontsize=8)

    ax.set_title(titulo, loc="left", fontweight="bold")
    ax.set_xlabel("Produção no período selecionado")
    ax.grid(axis="x", alpha=0.18)
    fig.tight_layout()
    return fig


def _grafico_tipo_produto(df_tipo: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(10.8, 4.3))

    if df_tipo.empty:
        ax.text(0.5, 0.5, "Sem dados no recorte selecionado", ha="center", va="center")
        ax.axis("off")
        return fig

    dados = df_tipo.sort_values("Quantidade", ascending=False).copy()

    ax.bar(
        dados["Tipo Produto"].astype(str),
        dados["Quantidade"].astype(int),
        color=VERDE,
    )

    for i, valor in enumerate(dados["Quantidade"].astype(int)):
        ax.text(i, valor, f"{valor}", ha="center", va="bottom", fontsize=8)

    ax.set_title("Produção por tipo de produto", loc="left", fontweight="bold")
    ax.set_ylabel("Beneficiários")
    ax.grid(axis="y", alpha=0.18)
    fig.tight_layout()
    return fig



VENDEDORES_INTERNOS_ORDEM = [
    "RENAN AVELINO RICARDO",
    "GENIANE CAUS",
    "FERNANDA PEREIRA SANTANA",
]


def _grafico_vendedores_internos_total(
    dados: pd.DataFrame,
):
    fig, ax = plt.subplots(
        figsize=(10.8, 4.7)
    )

    if dados.empty:
        ax.text(
            0.5,
            0.5,
            "Sem vendas dos vendedores internos no recorte selecionado",
            ha="center",
            va="center",
        )
        ax.axis("off")
        return fig

    base = (
        dados
        .groupby(
            [
                "Vendedor Interno",
                "Segmento",
            ],
            dropna=False,
        )
        ["Quantidade"]
        .sum()
        .reset_index()
    )

    vendedores = [
        vendedor
        for vendedor in VENDEDORES_INTERNOS_ORDEM
        if vendedor in base["Vendedor Interno"].tolist()
    ]

    for vendedor in base["Vendedor Interno"].dropna().unique():
        if vendedor not in vendedores:
            vendedores.append(vendedor)

    saude = []
    odonto = []

    for vendedor in vendedores:
        dados_vendedor = base[
            base["Vendedor Interno"].eq(vendedor)
        ]

        saude.append(
            int(
                dados_vendedor.loc[
                    dados_vendedor["Segmento"].eq("Saúde"),
                    "Quantidade",
                ].sum()
            )
        )

        odonto.append(
            int(
                dados_vendedor.loc[
                    dados_vendedor["Segmento"].eq("Odonto"),
                    "Quantidade",
                ].sum()
            )
        )

    x = np.arange(len(vendedores))
    width = 0.36

    ax.bar(
        x - width / 2,
        saude,
        width,
        label="Saúde",
        color=VERDE,
    )

    ax.bar(
        x + width / 2,
        odonto,
        width,
        label="Odonto",
        color="#6F7772",
    )

    for i, valor in enumerate(saude):
        if valor:
            ax.text(
                i - width / 2,
                valor,
                str(valor),
                ha="center",
                va="bottom",
                fontsize=8,
                fontweight="bold",
            )

    for i, valor in enumerate(odonto):
        if valor:
            ax.text(
                i + width / 2,
                valor,
                str(valor),
                ha="center",
                va="bottom",
                fontsize=8,
                fontweight="bold",
            )

    nomes_curto = [
        vendedor.title()
        for vendedor in vendedores
    ]

    ax.set_title(
        "Vendedores Internos - produção no período selecionado",
        loc="left",
        fontweight="bold",
    )

    ax.set_ylabel(
        "Quantidade de beneficiários"
    )

    ax.set_xticks(x)
    ax.set_xticklabels(
        nomes_curto,
        rotation=15,
        ha="right",
    )

    ax.grid(
        axis="y",
        alpha=0.18,
    )

    maior_total = max(
        saude + odonto
    ) if (saude or odonto) else 0

    if maior_total > 0:
        ax.set_ylim(
            0,
            maior_total * 1.20,
        )

    ax.legend(
        frameon=False,
        ncol=2,
        loc="upper right",
    )

    fig.tight_layout()

    return fig


def _grafico_vendedor_interno_competencia(
    dados: pd.DataFrame,
    vendedor: str,
):
    fig, ax = plt.subplots(
        figsize=(10.8, 4.7)
    )

    base = dados[
        dados["Vendedor Interno"].eq(vendedor)
    ].copy()

    if base.empty:
        ax.text(
            0.5,
            0.5,
            "Sem vendas no recorte selecionado",
            ha="center",
            va="center",
        )
        ax.axis("off")
        return fig

    competencias_base = (
        base[
            [
                "Competencia_Data",
                "Competencia",
            ]
        ]
        .drop_duplicates()
        .sort_values("Competencia_Data")
    )

    competencias = competencias_base[
        "Competencia"
    ].astype(str).tolist()

    labels = []

    for competencia in competencias:
        try:
            labels.append(
                pd.to_datetime(
                    competencia,
                    format="%m/%Y",
                    errors="coerce",
                ).strftime("%m/%Y")
            )
        except Exception:
            labels.append(str(competencia))

    saude = []
    odonto = []

    for competencia in competencias:
        base_comp = base[
            base["Competencia"].astype(str).eq(
                str(competencia)
            )
        ]

        saude.append(
            int(
                base_comp.loc[
                    base_comp["Segmento"].eq("Saúde"),
                    "Quantidade",
                ].sum()
            )
        )

        odonto.append(
            int(
                base_comp.loc[
                    base_comp["Segmento"].eq("Odonto"),
                    "Quantidade",
                ].sum()
            )
        )

    x = np.arange(len(labels))
    width = 0.36

    ax.bar(
        x - width / 2,
        saude,
        width,
        label="Saúde",
        color=VERDE,
    )

    ax.bar(
        x + width / 2,
        odonto,
        width,
        label="Odonto",
        color="#6F7772",
    )

    for i, valor in enumerate(saude):
        if valor:
            ax.text(
                i - width / 2,
                valor,
                str(valor),
                ha="center",
                va="bottom",
                fontsize=8,
            )

    for i, valor in enumerate(odonto):
        if valor:
            ax.text(
                i + width / 2,
                valor,
                str(valor),
                ha="center",
                va="bottom",
                fontsize=8,
            )

    ax.set_title(
        f"{vendedor.title()} - Saúde x Odonto por competência",
        loc="left",
        fontweight="bold",
        pad=14,
    )

    ax.set_ylabel(
        "Quantidade de beneficiários"
    )

    ax.set_xticks(x)
    ax.set_xticklabels(
        labels,
        rotation=35,
        ha="right",
    )

    maior_valor = max(
        saude + odonto
    ) if (saude or odonto) else 0

    if maior_valor > 0:
        ax.set_ylim(
            0,
            maior_valor * 1.22,
        )

    ax.grid(
        axis="y",
        alpha=0.18,
    )

    # A legenda fica dentro da área do gráfico, no canto superior direito,
    # sem disputar espaço com o título.
    ax.legend(
        frameon=False,
        ncol=2,
        loc="upper right",
    )

    fig.tight_layout()

    return fig


def _tabela_vendedor_interno(
    dados: pd.DataFrame,
    vendedor: str,
):
    base = dados[
        dados["Vendedor Interno"].eq(vendedor)
    ].copy()

    if base.empty:
        return None

    pivot = (
        base
        .pivot_table(
            index=[
                "Competencia_Data",
                "Competencia",
            ],
            columns="Segmento",
            values="Quantidade",
            aggfunc="sum",
            fill_value=0,
        )
        .reset_index()
        .sort_values("Competencia_Data")
    )

    for coluna in [
        "Saúde",
        "Odonto",
    ]:
        if coluna not in pivot.columns:
            pivot[coluna] = 0

    pivot["Total"] = (
        pivot["Saúde"]
        + pivot["Odonto"]
    )

    linhas = [
        [
            "Competência",
            "Saúde",
            "Odonto",
            "Total",
        ]
    ]

    for _, row in pivot.iterrows():
        linhas.append(
            [
                str(row["Competencia"]),
                _numero(row["Saúde"]),
                _numero(row["Odonto"]),
                _numero(row["Total"]),
            ]
        )

    tabela = Table(
        linhas,
        repeatRows=1,
        colWidths=[
            42 * mm,
            40 * mm,
            40 * mm,
            40 * mm,
        ],
    )

    tabela.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor(VERDE),
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.white,
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold",
                ),
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "ALIGN",
                    (1, 1),
                    (-1, -1),
                    "CENTER",
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.35,
                    colors.HexColor("#DDE6D8"),
                ),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [
                        colors.white,
                        colors.HexColor("#F8FAF6"),
                    ],
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
            ]
        )
    )

    return tabela




def _grafico_pipeline_vendedor_pdf(
    dados: pd.DataFrame,
):
    fig, ax = plt.subplots(
        figsize=(10.8, 4.4)
    )

    if dados.empty:
        ax.text(
            0.5,
            0.5,
            "Sem previsão de vendas carregada",
            ha="center",
            va="center",
        )
        ax.axis("off")
        return fig

    resumo = (
        dados
        .groupby(
            "Vendedor",
            dropna=False,
        )
        ["Vidas"]
        .sum()
        .sort_values(
            ascending=False
        )
    )

    nomes = [
        str(nome).title()
        for nome in resumo.index
    ]

    valores = resumo.astype(int).tolist()

    x = np.arange(
        len(nomes)
    )

    ax.bar(
        x,
        valores,
        color=VERDE,
    )

    for i, valor in enumerate(valores):
        ax.text(
            i,
            valor,
            _numero(valor),
            ha="center",
            va="bottom",
            fontsize=8.5,
            fontweight="bold",
        )

    if valores:
        ax.set_ylim(
            0,
            max(valores) * 1.18,
        )

    ax.set_title(
        "Previsão de Vendas - vidas prospectadas por vendedor",
        loc="left",
        fontweight="bold",
    )

    ax.set_ylabel(
        "Vidas"
    )

    ax.set_xticks(x)
    ax.set_xticklabels(
        nomes,
        rotation=12,
        ha="right",
    )

    ax.grid(
        axis="y",
        alpha=0.18,
    )

    fig.tight_layout()

    return fig


def _quebrar_status_pdf(
    texto: object,
    largura: int = 42,
) -> str:
    texto = str(texto)

    if len(texto) <= largura:
        return texto

    palavras = texto.split()
    linhas = []
    linha = []

    tamanho = 0

    for palavra in palavras:
        novo_tamanho = (
            tamanho
            + len(palavra)
            + (1 if linha else 0)
        )

        if novo_tamanho > largura and linha:
            linhas.append(
                " ".join(linha)
            )
            linha = [palavra]
            tamanho = len(palavra)
        else:
            linha.append(palavra)
            tamanho = novo_tamanho

    if linha:
        linhas.append(
            " ".join(linha)
        )

    return "\n".join(
        linhas[:3]
    )


def _grafico_pipeline_status_pdf(
    dados: pd.DataFrame,
):
    fig, ax = plt.subplots(
        figsize=(10.8, 6.0)
    )

    if dados.empty:
        ax.text(
            0.5,
            0.5,
            "Sem previsão de vendas carregada",
            ha="center",
            va="center",
        )
        ax.axis("off")
        return fig

    base = dados.copy()

    base["Status da Negociação"] = (
        base[
            "Status da Negociação"
        ]
        .astype("string")
        .fillna("Não informado")
        .str.strip()
        .replace(
            "",
            "Não informado",
        )
    )

    resumo = (
        base
        .groupby(
            "Status da Negociação",
            dropna=False,
        )
        ["Vidas"]
        .sum()
        .sort_values(
            ascending=False
        )
        .head(15)
        .sort_values(
            ascending=True
        )
    )

    nomes = [
        _quebrar_status_pdf(
            nome
        )
        for nome in resumo.index
    ]

    valores = resumo.astype(int).tolist()

    y = np.arange(
        len(nomes)
    )

    ax.barh(
        y,
        valores,
        color=VERDE,
    )

    for i, valor in enumerate(valores):
        ax.text(
            valor,
            i,
            f" {_numero(valor)}",
            va="center",
            fontsize=8,
        )

    ax.set_yticks(y)
    ax.set_yticklabels(
        nomes,
        fontsize=7.3,
    )

    ax.set_title(
        "Previsão de Vendas - vidas por status da negociação",
        loc="left",
        fontweight="bold",
    )

    ax.set_xlabel(
        "Vidas"
    )

    ax.grid(
        axis="x",
        alpha=0.18,
    )

    fig.tight_layout()

    return fig


def _tabela_pipeline_pdf(
    dados: pd.DataFrame,
):
    if dados.empty:
        return None

    base = dados.copy()

    base["Vidas"] = pd.to_numeric(
        base["Vidas"],
        errors="coerce",
    ).fillna(0).astype(int)

    linhas = [
        [
            _table_text(
                "Vendedor",
                bold=True,
                color="#FFFFFF",
                size=7.5,
            ),
            _table_text(
                "Empresa",
                bold=True,
                color="#FFFFFF",
                size=7.5,
            ),
            _table_text(
                "Status da Negociação",
                bold=True,
                color="#FFFFFF",
                size=7.5,
            ),
            _table_text(
                "Vidas",
                bold=True,
                color="#FFFFFF",
                size=7.5,
            ),
        ]
    ]

    for _, row in base.iterrows():
        linhas.append(
            [
                _table_text(
                    str(
                        row.get(
                            "Vendedor",
                            "",
                        )
                    ).title(),
                    size=7.0,
                ),
                _table_text(
                    row.get(
                        "Empresa",
                        "",
                    ),
                    size=7.0,
                ),
                _table_text(
                    row.get(
                        "Status da Negociação",
                        "",
                    ),
                    size=6.8,
                ),
                _table_text(
                    _numero(
                        row.get(
                            "Vidas",
                            0,
                        )
                    ),
                    size=7.0,
                ),
            ]
        )

    tabela = Table(
        linhas,
        repeatRows=1,
        colWidths=[
            39 * mm,
            49 * mm,
            64 * mm,
            18 * mm,
        ],
    )

    tabela.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor(
                        VERDE
                    ),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "ALIGN",
                    (3, 1),
                    (3, -1),
                    "CENTER",
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.35,
                    colors.HexColor(
                        "#DDE6D8"
                    ),
                ),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [
                        colors.white,
                        colors.HexColor(
                            "#F8FAF6"
                        ),
                    ],
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
            ]
        )
    )

    return tabela



def _tabela_dataframe(
    df: pd.DataFrame,
    colunas: list[str],
    headers: list[str] | None = None,
    formatos: dict[str, str] | None = None,
    max_linhas: int | None = None,
):
    dados = df.copy()

    if max_linhas is not None:
        dados = dados.head(max_linhas)

    dados = dados[colunas].copy()

    linhas = [[_table_text(h, bold=True, color="#FFFFFF", size=7.3) for h in (headers or colunas)]]

    formatos = formatos or {}

    for _, row in dados.iterrows():
        linha = []
        for coluna in colunas:
            valor = row[coluna]

            if coluna in formatos:
                tipo = formatos[coluna]
                if tipo == "data":
                    valor = pd.Timestamp(valor).strftime("%m/%Y") if pd.notna(valor) else ""
                elif tipo == "percentual":
                    valor = _percentual(valor)
                elif tipo == "numero":
                    valor = _numero(valor)

            linha.append(_table_text(valor, size=7.2))
        linhas.append(linha)

    n = max(len(colunas), 1)
    larguras = [174 / n * mm] * n

    tabela = Table(linhas, colWidths=larguras, repeatRows=1)

    tabela.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(VERDE)),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (1, 1), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#DDE6D8")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAF6")]),
                ("TOPPADDING", (0, 0), (-1, -1), 4.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
            ]
        )
    )

    return tabela


def gerar_relatorio_comercial_pdf(
    *,
    logo_path,
    origem_base: str,
    origem_carteira: str,
    filtros: dict,
    totais: dict,
    df_saude_comp: pd.DataFrame,
    df_odonto_comp: pd.DataFrame,
    comparativo_saude: pd.DataFrame,
    comparativo_odonto: pd.DataFrame,
    df_saude_exec: pd.DataFrame,
    df_odonto_exec: pd.DataFrame,
    df_produtos_ranking: pd.DataFrame,
    df_corretoras_ranking: pd.DataFrame,
    df_vendedores_ranking: pd.DataFrame,
    df_entidades_ranking: pd.DataFrame,
    df_tipo_produto: pd.DataFrame,
    df_vendedores_internos: pd.DataFrame,
    df_pipeline_vendas: pd.DataFrame,
) -> bytes:
    """Gera o relatório comercial gerencial completo em PDF."""

    buffer = BytesIO()
    styles = _styles()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=17 * mm,
        bottomMargin=16 * mm,
        title="Relatório Gerencial - Dashboard Comercial Mediatorie",
        author="Mediatorie Administradora de Benefícios",
    )

    story = []

    logo = Path(logo_path) if logo_path else None

    if logo and logo.exists():
        img = Image(str(logo))
        proporcao = img.imageHeight / img.imageWidth
        img.drawWidth = 57 * mm
        img.drawHeight = 57 * proporcao * mm
        story.extend([img, Spacer(1, 4 * mm)])

    story.append(
        Paragraph(
            "Relatório Gerencial - Dashboard Comercial",
            styles["MediatorieTitle"],
        )
    )
    story.append(
        Paragraph(
            "Produção comercial, metas e principais rankings do período selecionado.",
            styles["MediatorieSubtitle"],
        )
    )
    story.append(Spacer(1, 3 * mm))

    dados_capa = [
        ["Gerado em", datetime.now().strftime("%d/%m/%Y %H:%M")],
        ["Base Total", origem_base],
        ["Carteira de Executivos", origem_carteira],
        [
            "Competência",
            _resumir_filtro(
                filtros.get("competencias"),
                filtros.get("total_competencias"),
            ),
        ],
        [
            "Material",
            _resumir_filtro(
                filtros.get("materiais"),
                filtros.get("total_materiais"),
            ),
        ],
        [
            "Corretora",
            _resumir_filtro(
                filtros.get("corretoras"),
                filtros.get("total_corretoras"),
            ),
        ],
        [
            "Vendedor",
            _resumir_filtro(
                filtros.get("vendedores"),
                filtros.get("total_vendedores"),
            ),
        ],
    ]

    dados_capa = [
        [
            _table_text(chave, bold=True, color=VERDE_ESCURO, size=8.2),
            _table_text(valor, size=8.2),
        ]
        for chave, valor in dados_capa
    ]

    tabela_capa = Table(
        dados_capa,
        colWidths=[48 * mm, 116 * mm],
    )

    tabela_capa.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EEF5E5")),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor(VERDE_ESCURO)),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.2),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#DDE6D8")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    story.extend(
        [
            tabela_capa,
            Spacer(1, 5 * mm),
            Paragraph(
                "O relatório utiliza exatamente o recorte de filtros aplicado no dashboard no momento da geração.",
                styles["BodyMediatorie"],
            ),
            PageBreak(),
        ]
    )

    # =====================================================
    # RESUMO EXECUTIVO
    # =====================================================
    story.append(Paragraph("Resumo executivo", styles["Section"]))

    story.append(
        _kpi_table(
            [
                ("Saúde", _numero(totais.get("saude", 0))),
                ("Odonto", _numero(totais.get("odonto", 0))),
                ("Total", _numero(totais.get("total", 0))),
                ("Diferença > 0", _numero(totais.get("nao_corretos", 0))),
            ]
        )
    )

    story.append(Spacer(1, 4 * mm))

    story.append(
        _fig_para_imagem(
            _grafico_competencia(
                df_saude_comp,
                df_odonto_comp,
            )
        )
    )

    story.append(PageBreak())

    # =====================================================
    # METAS
    # =====================================================
    story.append(Paragraph("Vendido x Meta - Saúde", styles["Section"]))

    vendido_saude = int(comparativo_saude["Vendido"].sum()) if not comparativo_saude.empty else 0
    meta_saude = int(comparativo_saude["Meta Saúde Total"].sum()) if not comparativo_saude.empty else 0
    ating_saude = vendido_saude / meta_saude * 100 if meta_saude else 0
    dif_saude = vendido_saude - meta_saude

    story.append(
        _kpi_table(
            [
                ("Vendido", _numero(vendido_saude)),
                ("Meta", _numero(meta_saude)),
                ("Atingimento", _percentual(ating_saude)),
                ("Diferença", f"{dif_saude:+,}".replace(",", ".")),
            ]
        )
    )
    story.append(Spacer(1, 4 * mm))
    story.append(
        _fig_para_imagem(
            _grafico_meta(
                comparativo_saude,
                "Meta Saúde Total",
                "Saúde - Vendido x Meta Total",
            )
        )
    )

    if not comparativo_saude.empty:
        story.append(
            _tabela_dataframe(
                comparativo_saude,
                [
                    "Competencia",
                    "Meta Saúde Empresarial",
                    "Meta Coletivo por Adesão",
                    "Meta Saúde Total",
                    "Vendido",
                    "Atingimento (%)",
                ],
                headers=[
                    "Competência",
                    "Meta Empresarial",
                    "Meta Adesão",
                    "Meta Total",
                    "Vendido",
                    "Atingimento",
                ],
                formatos={
                    "Competencia": "data",
                    "Meta Saúde Empresarial": "numero",
                    "Meta Coletivo por Adesão": "numero",
                    "Meta Saúde Total": "numero",
                    "Vendido": "numero",
                    "Atingimento (%)": "percentual",
                },
            )
        )

    story.append(PageBreak())
    story.append(Paragraph("Vendido x Meta - Odonto", styles["Section"]))

    vendido_odonto = int(comparativo_odonto["Vendido"].sum()) if not comparativo_odonto.empty else 0
    meta_odonto = int(comparativo_odonto["Meta Odonto"].sum()) if not comparativo_odonto.empty else 0
    ating_odonto = vendido_odonto / meta_odonto * 100 if meta_odonto else 0
    dif_odonto = vendido_odonto - meta_odonto

    story.append(
        _kpi_table(
            [
                ("Vendido", _numero(vendido_odonto)),
                ("Meta", _numero(meta_odonto)),
                ("Atingimento", _percentual(ating_odonto)),
                ("Diferença", f"{dif_odonto:+,}".replace(",", ".")),
            ]
        )
    )
    story.append(Spacer(1, 4 * mm))
    story.append(
        _fig_para_imagem(
            _grafico_meta(
                comparativo_odonto,
                "Meta Odonto",
                "Odonto - Vendido x Meta",
            )
        )
    )

    if not comparativo_odonto.empty:
        story.append(
            _tabela_dataframe(
                comparativo_odonto,
                [
                    "Competencia",
                    "Meta Odonto",
                    "Vendido",
                    "Diferença",
                    "Atingimento (%)",
                ],
                headers=[
                    "Competência",
                    "Meta",
                    "Vendido",
                    "Diferença",
                    "Atingimento",
                ],
                formatos={
                    "Competencia": "data",
                    "Meta Odonto": "numero",
                    "Vendido": "numero",
                    "Diferença": "numero",
                    "Atingimento (%)": "percentual",
                },
            )
        )

    story.append(
        Paragraph(
            "Observação: quando Material, Corretora ou Vendedor estiverem filtrados, o campo Vendido representa o recorte selecionado, enquanto a meta permanece a meta corporativa mensal.",
            styles["SmallMediatorie"],
        )
    )

    story.append(PageBreak())

    # =====================================================
    # EXECUTIVOS
    # =====================================================
    story.append(
        Paragraph(
            "Produção por executivo",
            styles["Section"],
        )
    )

    story.append(
        Paragraph(
            "Saúde",
            styles["BodyMediatorie"],
        )
    )

    story.append(
        _fig_para_imagem(
            _grafico_executivos(
                df_saude_exec,
                "Saúde - produção por executivo",
            ),
            largura_mm=164,
        )
    )

    story.append(
        Spacer(
            1,
            5 * mm,
        )
    )

    story.append(
        Paragraph(
            "Odonto",
            styles["BodyMediatorie"],
        )
    )

    story.append(
        _fig_para_imagem(
            _grafico_executivos(
                df_odonto_exec,
                "Odonto - produção por executivo",
            ),
            largura_mm=164,
        )
    )

    story.append(PageBreak())

    # =====================================================
    # VENDEDORES INTERNOS
    # =====================================================
    story.append(
        Paragraph(
            "Vendedores Internos",
            styles["Section"],
        )
    )

    story.append(
        Paragraph(
            "Produção dos vendedores internos utilizando as mesmas regras homologadas do Dashboard Comercial. "
            "Esta visão considera o recorte de Competência, Material e Corretora utilizado pela aba Vendedores Internos.",
            styles["BodyMediatorie"],
        )
    )

    if df_vendedores_internos.empty:
        story.append(
            Paragraph(
                "Não foram encontradas vendas dos vendedores internos no recorte selecionado.",
                styles["BodyMediatorie"],
            )
        )
    else:
        total_saude_internos = int(
            df_vendedores_internos.loc[
                df_vendedores_internos["Segmento"].eq("Saúde"),
                "Quantidade",
            ].sum()
        )

        total_odonto_internos = int(
            df_vendedores_internos.loc[
                df_vendedores_internos["Segmento"].eq("Odonto"),
                "Quantidade",
            ].sum()
        )

        story.append(
            _kpi_table(
                [
                    (
                        "Saúde",
                        _numero(total_saude_internos),
                    ),
                    (
                        "Odonto",
                        _numero(total_odonto_internos),
                    ),
                    (
                        "Total",
                        _numero(
                            total_saude_internos
                            + total_odonto_internos
                        ),
                    ),
                    (
                        "Vendedores",
                        _numero(
                            df_vendedores_internos[
                                "Vendedor Interno"
                            ].nunique()
                        ),
                    ),
                ]
            )
        )

        story.append(
            Spacer(
                1,
                4 * mm,
            )
        )

        story.append(
            _fig_para_imagem(
                _grafico_vendedores_internos_total(
                    df_vendedores_internos
                )
            )
        )

        for vendedor in VENDEDORES_INTERNOS_ORDEM:
            story.append(
                PageBreak()
            )

            story.append(
                Paragraph(
                    vendedor.title(),
                    styles["Section"],
                )
            )

            base_vendedor = df_vendedores_internos[
                df_vendedores_internos[
                    "Vendedor Interno"
                ].eq(vendedor)
            ].copy()

            total_saude_vendedor = int(
                base_vendedor.loc[
                    base_vendedor["Segmento"].eq("Saúde"),
                    "Quantidade",
                ].sum()
            )

            total_odonto_vendedor = int(
                base_vendedor.loc[
                    base_vendedor["Segmento"].eq("Odonto"),
                    "Quantidade",
                ].sum()
            )

            story.append(
                _kpi_table(
                    [
                        (
                            "Saúde",
                            _numero(
                                total_saude_vendedor
                            ),
                        ),
                        (
                            "Odonto",
                            _numero(
                                total_odonto_vendedor
                            ),
                        ),
                        (
                            "Total",
                            _numero(
                                total_saude_vendedor
                                + total_odonto_vendedor
                            ),
                        ),
                    ]
                )
            )

            story.append(
                Spacer(
                    1,
                    4 * mm,
                )
            )

            story.append(
                _fig_para_imagem(
                    _grafico_vendedor_interno_competencia(
                        df_vendedores_internos,
                        vendedor,
                    )
                )
            )

            tabela_interno = (
                _tabela_vendedor_interno(
                    df_vendedores_internos,
                    vendedor,
                )
            )

            if tabela_interno is not None:
                story.append(
                    Spacer(
                        1,
                        3 * mm,
                    )
                )

                story.append(
                    Paragraph(
                        "Consolidação por competência",
                        styles["BodyMediatorie"],
                    )
                )

                story.append(
                    tabela_interno
                )

    story.append(PageBreak())

    # =====================================================
    # PREVISÃO DE VENDAS
    # =====================================================
    story.append(
        Paragraph(
            "Previsão de Vendas",
            styles["Section"],
        )
    )

    story.append(
        Paragraph(
            "Pipeline dos vendedores internos conforme a base carregada e os filtros de Vendedor e Status da Negociação utilizados na aba Previsão de Vendas.",
            styles["BodyMediatorie"],
        )
    )

    if df_pipeline_vendas.empty:
        story.append(
            Paragraph(
                "Nenhum registro de previsão de vendas estava disponível no momento da geração do relatório.",
                styles["BodyMediatorie"],
            )
        )
    else:
        total_oportunidades_pipeline = len(
            df_pipeline_vendas
        )

        total_vidas_pipeline = int(
            pd.to_numeric(
                df_pipeline_vendas["Vidas"],
                errors="coerce",
            )
            .fillna(0)
            .sum()
        )

        total_vendedores_pipeline = int(
            df_pipeline_vendas[
                "Vendedor"
            ].nunique()
        )

        status_pipeline_pdf = (
            df_pipeline_vendas[
                "Status da Negociação"
            ]
            .astype("string")
            .fillna("Não informado")
            .str.strip()
            .replace(
                "",
                "Não informado",
            )
        )

        total_status_pipeline = int(
            status_pipeline_pdf.nunique()
        )

        story.append(
            _kpi_table(
                [
                    (
                        "Oportunidades",
                        _numero(
                            total_oportunidades_pipeline
                        ),
                    ),
                    (
                        "Vidas prospectadas",
                        _numero(
                            total_vidas_pipeline
                        ),
                    ),
                    (
                        "Vendedores",
                        _numero(
                            total_vendedores_pipeline
                        ),
                    ),
                    (
                        "Status distintos",
                        _numero(
                            total_status_pipeline
                        ),
                    ),
                ]
            )
        )

        story.append(
            Spacer(
                1,
                4 * mm,
            )
        )

        # Um gráfico por linha, para preservar legibilidade no PDF.
        story.append(
            _fig_para_imagem(
                _grafico_pipeline_vendedor_pdf(
                    df_pipeline_vendas
                ),
                largura_mm=164,
            )
        )

        story.append(
            Spacer(
                1,
                5 * mm,
            )
        )

        story.append(
            _fig_para_imagem(
                _grafico_pipeline_status_pdf(
                    df_pipeline_vendas
                ),
                largura_mm=164,
            )
        )

        story.append(
            PageBreak()
        )

        story.append(
            Paragraph(
                "Oportunidades da Previsão de Vendas",
                styles["Section"],
            )
        )

        tabela_pipeline = (
            _tabela_pipeline_pdf(
                df_pipeline_vendas
            )
        )

        if tabela_pipeline is not None:
            story.append(
                tabela_pipeline
            )

    story.append(PageBreak())

    # =====================================================
    # RANKINGS
    # =====================================================
    rankings = [
        (
            df_produtos_ranking,
            "Descrição Material",
            "Produtos mais vendidos",
        ),
        (
            df_corretoras_ranking,
            "Descrição Corretora",
            "Maiores corretoras",
        ),
        (
            df_vendedores_ranking,
            "Descrição Vendedor",
            "Maiores vendedores",
        ),
        (
            df_entidades_ranking,
            "Descrição Entidade",
            "Ranking por entidade",
        ),
    ]

    for indice, (ranking, coluna, titulo) in enumerate(rankings):
        story.append(Paragraph(titulo, styles["Section"]))
        story.append(
            _fig_para_imagem(
                _grafico_ranking(
                    ranking,
                    coluna,
                    titulo,
                    limite=10,
                )
            )
        )

        if not ranking.empty:
            story.append(
                _tabela_dataframe(
                    ranking,
                    [coluna, "Quantidade"],
                    headers=[titulo.replace("Maiores ", "").replace("Ranking por ", "").capitalize(), "Quantidade"],
                    formatos={"Quantidade": "numero"},
                    max_linhas=10,
                )
            )

        if indice < len(rankings) - 1:
            story.append(PageBreak())

    story.append(PageBreak())

    # =====================================================
    # TIPO PRODUTO
    # =====================================================
    story.append(Paragraph("Tipo de produto", styles["Section"]))
    story.append(
        _fig_para_imagem(
            _grafico_tipo_produto(
                df_tipo_produto,
            )
        )
    )

    if not df_tipo_produto.empty:
        story.append(
            _tabela_dataframe(
                df_tipo_produto,
                ["Tipo Produto", "Quantidade"],
                headers=["Tipo de produto", "Quantidade"],
                formatos={"Quantidade": "numero"},
            )
        )

    story.append(PageBreak())

    # =====================================================
    # REGRAS
    # =====================================================
    story.append(Paragraph("Regras utilizadas", styles["Section"]))

    regras = [
        ["Regra", "Como o dashboard considera"],
        ["Movimentação", "Somente VIDA NOVA."],
        [
            "Cancelamento",
            "SEM JUSTA CAUSA, JUSTA CAUSA, A PEDIDO DO BENEFICIÁRIO (RN561), BENEFÍCIO DEMITIDO/APOSENTADO (RN279), DESLIGAMENTO DA EMPRESA (RN279), INADIMPLENTE ou campo vazio.",
        ],
        [
            "Validação de data",
            "Data Inclusão Vida - Data Início Beneficiário deve resultar em Diferença menor ou igual a zero.",
        ],
        ["Competência", "Definida pela Data Inclusão Vida e considerada a partir de 01/2026."],
        ["Saúde", "Id Acomodação diferente de ODO e SEM."],
        ["Odonto", "Id Acomodação igual a ODO."],
        ["Ambulatorial", "Id Acomodação igual a AMB."],
        ["Completo", "Id Acomodação igual a ENF ou QUA."],
        [
            "Rankings",
            "Contagem de beneficiários dentro da base válida e do recorte de filtros selecionado.",
        ],
    ]

    regras_formatadas = []
    for indice, (regra, descricao) in enumerate(regras):
        if indice == 0:
            regras_formatadas.append(
                [
                    _table_text(regra, bold=True, color="#FFFFFF", size=8),
                    _table_text(descricao, bold=True, color="#FFFFFF", size=8),
                ]
            )
        else:
            regras_formatadas.append(
                [
                    _table_text(regra, bold=True, size=7.8),
                    _table_text(descricao, size=7.8),
                ]
            )

    tabela_regras = Table(
        regras_formatadas,
        colWidths=[42 * mm, 122 * mm],
        repeatRows=1,
    )

    tabela_regras.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(VERDE)),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#DDE6D8")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAF6")]),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )

    story.append(tabela_regras)

    def _pagina(canvas, doc_obj):
        canvas.saveState()

        largura, altura = A4

        canvas.setStrokeColor(colors.HexColor(VERDE))
        canvas.setLineWidth(1.2)
        canvas.line(
            16 * mm,
            altura - 11 * mm,
            largura - 16 * mm,
            altura - 11 * mm,
        )

        canvas.setFont("Helvetica-Bold", 7.5)
        canvas.setFillColor(colors.HexColor(VERDE_ESCURO))
        canvas.drawString(
            16 * mm,
            altura - 8.5 * mm,
            "MEDIATORIE | DASHBOARD COMERCIAL",
        )

        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor(CINZA))
        canvas.drawString(
            16 * mm,
            9 * mm,
            "Mediatorie Administradora de Benefícios",
        )
        canvas.drawRightString(
            largura - 16 * mm,
            9 * mm,
            f"Página {doc_obj.page}",
        )

        canvas.restoreState()

    doc.build(
        story,
        onFirstPage=_pagina,
        onLaterPages=_pagina,
    )

    buffer.seek(0)
    return buffer.getvalue()
