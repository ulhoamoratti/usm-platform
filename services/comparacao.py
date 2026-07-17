import re
import unicodedata
from io import BytesIO

import pandas as pd


PADRAO_PROCESSO_CNJ = re.compile(
    r"\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}"
)


def normalizar_texto(valor):
    """
    Normaliza textos para comparação de nomes de colunas:
    - remove acentos;
    - converte para minúsculas;
    - elimina espaços excedentes.
    """
    texto = str(valor).strip().lower()

    texto = unicodedata.normalize(
        "NFKD",
        texto,
    )

    texto = "".join(
        caractere
        for caractere in texto
        if not unicodedata.combining(caractere)
    )

    texto = re.sub(
        r"\s+",
        " ",
        texto,
    )

    return texto


def localizar_coluna(dataframe, nomes_possiveis):
    """
    Localiza uma coluna sem depender de acentos,
    maiúsculas ou espaços invisíveis.
    """
    mapa_colunas = {
        normalizar_texto(coluna): coluna
        for coluna in dataframe.columns
    }

    for nome in nomes_possiveis:
        nome_normalizado = normalizar_texto(nome)

        if nome_normalizado in mapa_colunas:
            return mapa_colunas[nome_normalizado]

    return None


def extrair_numero_processo(valor):
    """
    Extrai o número CNJ completo de qualquer texto.

    Exemplo:
    0001413-58.2010.5.05.0511 - VERACEL

    Resultado:
    0001413-58.2010.5.05.0511
    """
    if pd.isna(valor):
        return None

    texto = str(valor).strip()

    correspondencia = PADRAO_PROCESSO_CNJ.search(
        texto
    )

    if correspondencia:
        return correspondencia.group(0)

    return None


def normalizar_hora(valor):
    """
    Converte diferentes representações de horário
    para o padrão HH:MM.
    """
    if pd.isna(valor):
        return None

    if hasattr(valor, "strftime"):
        try:
            return valor.strftime("%H:%M")
        except ValueError:
            pass

    texto = str(valor).strip()

    if not texto or texto.lower() == "nan":
        return None

    correspondencia = re.search(
        r"(\d{1,2}):(\d{2})",
        texto,
    )

    if correspondencia:
        hora = int(
            correspondencia.group(1)
        )

        minuto = correspondencia.group(2)

        return f"{hora:02d}:{minuto}"

    convertido = pd.to_datetime(
        texto,
        errors="coerce",
    )

    if pd.notna(convertido):
        return convertido.strftime("%H:%M")

    return None


def preparar_carteira(carteira):
    """
    Valida e prepara a carteira de processos.
    """
    coluna_processo = localizar_coluna(
        carteira,
        ["Processo"],
    )

    if coluna_processo is None:
        raise ValueError(
            "A carteira deve possuir uma coluna chamada "
            "'Processo'."
        )

    resultado = carteira.copy()

    resultado["Processo_Normalizado"] = resultado[
        coluna_processo
    ].apply(extrair_numero_processo)

    resultado = resultado.dropna(
        subset=["Processo_Normalizado"]
    )

    resultado = resultado.drop_duplicates(
        subset=["Processo_Normalizado"]
    )

    coluna_cliente = localizar_coluna(
        resultado,
        [
            "Cliente",
            "Cliente do processo",
        ],
    )

    return resultado, coluna_cliente


