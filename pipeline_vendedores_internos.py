from __future__ import annotations

from io import BytesIO
import unicodedata

import pandas as pd


VENDEDORES_INTERNOS = [
    "RENAN AVELINO RICARDO",
    "GENIANE CAUS",
    "FERNANDA PEREIRA SANTANA",
]

COLUNAS_PIPELINE = [
    "Vendedor",
    "Empresa",
    "Plano de Saúde",
    "Plano Odonto",
    "Pessoa de Contato",
    "Data Base",
    "Status da Negociação",
    "Vidas",
]

ALIASES_VENDEDORES = {
    "RENAN AVELINO RICARDO": [
        "RENAN AVELINO RICARDO",
        "RENAN AVELINO",
    ],
    "GENIANE CAUS": [
        "GENIANE CAUS",
    ],
    "FERNANDA PEREIRA SANTANA": [
        "FERNANDA PEREIRA SANTANA",
        "FERNANDA SANTANA",
    ],
}


def normalizar_texto(valor: object) -> str:
    if pd.isna(valor):
        return ""

    texto = unicodedata.normalize(
        "NFKD",
        str(valor),
    )

    texto = "".join(
        caractere
        for caractere in texto
        if not unicodedata.combining(caractere)
    )

    return " ".join(
        texto.upper().strip().split()
    )


_MAPA_VENDEDORES = {}

for vendedor_canonico, aliases in ALIASES_VENDEDORES.items():
    for alias in aliases:
        _MAPA_VENDEDORES[
            normalizar_texto(alias)
        ] = vendedor_canonico


def canonizar_vendedor(valor: object):
    return _MAPA_VENDEDORES.get(
        normalizar_texto(valor)
    )


def preparar_pipeline(
    df: pd.DataFrame,
) -> pd.DataFrame:
    base = df.copy()

    for coluna in COLUNAS_PIPELINE:
        if coluna not in base.columns:
            base[coluna] = pd.NA

    base = base[
        COLUNAS_PIPELINE
    ].copy()

    base["Vendedor"] = (
        base["Vendedor"]
        .map(canonizar_vendedor)
    )

    base = base[
        base["Vendedor"].notna()
    ].copy()

    for coluna in [
        "Empresa",
        "Plano de Saúde",
        "Plano Odonto",
        "Pessoa de Contato",
        "Data Base",
        "Status da Negociação",
    ]:
        base[coluna] = (
            base[coluna]
            .astype("string")
            .fillna("")
            .str.strip()
        )

    base["Vidas"] = pd.to_numeric(
        base["Vidas"],
        errors="coerce",
    ).fillna(0).round().astype("Int64")

    base = base[
        base["Empresa"].ne("")
    ].copy()

    return base.reset_index(drop=True)


def _tentar_formato_flat(
    conteudo: bytes,
):
    df = pd.read_excel(
        BytesIO(conteudo),
        dtype=object,
    )

    mapa = {
        normalizar_texto(coluna): coluna
        for coluna in df.columns
    }

    aliases = {
        "Vendedor": [
            "VENDEDOR",
            "CONSULTOR",
        ],
        "Empresa": [
            "EMPRESA",
        ],
        "Plano de Saúde": [
            "PLANO DE SAUDE",
            "PLANO SAUDE",
        ],
        "Plano Odonto": [
            "PLANO ODONTO",
            "ODONTO",
        ],
        "Pessoa de Contato": [
            "PESSOA DE CONTATO",
            "CONTATO",
        ],
        "Data Base": [
            "DATA BASE",
        ],
        "Status da Negociação": [
            "STATUS DA NEGOCIACAO",
            "STATUS",
        ],
        "Vidas": [
            "VIDAS",
        ],
    }

    renomear = {}

    for padrao, candidatos in aliases.items():
        encontrada = None

        for candidato in candidatos:
            chave = normalizar_texto(candidato)

            if chave in mapa:
                encontrada = mapa[chave]
                break

        if encontrada is not None:
            renomear[
                encontrada
            ] = padrao

    df = df.rename(
        columns=renomear
    )

    if (
        "Vendedor" in df.columns
        and "Empresa" in df.columns
    ):
        return preparar_pipeline(
            df
        )

    return None


def _ler_modelo_reuniao(
    conteudo: bytes,
) -> pd.DataFrame:
    raw = pd.read_excel(
        BytesIO(conteudo),
        sheet_name=0,
        header=None,
        dtype=object,
    )

    registros = []
    vendedor_atual = None

    for _, linha in raw.iterrows():
        valor_coluna_b = (
            linha.iloc[1]
            if len(linha) > 1
            else pd.NA
        )

        vendedor_encontrado = (
            canonizar_vendedor(
                valor_coluna_b
            )
        )

        if vendedor_encontrado:
            vendedor_atual = (
                vendedor_encontrado
            )
            continue

        texto_b = normalizar_texto(
            valor_coluna_b
        )

        if texto_b == "EMPRESA":
            continue

        if not vendedor_atual:
            continue

        if not texto_b:
            continue

        if (
            "TOTAL DE VIDAS PROSPECTADAS"
            in texto_b
            or
            "COMERCIAL MEDIATORIE"
            in texto_b
        ):
            continue

        valores = []

        for indice in range(1, 8):
            valores.append(
                linha.iloc[indice]
                if len(linha) > indice
                else pd.NA
            )

        empresa = valores[0]

        if pd.isna(empresa):
            continue

        registros.append(
            [
                vendedor_atual,
                *valores,
            ]
        )

    return preparar_pipeline(
        pd.DataFrame(
            registros,
            columns=COLUNAS_PIPELINE,
        )
    )


def carregar_pipeline_excel(
    nome: str,
    conteudo: bytes,
) -> pd.DataFrame:
    del nome

    try:
        flat = _tentar_formato_flat(
            conteudo
        )

        if flat is not None:
            return flat

    except Exception:
        pass

    return _ler_modelo_reuniao(
        conteudo
    )


def exportar_pipeline_excel(
    df: pd.DataFrame,
) -> bytes:
    base = preparar_pipeline(
        df
    )

    buffer = BytesIO()

    with pd.ExcelWriter(
        buffer,
        engine="openpyxl",
    ) as writer:
        base.to_excel(
            writer,
            index=False,
            sheet_name="PIPELINE INTERNO",
        )

    buffer.seek(0)

    return buffer.getvalue()
