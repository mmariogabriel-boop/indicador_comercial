"""Painel Streamlit do Indicador Operacional Mediatorie."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from relatorio_pdf import gerar_relatorio_pdf

import processamento as processamento_mod

from processamento import (
    COLUNA_PRODUTO,
    COLUNAS_OBRIGATORIAS,
    consolidar_mensal,
    processar_base,
    ranking_produtos_fora,
    resumo_operacional,
)

# Mantido localmente para o app não quebrar caso o servidor ainda esteja
# com uma versão antiga de processamento.py. A compatibilidade completa
# é validada logo abaixo e gera uma mensagem clara no painel.
COLUNA_EFETIVACAO = "Data Efetivação"
VERSAO_PROCESSAMENTO_ESPERADA = "2026-09-15-efetivacao-1diautil-v1"


BASE_DIR = Path(__file__).resolve().parent
LOGO_PATH = BASE_DIR / "assets" / "logo_mediatorie.png"
ARQUIVO_PADRAO = BASE_DIR / "base_efetivacao.xlsx"
ARQUIVO_MOVIMENTACOES_PADRAO = BASE_DIR / "base_movimentacoes.xlsx"
PERIODO_INICIAL_MOVIMENTACOES = pd.Period("2026-01", freq="M")

VERDE = "#86BC25"
VERDE_ESCURO = "#5F8E16"
VERMELHO = "#D64545"
GRAFITE = "#4B4F4D"
FUNDO = "#F5F7F2"


st.set_page_config(
    page_title="Indicador Operacional | Mediatorie",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# VALIDAÇÃO DE VERSÃO DO PROCESSAMENTO
# =========================================================
# Evita o ImportError genérico do Streamlit Cloud quando app.py e
# processamento.py são publicados em versões diferentes.
versao_processamento = getattr(processamento_mod, "VERSAO_PROCESSAMENTO", None)
if versao_processamento != VERSAO_PROCESSAMENTO_ESPERADA:
    st.error(
        "O arquivo `processamento.py` do servidor está desatualizado. "
        "Substitua `app.py` e `processamento.py` juntos pela mesma versão. "
        f"Versão esperada: {VERSAO_PROCESSAMENTO_ESPERADA}."
    )
    st.stop()


st.markdown(
    f"""
    <style>
        .stApp {{ background-color: {FUNDO}; }}
        [data-testid="stSidebar"] {{
            background: linear-gradient(180deg, #FFFFFF 0%, #F0F4EA 100%);
            border-right: 1px solid #DDE6D3;
        }}
        [data-testid="stMetric"] {{
            background-color: #FFFFFF;
            border: 1px solid #E2E8DC;
            border-left: 5px solid {VERDE};
            border-radius: 12px;
            padding: 15px 16px;
            box-shadow: 0 4px 14px rgba(75, 79, 77, 0.06);
        }}
        [data-testid="stMetricLabel"] {{ color: #667064; }}
        [data-testid="stMetricValue"] {{ color: {GRAFITE}; }}
        div[data-baseweb="tab-list"] {{ gap: 8px; }}
        button[data-baseweb="tab"] {{
            background-color: #FFFFFF;
            border-radius: 9px 9px 0 0;
            padding: 10px 18px;
        }}
        button[data-baseweb="tab"][aria-selected="true"] {{
            color: {VERDE_ESCURO};
            border-bottom-color: {VERDE};
        }}
        .mediatorie-header {{
            padding: 6px 0 18px 0;
        }}
        .mediatorie-kicker {{
            color: {VERDE_ESCURO};
            font-size: 0.85rem;
            font-weight: 700;
            letter-spacing: 0.12em;
            text-transform: uppercase;
        }}
        .mediatorie-title {{
            color: {GRAFITE};
            font-size: 2.05rem;
            font-weight: 750;
            line-height: 1.15;
            margin: 4px 0;
        }}
        .mediatorie-subtitle {{ color: #69736A; font-size: 1rem; }}
        .block-container {{ padding-top: 1.4rem; max-width: 1500px; }}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def ler_excel_upload(conteudo: bytes) -> pd.DataFrame:
    return pd.read_excel(BytesIO(conteudo))


@st.cache_data(show_spinner=False)
def ler_excel_local(caminho: str, ultima_alteracao: float) -> pd.DataFrame:
    del ultima_alteracao  # participa da chave do cache
    return pd.read_excel(caminho)


def percentual_br(valor: float) -> str:
    return f"{valor:.2f}%".replace(".", ",")


def cabecalho() -> None:
    logo, texto = st.columns([1.1, 4.9])
    with logo:
        st.image(str(LOGO_PATH), width=230)
    with texto:
        st.markdown(
            """
            <div class="mediatorie-header">
                <div class="mediatorie-kicker">Gestão de operações</div>
                <div class="mediatorie-title">Indicador Operacional</div>
                <div class="mediatorie-subtitle">
                    Acompanhamento das efetivações de Saúde e Odonto.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def grafico_percentual(mensal: pd.DataFrame, meta: float, titulo: str) -> go.Figure:
    fig = go.Figure()

    fig.add_bar(
        x=mensal["Comp"],
        y=mensal["Percentual_Dentro"],
        name="Dentro do SLA",
        marker_color=VERDE,
        text=mensal["Percentual_Dentro"].map(percentual_br),
        textposition="inside",
        insidetextanchor="middle",
        textfont=dict(color="#FFFFFF", size=12),
        customdata=mensal[["Dentro", "Total"]],
        hovertemplate=(
            "<b>%{x}</b><br>Dentro: %{customdata[0]:,.0f}"
            "<br>Total: %{customdata[1]:,.0f}<br>Percentual: %{y:.2f}%<extra></extra>"
        ),
    )
    fig.add_bar(
        x=mensal["Comp"],
        y=mensal["Percentual_Fora"],
        name="Fora do SLA",
        marker_color=VERMELHO,
        text=mensal["Percentual_Fora"].map(percentual_br),
        textposition="inside",
        insidetextanchor="middle",
        textfont=dict(color="#FFFFFF", size=12),
        customdata=mensal[["Fora", "Total"]],
        hovertemplate=(
            "<b>%{x}</b><br>Fora: %{customdata[0]:,.0f}"
            "<br>Total: %{customdata[1]:,.0f}<br>Percentual: %{y:.2f}%<extra></extra>"
        ),
    )
    fig.add_hline(
        y=meta,
        line_color=GRAFITE,
        line_dash="dot",
        line_width=2,
        annotation_text=f"Meta {percentual_br(meta)}",
        annotation_position="top right",
    )
    fig.update_layout(
        title=dict(
            text=f"{titulo}<br><sup>Participação mensal das efetivações dentro e fora do SLA</sup>",
            x=0.01,
        ),
        barmode="stack",
        barnorm="percent",
        height=470,
        margin=dict(l=35, r=25, t=85, b=55),
        legend=dict(orientation="h", y=1.11, x=1, xanchor="right"),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(family="Arial", color=GRAFITE),
        hovermode="x unified",
        uniformtext_minsize=10,
        uniformtext_mode="hide",
    )
    fig.update_yaxes(
        title="Percentual",
        range=[0, 100],
        ticksuffix="%",
        dtick=20,
        gridcolor="#E8EDE4",
        zeroline=False,
    )
    fig.update_xaxes(title="Competência", showgrid=False)
    return fig


def grafico_quantidade(mensal: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for coluna, nome, cor in [
        ("Dentro", "Dentro do SLA", VERDE),
        ("Fora", "Fora do SLA", VERMELHO),
    ]:
        fig.add_bar(
            x=mensal["Comp"],
            y=mensal[coluna],
            name=nome,
            marker_color=cor,
            text=mensal[coluna],
            textposition="inside",
            textfont=dict(color="#FFFFFF"),
            hovertemplate=f"<b>%{{x}}</b><br>{nome}: %{{y:,.0f}}<extra></extra>",
        )

    fig.update_layout(
        title=dict(text="Volume mensal<br><sup>Quantidade de efetivações por situação</sup>", x=0.01),
        barmode="stack",
        height=410,
        margin=dict(l=30, r=20, t=80, b=50),
        legend=dict(orientation="h", y=1.12, x=1, xanchor="right"),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(family="Arial", color=GRAFITE),
        hovermode="x unified",
        uniformtext_minsize=9,
        uniformtext_mode="hide",
    )
    fig.update_yaxes(title="Efetivações", gridcolor="#E8EDE4", zeroline=False)
    fig.update_xaxes(title="Competência", showgrid=False)
    return fig


def grafico_ranking(dados: pd.DataFrame) -> go.Figure | None:
    ranking = ranking_produtos_fora(dados)
    ranking = ranking.loc[ranking["Fora"].gt(0)].copy()
    if ranking.empty:
        return None

    nomes = ranking[COLUNA_PRODUTO].map(
        lambda texto: texto if len(texto) <= 38 else texto[:35] + "..."
    )
    fig = go.Figure(
        go.Bar(
            x=ranking["Fora"],
            y=nomes,
            orientation="h",
            marker_color=VERMELHO,
            text=ranking["Fora"],
            textposition="outside",
            customdata=ranking[[COLUNA_PRODUTO, "Total", "Percentual_Fora"]],
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>Fora: %{x:,.0f}"
                "<br>Total: %{customdata[1]:,.0f}"
                "<br>Percentual fora: %{customdata[2]:.2f}%<extra></extra>"
            ),
        )
    )
    fig.update_layout(
        title=dict(text="Atenção por produto<br><sup>Produtos com mais efetivações fora do SLA</sup>", x=0.01),
        height=410,
        margin=dict(l=20, r=45, t=80, b=50),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(family="Arial", color=GRAFITE),
        showlegend=False,
    )
    fig.update_xaxes(title="Quantidade fora", gridcolor="#E8EDE4", zeroline=False)
    fig.update_yaxes(title=None)
    return fig



# =========================================================
# MOVIMENTAÇÕES - SEGUNDA BASE
# =========================================================
COLUNAS_MOVIMENTACOES = ["Dt.Modificação", "Dt.Entrada SAP"]


def validar_colunas_movimentacoes(df: pd.DataFrame) -> None:
    faltantes = [coluna for coluna in COLUNAS_MOVIMENTACOES if coluna not in df.columns]
    if faltantes:
        raise KeyError(
            "Na base de movimentações faltam as colunas: " + ", ".join(faltantes)
        )


def calcular_dias_uteis_movimentacao(linha: pd.Series):
    data_modificacao = linha["Dt.Modificação"]
    data_entrada = linha["Dt.Entrada SAP"]

    if pd.isna(data_modificacao) or pd.isna(data_entrada):
        return np.nan

    return np.busday_count(
        data_modificacao.date().isoformat(),
        data_entrada.date().isoformat(),
    )


@st.cache_data(show_spinner=False)
def processar_movimentacoes(df_original: pd.DataFrame, sla_dias: int) -> pd.DataFrame:
    """Aplica a regra do indicador de movimentações na segunda planilha."""
    df = df_original.copy()
    df.columns = [str(coluna).strip() for coluna in df.columns]
    validar_colunas_movimentacoes(df)

    df["Dt.Modificação"] = pd.to_datetime(df["Dt.Modificação"], errors="coerce")
    df["Dt.Entrada SAP"] = pd.to_datetime(df["Dt.Entrada SAP"], errors="coerce")

    df["dias_uteis"] = df.apply(calcular_dias_uteis_movimentacao, axis=1).astype("Int64")

    condicoes = [
        df["dias_uteis"].le(sla_dias),
        df["dias_uteis"].gt(sla_dias),
    ]

    df["Indicador"] = np.select(
        [condicao.fillna(False).to_numpy(dtype=bool) for condicao in condicoes],
        ["Dentro do prazo", "Fora do prazo"],
        default="Verificar",
    )

    df["Periodo"] = df["Dt.Modificação"].dt.to_period("M")
    df["Competencia"] = df["Periodo"].dt.strftime("%m/%Y")
    df.loc[df["Periodo"].isna(), "Competencia"] = "Sem competência"

    return df


def consolidar_movimentacoes_mensal(df: pd.DataFrame) -> pd.DataFrame:
    """Consolida somente competências de 01/2026 em diante."""
    validos = df.loc[
        df["Indicador"].isin(["Dentro do prazo", "Fora do prazo"])
        & df["Periodo"].notna()
        & df["Periodo"].ge(PERIODO_INICIAL_MOVIMENTACOES)
    ].copy()

    if validos.empty:
        return pd.DataFrame(
            columns=[
                "Periodo",
                "Competencia",
                "Quantidade_Dentro",
                "Quantidade_Fora",
                "Total",
                "Percentual_Dentro",
                "Percentual_Fora",
            ]
        )

    mensal = (
        validos.groupby(["Periodo", "Competencia", "Indicador"], observed=False)
        .size()
        .unstack(fill_value=0)
        .reset_index()
        .rename(
            columns={
                "Dentro do prazo": "Quantidade_Dentro",
                "Fora do prazo": "Quantidade_Fora",
            }
        )
    )

    for coluna in ["Quantidade_Dentro", "Quantidade_Fora"]:
        if coluna not in mensal.columns:
            mensal[coluna] = 0

    mensal["Quantidade_Dentro"] = mensal["Quantidade_Dentro"].astype(int)
    mensal["Quantidade_Fora"] = mensal["Quantidade_Fora"].astype(int)
    mensal["Total"] = mensal["Quantidade_Dentro"] + mensal["Quantidade_Fora"]
    mensal["Percentual_Dentro"] = np.where(
        mensal["Total"].gt(0),
        mensal["Quantidade_Dentro"] / mensal["Total"] * 100,
        0,
    )
    mensal["Percentual_Fora"] = np.where(
        mensal["Total"].gt(0),
        mensal["Quantidade_Fora"] / mensal["Total"] * 100,
        0,
    )

    return mensal.sort_values("Periodo").reset_index(drop=True)


def grafico_movimentacoes_quantidade(mensal: pd.DataFrame) -> go.Figure:
    fig = go.Figure()

    fig.add_bar(
        x=mensal["Competencia"],
        y=mensal["Quantidade_Dentro"],
        name="Dentro do prazo",
        marker_color=VERDE,
        text=mensal["Quantidade_Dentro"].map(lambda valor: f"{int(valor)}" if valor > 0 else ""),
        textposition="inside",
        insidetextanchor="middle",
        textfont=dict(color="#000000", size=12),
        hovertemplate="<b>%{x}</b><br>Dentro do prazo: %{y:,.0f}<extra></extra>",
    )

    fig.add_bar(
        x=mensal["Competencia"],
        y=mensal["Quantidade_Fora"],
        name="Fora do prazo",
        marker_color=VERMELHO,
        text=mensal["Quantidade_Fora"].map(lambda valor: f"{int(valor)}" if valor > 0 else ""),
        textposition="inside",
        insidetextanchor="middle",
        textfont=dict(color="#000000", size=12),
        hovertemplate="<b>%{x}</b><br>Fora do prazo: %{y:,.0f}<extra></extra>",
    )

    fig.update_layout(
        title=dict(
            text="Movimentações por competência<br><sup>Quantidade dentro e fora do prazo — a partir de 01/2026</sup>",
            x=0.01,
        ),
        barmode="stack",
        height=460,
        margin=dict(l=35, r=25, t=85, b=55),
        legend=dict(orientation="h", y=1.11, x=1, xanchor="right"),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(family="Arial", color=GRAFITE),
        hovermode="x unified",
        uniformtext_minsize=10,
        uniformtext_mode="hide",
    )
    fig.update_yaxes(title="Quantidade", gridcolor="#E8EDE4", zeroline=False)
    fig.update_xaxes(title="Competência", showgrid=False)
    return fig


def grafico_movimentacoes_percentual(mensal: pd.DataFrame, meta: float) -> go.Figure:
    fig = go.Figure()

    fig.add_bar(
        x=mensal["Competencia"],
        y=mensal["Percentual_Dentro"],
        name="Dentro do prazo",
        marker_color=VERDE,
        text=mensal["Percentual_Dentro"].map(percentual_br),
        textposition="inside",
        insidetextanchor="middle",
        textfont=dict(color="#000000", size=12),
        customdata=mensal[["Quantidade_Dentro", "Total"]],
        hovertemplate=(
            "<b>%{x}</b><br>Dentro: %{customdata[0]:,.0f}"
            "<br>Total: %{customdata[1]:,.0f}<br>Percentual: %{y:.2f}%<extra></extra>"
        ),
    )

    fig.add_bar(
        x=mensal["Competencia"],
        y=mensal["Percentual_Fora"],
        name="Fora do prazo",
        marker_color=VERMELHO,
        text=mensal["Percentual_Fora"].map(percentual_br),
        textposition="inside",
        insidetextanchor="middle",
        textfont=dict(color="#000000", size=12),
        customdata=mensal[["Quantidade_Fora", "Total"]],
        hovertemplate=(
            "<b>%{x}</b><br>Fora: %{customdata[0]:,.0f}"
            "<br>Total: %{customdata[1]:,.0f}<br>Percentual: %{y:.2f}%<extra></extra>"
        ),
    )

    fig.add_hline(
        y=meta,
        line_color=GRAFITE,
        line_dash="dot",
        line_width=2,
        annotation_text=f"Meta {percentual_br(meta)}",
        annotation_position="top right",
    )

    fig.update_layout(
        title=dict(
            text="Percentual de movimentações por competência<br><sup>Participação dentro e fora do prazo — a partir de 01/2026</sup>",
            x=0.01,
        ),
        barmode="stack",
        height=460,
        margin=dict(l=35, r=25, t=85, b=55),
        legend=dict(orientation="h", y=1.11, x=1, xanchor="right"),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(family="Arial", color=GRAFITE),
        hovermode="x unified",
        uniformtext_minsize=10,
        uniformtext_mode="hide",
    )
    fig.update_yaxes(
        title="Percentual",
        range=[0, 100],
        ticksuffix="%",
        dtick=20,
        gridcolor="#E8EDE4",
        zeroline=False,
    )
    fig.update_xaxes(title="Competência", showgrid=False)
    return fig


def exibir_movimentacoes(dados_movimentacoes: pd.DataFrame, meta: float) -> None:
    mensal = consolidar_movimentacoes_mensal(dados_movimentacoes)

    if mensal.empty:
        st.warning("Não existem movimentações válidas a partir de 01/2026 para montar os gráficos.")
        return

    total = int(mensal["Total"].sum())
    dentro = int(mensal["Quantidade_Dentro"].sum())
    fora = int(mensal["Quantidade_Fora"].sum())
    percentual_dentro = (dentro / total * 100) if total else 0.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Movimentações", f"{total:,}".replace(",", "."))
    c2.metric("Dentro do prazo", f"{dentro:,}".replace(",", "."))
    c3.metric("Fora do prazo", f"{fora:,}".replace(",", "."))
    c4.metric("Cumprimento", percentual_br(percentual_dentro))

    st.plotly_chart(
        grafico_movimentacoes_quantidade(mensal),
        use_container_width=True,
        config={"displaylogo": False, "locale": "pt-BR"},
        key="grafico_movimentacoes_quantidade",
    )
    st.plotly_chart(
        grafico_movimentacoes_percentual(mensal, meta),
        use_container_width=True,
        config={"displaylogo": False, "locale": "pt-BR"},
        key="grafico_movimentacoes_percentual",
    )

    verificar = int(dados_movimentacoes["Indicador"].eq("Verificar").sum())
    if verificar:
        st.caption(
            f"⚠️ {verificar} registro(s) sem uma das datas obrigatórias foram classificados como Verificar e não entram nos gráficos."
        )

    with st.expander("Ver consolidação mensal das movimentações"):
        tabela = mensal.drop(columns="Periodo").rename(
            columns={
                "Quantidade_Dentro": "Dentro",
                "Quantidade_Fora": "Fora",
                "Percentual_Dentro": "% Dentro",
                "Percentual_Fora": "% Fora",
            }
        )
        st.dataframe(
            tabela,
            use_container_width=True,
            hide_index=True,
            column_config={
                "% Dentro": st.column_config.NumberColumn(format="%.2f%%"),
                "% Fora": st.column_config.NumberColumn(format="%.2f%%"),
            },
        )

def exibir_kpis(dados: pd.DataFrame) -> None:
    resumo = resumo_operacional(dados)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Efetivações", f"{resumo['total']:,}".replace(",", "."))
    col2.metric("Dentro do SLA", f"{resumo['dentro']:,}".replace(",", "."))
    col3.metric("Fora do SLA", f"{resumo['fora']:,}".replace(",", "."))
    col4.metric("Cumprimento do SLA", percentual_br(resumo["percentual_dentro"]))

    if resumo["sem_data"]:
        st.caption(
            f"⚠️ {resumo['sem_data']} registro(s) sem uma das datas obrigatórias "
            "não entram no cálculo do SLA."
        )


def exibir_secao(dados: pd.DataFrame, titulo: str, meta: float) -> None:
    if dados.empty:
        st.info(f"Não existem registros para {titulo.lower()} nos filtros selecionados.")
        return

    exibir_kpis(dados)
    mensal = consolidar_mensal(dados)
    if mensal.empty:
        st.warning("Não existem registros com datas válidas para montar os gráficos.")
        return

    st.plotly_chart(
        grafico_percentual(mensal, meta, f"Cumprimento do SLA — {titulo}"),
        use_container_width=True,
        config={"displaylogo": False, "locale": "pt-BR"},
        key=f"grafico_percentual_{titulo}",
    )

    coluna_grafico, coluna_ranking = st.columns([1.15, 0.85])
    with coluna_grafico:
        st.plotly_chart(
            grafico_quantidade(mensal),
            use_container_width=True,
            config={"displaylogo": False, "locale": "pt-BR"},
            key=f"grafico_quantidade_{titulo}",
        )
    with coluna_ranking:
        ranking = grafico_ranking(dados)
        if ranking is None:
            st.success("Nenhum produto fora do SLA nos filtros selecionados.")
        else:
            st.plotly_chart(
                ranking,
                use_container_width=True,
                config={"displaylogo": False, "locale": "pt-BR"},
                key=f"grafico_ranking_{titulo}",
            )

    with st.expander("Ver consolidação mensal"):
        tabela = mensal.drop(columns="Periodo").rename(
            columns={
                "Percentual_Fora": "% Fora",
                "Percentual_Dentro": "% Dentro",
            }
        )
        st.dataframe(
            tabela,
            use_container_width=True,
            hide_index=True,
            column_config={
                "% Fora": st.column_config.NumberColumn(format="%.2f%%"),
                "% Dentro": st.column_config.NumberColumn(format="%.2f%%"),
            },
        )



cabecalho()

# =========================================================
# ENTRADA DAS DUAS PLANILHAS
# =========================================================
with st.sidebar:
    st.markdown("### Bases de dados")
    arquivo_efetivacao = st.file_uploader(
        "1. Base de efetivações",
        type=["xlsx"],
        key="upload_efetivacao",
    )
    arquivo_movimentacoes = st.file_uploader(
        "2. Base de movimentações",
        type=["xlsx"],
        key="upload_movimentacoes",
    )

    st.divider()
    st.markdown("### Regras")
    sla_movimentacao_dias = st.number_input(
        "Prazo de Movimentações (dias úteis)",
        min_value=0,
        max_value=60,
        value=4,
        step=1,
        help="Este prazo afeta somente o indicador de Movimentações.",
    )
    meta_sla = st.slider(
        "Meta de cumprimento (%)",
        min_value=0,
        max_value=100,
        value=95,
        step=1,
    )
    st.caption(
        "Efetivação: Vigência Inicio × Data Efetivação, em dias úteis, "
        "com SLA fixo de até 1 dia útil. "
        "Movimentações: Dt.Modificação × Dt.Entrada SAP, usando somente o prazo acima."
    )


# =========================================================
# CARREGAMENTO DA BASE DE EFETIVAÇÕES
# =========================================================
try:
    if arquivo_efetivacao is not None:
        dados_brutos = ler_excel_upload(arquivo_efetivacao.getvalue())
        origem_efetivacao = arquivo_efetivacao.name
    elif ARQUIVO_PADRAO.exists():
        dados_brutos = ler_excel_local(
            str(ARQUIVO_PADRAO), ARQUIVO_PADRAO.stat().st_mtime
        )
        origem_efetivacao = ARQUIVO_PADRAO.name
    else:
        dados_brutos = None
        origem_efetivacao = None

    if dados_brutos is not None:
        dados = processar_base(dados_brutos)
    else:
        dados = None
except (KeyError, ValueError, OSError) as erro:
    st.error(f"Não foi possível processar a base de efetivações: {erro}")
    st.stop()


# =========================================================
# CARREGAMENTO DA BASE DE MOVIMENTAÇÕES
# =========================================================
try:
    if arquivo_movimentacoes is not None:
        movimentacoes_brutas = ler_excel_upload(arquivo_movimentacoes.getvalue())
        origem_movimentacoes = arquivo_movimentacoes.name
    elif ARQUIVO_MOVIMENTACOES_PADRAO.exists():
        movimentacoes_brutas = ler_excel_local(
            str(ARQUIVO_MOVIMENTACOES_PADRAO),
            ARQUIVO_MOVIMENTACOES_PADRAO.stat().st_mtime,
        )
        origem_movimentacoes = ARQUIVO_MOVIMENTACOES_PADRAO.name
    else:
        movimentacoes_brutas = None
        origem_movimentacoes = None

    if movimentacoes_brutas is not None:
        dados_movimentacoes = processar_movimentacoes(
            movimentacoes_brutas,
            int(sla_movimentacao_dias),
        )
    else:
        dados_movimentacoes = None
except (KeyError, ValueError, OSError) as erro:
    st.error(f"Não foi possível processar a base de movimentações: {erro}")
    st.stop()


# A aplicação foi pensada para receber as duas planilhas.
if dados is None or dados_movimentacoes is None:
    faltantes = []
    if dados is None:
        faltantes.append("Base de efetivações")
    if dados_movimentacoes is None:
        faltantes.append("Base de movimentações")

    st.info(
        "Envie as duas planilhas no menu lateral para aplicar as regras e carregar o painel.\n\n"
        + "Faltando: **" + " e ".join(faltantes) + "**."
    )
    st.stop()


# =========================================================
# FILTROS DA BASE DE EFETIVAÇÕES
# =========================================================
with st.sidebar:
    st.divider()
    st.markdown("### Filtros de efetivação")

    tipos_disponiveis = sorted(dados["Tipo"].dropna().unique().tolist())
    tipos = st.multiselect(
        "Segmento",
        tipos_disponiveis,
        default=tipos_disponiveis,
    )

    periodos_disponiveis = (
        dados.loc[dados["Periodo"].notna(), ["Periodo", "Competência"]]
        .drop_duplicates()
        .sort_values("Periodo")["Competência"]
        .tolist()
    )
    if dados["Competência"].eq("Sem competência").any():
        periodos_disponiveis.append("Sem competência")

    competencias = st.multiselect(
        "Competência",
        periodos_disponiveis,
        default=periodos_disponiveis,
    )

    st.caption(f"Efetivações: {origem_efetivacao}")
    st.caption(f"Movimentações: {origem_movimentacoes}")


dados_filtrados = dados.loc[
    dados["Tipo"].isin(tipos) & dados["Competência"].isin(competencias)
].copy()

if dados_filtrados.empty:
    st.warning("Nenhum registro de efetivação corresponde aos filtros selecionados.")
    st.stop()


# =========================================================
# RELATÓRIO GERENCIAL EM PDF
# =========================================================
with st.sidebar:
    st.divider()
    st.markdown("### Relatório gerencial")
    st.caption(
        "Gera um PDF com os indicadores, gráficos, rankings, filtros e regras "
        "que estão sendo utilizados no painel."
    )

    if st.button(
        "Gerar relatório PDF",
        use_container_width=True,
        type="primary",
    ):
        with st.spinner("Montando relatório gerencial..."):
            secoes_pdf = []

            for titulo_pdf, base_pdf in [
                ("Visão geral", dados_filtrados),
                (
                    "Saúde",
                    dados_filtrados.loc[
                        dados_filtrados["Tipo"].eq("Saúde")
                    ].copy(),
                ),
                (
                    "Odonto",
                    dados_filtrados.loc[
                        dados_filtrados["Tipo"].eq("Odonto")
                    ].copy(),
                ),
            ]:
                secoes_pdf.append(
                    {
                        "titulo": titulo_pdf,
                        "resumo": resumo_operacional(base_pdf),
                        "mensal": consolidar_mensal(base_pdf),
                        "ranking": ranking_produtos_fora(base_pdf),
                    }
                )

            mensal_mov_pdf = consolidar_movimentacoes_mensal(
                dados_movimentacoes
            )

            total_mov_pdf = int(
                mensal_mov_pdf["Total"].sum()
            ) if not mensal_mov_pdf.empty else 0

            dentro_mov_pdf = int(
                mensal_mov_pdf["Quantidade_Dentro"].sum()
            ) if not mensal_mov_pdf.empty else 0

            fora_mov_pdf = int(
                mensal_mov_pdf["Quantidade_Fora"].sum()
            ) if not mensal_mov_pdf.empty else 0

            percentual_mov_pdf = (
                dentro_mov_pdf / total_mov_pdf * 100
                if total_mov_pdf
                else 0.0
            )

            movimentacoes_pdf = {
                "mensal": mensal_mov_pdf,
                "resumo": {
                    "total": total_mov_pdf,
                    "dentro": dentro_mov_pdf,
                    "fora": fora_mov_pdf,
                    "percentual_dentro": percentual_mov_pdf,
                    "verificar": int(
                        dados_movimentacoes["Indicador"]
                        .eq("Verificar")
                        .sum()
                    ),
                },
            }

            st.session_state["relatorio_pdf_bytes"] = gerar_relatorio_pdf(
                secoes_efetivacao=secoes_pdf,
                movimentacoes=movimentacoes_pdf,
                meta_sla=float(meta_sla),
                sla_movimentacao_dias=int(sla_movimentacao_dias),
                filtros={
                    "tipos": tipos,
                    "competencias": competencias,
                },
                origem_efetivacao=origem_efetivacao,
                origem_movimentacoes=origem_movimentacoes,
                logo_path=LOGO_PATH,
            )

    if "relatorio_pdf_bytes" in st.session_state:
        st.download_button(
            "Baixar relatório em PDF",
            data=st.session_state["relatorio_pdf_bytes"],
            file_name="relatorio_gerencial_indicador_operacional.pdf",
            mime="application/pdf",
            use_container_width=True,
        )


# =========================================================
# ABAS
# =========================================================
aba_geral, aba_saude, aba_odonto, aba_movimentacoes, aba_base = st.tabs(
    ["Visão geral", "Saúde", "Odonto", "Movimentações", "Base tratada"]
)

with aba_geral:
    exibir_secao(dados_filtrados, "Visão geral", float(meta_sla))

with aba_saude:
    exibir_secao(
        dados_filtrados.loc[dados_filtrados["Tipo"].eq("Saúde")],
        "Saúde",
        float(meta_sla),
    )

with aba_odonto:
    exibir_secao(
        dados_filtrados.loc[dados_filtrados["Tipo"].eq("Odonto")],
        "Odonto",
        float(meta_sla),
    )

with aba_movimentacoes:
    st.subheader("Indicador de Movimentações")
    st.caption(
        f"Regra exclusiva de Movimentações: dias úteis entre Dt.Modificação e Dt.Entrada SAP. "
        f"Até {int(sla_movimentacao_dias)} dia(s) útil(eis) = Dentro do prazo; "
        f"acima desse prazo = Fora do prazo. "
        "Os gráficos consideram somente 01/2026 em diante."
    )
    exibir_movimentacoes(dados_movimentacoes, float(meta_sla))

with aba_base:
    st.subheader("Bases tratadas")

    sub_efetivacao, sub_movimentacoes = st.tabs(
        ["Efetivações", "Movimentações"]
    )

    with sub_efetivacao:
        st.caption("Use os filtros da barra lateral para restringir os registros.")
        colunas_exibir = [
            coluna
            for coluna in [
                "Competência",
                "Tipo",
                COLUNA_PRODUTO,
                "Vigência Inicio",
                "Data do envio informativo",
                COLUNA_EFETIVACAO,
                "Dias para efetivação",
                "Prazo",
            ]
            if coluna in dados_filtrados.columns
        ]
        st.dataframe(
            dados_filtrados[colunas_exibir],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Vigência Inicio": st.column_config.DateColumn(format="DD/MM/YYYY"),
                "Data do envio informativo": st.column_config.DateColumn(format="DD/MM/YYYY"),
                COLUNA_EFETIVACAO: st.column_config.DateColumn(format="DD/MM/YYYY"),
            },
        )

    with sub_movimentacoes:
        colunas_mov = [
            coluna
            for coluna in [
                "Competencia",
                "Dt.Modificação",
                "Dt.Entrada SAP",
                "dias_uteis",
                "Indicador",
            ]
            if coluna in dados_movimentacoes.columns
        ]
        st.dataframe(
            dados_movimentacoes[colunas_mov],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Dt.Modificação": st.column_config.DateColumn(format="DD/MM/YYYY"),
                "Dt.Entrada SAP": st.column_config.DateColumn(format="DD/MM/YYYY"),
            },
        )