def preparar_base_trt(trt):
    """
    Prepara a base do TRT e mantém somente registros
    que possuem audiência com data e horário.
    """
    coluna_processo = localizar_coluna(
        trt,
        [
            "Número do Processo",
            "Numero do Processo",
            "Processo",
        ],
    )

    coluna_data = localizar_coluna(
        trt,
        [
            "Data da Audiência",
            "Data da Audiencia",
            "Data Audiência",
            "Data Audiencia",
        ],
    )

    coluna_hora = localizar_coluna(
        trt,
        [
            "Hora da Audiência",
            "Hora da Audiencia",
            "Hora Audiência",
            "Hora Audiencia",
        ],
    )

    if coluna_processo is None:
        raise ValueError(
            "Não foi localizada a coluna do número do "
            "processo na base do TRT."
        )

    if coluna_data is None:
        raise ValueError(
            "Não foi localizada a coluna da data da "
            "audiência na base do TRT."
        )

    if coluna_hora is None:
        raise ValueError(
            "Não foi localizada a coluna do horário da "
            "audiência na base do TRT."
        )

    resultado = trt.copy()

    resultado["Processo_Normalizado"] = resultado[
        coluna_processo
    ].apply(extrair_numero_processo)

    datas = pd.to_datetime(
        resultado[coluna_data],
        errors="coerce",
        dayfirst=True,
    )

    resultado["Data_Normalizada"] = (
        datas.dt.strftime("%Y-%m-%d")
    )

    resultado["Hora_Normalizada"] = resultado[
        coluna_hora
    ].apply(normalizar_hora)

    resultado = resultado.dropna(
        subset=[
            "Processo_Normalizado",
            "Data_Normalizada",
            "Hora_Normalizada",
        ]
    )

    resultado = resultado[
        resultado["Data_Normalizada"].ne("")
        & resultado["Hora_Normalizada"].ne("")
    ].copy()

    return (
        resultado,
        coluna_processo,
        coluna_data,
        coluna_hora,
    )


def preparar_pauta_interna(pauta):
    """
    Prepara a pauta interna.
    """
    coluna_processo = localizar_coluna(
        pauta,
        [
            "Processo",
            "Número do Processo",
            "Numero do Processo",
        ],
    )

    coluna_data_hora = localizar_coluna(
        pauta,
        [
            "Data/hora",
            "Data/Hora",
            "Data e Hora",
            "Data hora",
        ],
    )

    if coluna_processo is None:
        raise ValueError(
            "Não foi localizada a coluna 'Processo' "
            "na pauta interna."
        )

    if coluna_data_hora is None:
        raise ValueError(
            "Não foi localizada a coluna 'Data/hora' "
            "na pauta interna."
        )

    resultado = pauta.copy()

    resultado["Processo_Normalizado"] = resultado[
        coluna_processo
    ].apply(extrair_numero_processo)

    data_hora = pd.to_datetime(
        resultado[coluna_data_hora],
        errors="coerce",
        dayfirst=True,
    )

    resultado["Data_Normalizada"] = (
        data_hora.dt.strftime("%Y-%m-%d")
    )

    resultado["Hora_Normalizada"] = (
        data_hora.dt.strftime("%H:%M")
    )

    resultado = resultado.dropna(
        subset=["Processo_Normalizado"]
    ).copy()

    return resultado


def criar_chave_audiencia(dataframe):
    """
    Cria a chave técnica:
    processo + data + horário.
    """
    resultado = dataframe.copy()

    resultado["Chave_Audiencia"] = (
        resultado["Processo_Normalizado"]
        + "|"
        + resultado["Data_Normalizada"].fillna("")
        + "|"
        + resultado["Hora_Normalizada"].fillna("")
    )

    return resultado


def obter_colunas_resultado(
    dataframe,
    coluna_data_trt,
    coluna_hora_trt,
):
    """
    Seleciona as colunas relevantes disponíveis
    na base do TRT.
    """
    nomes_desejados = [
        "Processo_Normalizado",
        "Cliente",
        coluna_data_trt,
        coluna_hora_trt,
        localizar_coluna(
            dataframe,
            ["Órgão Julgador", "Orgao Julgador"],
        ),
        localizar_coluna(
            dataframe,
            ["Classe Judicial"],
        ),
        localizar_coluna(
            dataframe,
            ["Polo Ativo"],
        ),
        localizar_coluna(
            dataframe,
            ["Polo Passivo"],
        ),
        localizar_coluna(
            dataframe,
            ["Status do Processo"],
        ),
    ]

    return [
        coluna
        for coluna in nomes_desejados
        if coluna is not None
        and coluna in dataframe.columns
    ]


def realizar_conferencia(
    carteira,
    trt,
    pauta_interna,
):
    """
    Classifica as audiências da carteira em:

    1. AUSENTE DA PAUTA INTERNA:
       o processo não aparece na pauta interna.

    2. DIVERGÊNCIA DE DATA/HORÁRIO:
       o processo aparece, mas não há correspondência
       exata da audiência do TRT.

    3. CONFERIDA:
       processo, data e horário coincidem.
    """
    (
        carteira_preparada,
        coluna_cliente,
    ) = preparar_carteira(
        carteira
    )

    (
        trt_preparado,
        _,
        coluna_data_trt,
        coluna_hora_trt,
    ) = preparar_base_trt(
        trt
    )

    pauta_preparada = preparar_pauta_interna(
        pauta_interna
    )

    processos_carteira = set(
        carteira_preparada[
            "Processo_Normalizado"
        ]
    )

    audiencias_carteira = trt_preparado[
        trt_preparado[
            "Processo_Normalizado"
        ].isin(processos_carteira)
    ].copy()

    audiencias_carteira = criar_chave_audiencia(
        audiencias_carteira
    )

    pauta_preparada = criar_chave_audiencia(
        pauta_preparada
    )

    processos_pauta = set(
        pauta_preparada[
            "Processo_Normalizado"
        ]
    )

    chaves_pauta = set(
        pauta_preparada[
            "Chave_Audiencia"
        ]
    )

    def classificar(linha):
        processo = linha[
            "Processo_Normalizado"
        ]

        chave = linha[
            "Chave_Audiencia"
        ]

        if processo not in processos_pauta:
            return "AUSENTE DA PAUTA INTERNA"

        if chave not in chaves_pauta:
            return "DIVERGÊNCIA DE DATA/HORÁRIO"

        return "CONFERIDA"

    audiencias_carteira[
        "Status_Conferencia"
    ] = audiencias_carteira.apply(
        classificar,
        axis=1,
    )

    if coluna_cliente is not None:
        clientes = carteira_preparada[
            [
                "Processo_Normalizado",
                coluna_cliente,
            ]
        ].copy()

        clientes = clientes.rename(
            columns={
                coluna_cliente: "Cliente",
            }
        )

        audiencias_carteira = (
            audiencias_carteira.merge(
                clientes,
                how="left",
                on="Processo_Normalizado",
            )
        )

    ausentes = audiencias_carteira[
        audiencias_carteira[
            "Status_Conferencia"
        ].eq("AUSENTE DA PAUTA INTERNA")
    ].copy()

    divergencias = audiencias_carteira[
        audiencias_carteira[
            "Status_Conferencia"
        ].eq("DIVERGÊNCIA DE DATA/HORÁRIO")
    ].copy()

    conferidas = audiencias_carteira[
        audiencias_carteira[
            "Status_Conferencia"
        ].eq("CONFERIDA")
    ].copy()

    colunas_resultado = obter_colunas_resultado(
        audiencias_carteira,
        coluna_data_trt,
        coluna_hora_trt,
    )

    colunas_resultado.append(
        "Status_Conferencia"
    )

    ausentes = ausentes[
        colunas_resultado
    ].copy()

    divergencias = divergencias[
        colunas_resultado
    ].copy()

    conferidas = conferidas[
        colunas_resultado
    ].copy()

    for dataframe in [
        ausentes,
        divergencias,
        conferidas,
    ]:
        dataframe.rename(
            columns={
                "Processo_Normalizado": "Processo",
            },
            inplace=True,
        )

    return {
        "ausentes": ausentes,
        "divergencias": divergencias,
        "conferidas": conferidas,
        "total_audiencias_trt": len(
            trt_preparado
        ),
        "total_audiencias_carteira": len(
            audiencias_carteira
        ),
        "total_ausentes": len(
            ausentes
        ),
        "total_divergencias": len(
            divergencias
        ),
        "total_conferidas": len(
            conferidas
        ),
    }


def gerar_excel_resultado(
    ausentes,
    divergencias,
    conferidas,
):
    """
    Gera o Excel com as três classificações.
    """
    arquivo_saida = BytesIO()

    with pd.ExcelWriter(
        arquivo_saida,
        engine="openpyxl",
    ) as writer:
        ausentes.to_excel(
            writer,
            sheet_name="AUSENTES",
            index=False,
        )

        divergencias.to_excel(
            writer,
            sheet_name="DIVERGENCIAS",
            index=False,
        )

        conferidas.to_excel(
            writer,
            sheet_name="CONFERIDAS",
            index=False,
        )

    arquivo_saida.seek(0)

    return arquivo_saida.getvalue()