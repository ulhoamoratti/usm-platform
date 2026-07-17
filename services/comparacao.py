import re
import unicodedata
from io import BytesIO
from typing import Optional

import pandas as pd


PADRAO_PROCESSO_CNJ = re.compile(
    r"\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}"
)


def normalizar_texto(valor: object) -> str:
    """
    Normaliza textos para comparação de nomes de colunas:
    remove acentos, converte para minúsculas e reduz espaços.
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


def localizar_coluna(
    dataframe: pd.DataFrame,
    nomes_possiveis: list[str],
) -> Optional[str]:
    """
    Localiza uma coluna ignorando diferenças de acentuação,
    letras maiúsculas, minúsculas e espaços externos.
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


def extrair_numero_processo(valor: object) -> Optional[str]:
    """
    Extrai o número CNJ completo contido em uma célula.

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


def normalizar_hora(valor: object) -> Optional[str]:
    """
    Converte diferentes representações de horário
    para o padrão HH:MM.
    """
    if pd.isna(valor):
        return None

    if hasattr(valor, "strftime"):
        try:
            return valor.strftime("%H:%M")
        except (ValueError, TypeError):
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


def preparar_carteira(
    carteira: pd.DataFrame,
) -> tuple[pd.DataFrame, Optional[str]]:
    """
    Valida e prepara a carteira de processos.
    """
    coluna_processo = localizar_coluna(
        carteira,
        ["Processo"],
    )

    if coluna_processo is None:
        raise ValueError(
            "A carteira deve possuir uma coluna chamada 'Processo'."
        )

    coluna_cliente = localizar_coluna(
        carteira,
        [
            "Cliente",
            "Cliente do processo",
            "Cliente do Processo",
        ],
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

    return resultado, coluna_cliente


def preparar_base_trt(
    trt: pd.DataFrame,
) -> pd.DataFrame:
    """
    Prepara a base do TRT e mantém apenas registros
    com número do processo, data e horário de audiência.
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
            "Não foi localizada a coluna do número do processo "
            "na base do TRT."
        )

    if coluna_data is None:
        raise ValueError(
            "Não foi localizada a coluna da data da audiência "
            "na base do TRT."
        )

    if coluna_hora is None:
        raise ValueError(
            "Não foi localizada a coluna do horário da audiência "
            "na base do TRT."
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

    resultado["Data_TRT"] = (
        datas.dt.strftime("%d/%m/%Y")
    )

    resultado["Hora_Normalizada"] = resultado[
        coluna_hora
    ].apply(normalizar_hora)

    resultado["Hora_TRT"] = resultado[
        "Hora_Normalizada"
    ]

    resultado = resultado.dropna(
        subset=[
            "Processo_Normalizado",
            "Data_Normalizada",
            "Hora_Normalizada",
        ]
    ).copy()

    resultado = resultado[
        resultado["Data_Normalizada"].ne("")
        & resultado["Hora_Normalizada"].ne("")
    ].copy()

    return resultado


def preparar_pauta_interna(
    pauta: pd.DataFrame,
) -> pd.DataFrame:
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

    resultado["Data_Pauta"] = (
        data_hora.dt.strftime("%d/%m/%Y")
    )

    resultado["Hora_Normalizada"] = (
        data_hora.dt.strftime("%H:%M")
    )

    resultado = resultado.dropna(
        subset=["Processo_Normalizado"]
    ).copy()

    return resultado


def formatar_lista(
    valores: list[object],
) -> str:
    """
    Elimina vazios e duplicidades e organiza os valores
    em uma única célula, separados por vírgula.
    """
    valores_validos = {
        str(valor).strip()
        for valor in valores
        if pd.notna(valor)
        and str(valor).strip()
        and str(valor).strip().lower() != "nan"
    }

    return ", ".join(
        sorted(valores_validos)
    )


def construir_indice_pauta(
    pauta: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """
    Organiza a pauta interna por número de processo.
    """
    indice = {}

    for processo, grupo in pauta.groupby(
        "Processo_Normalizado"
    ):
        indice[processo] = grupo.copy()

    return indice


def diagnosticar_audiencia(
    linha_trt: pd.Series,
    indice_pauta: dict[str, pd.DataFrame],
) -> pd.Series:
    """
    Classifica uma audiência conforme a seguinte ordem:

    1. Processo ausente da pauta interna;
    2. Data divergente;
    3. Horário divergente;
    4. Conferida.
    """
    processo = linha_trt[
        "Processo_Normalizado"
    ]

    data_trt = linha_trt[
        "Data_Normalizada"
    ]

    hora_trt = linha_trt[
        "Hora_Normalizada"
    ]

    if processo not in indice_pauta:
        return pd.Series(
            {
                "Status_Conferencia": (
                    "PROCESSO AUSENTE DA PAUTA INTERNA"
                ),
                "Descricao_Divergencia": (
                    "O número do processo não foi localizado "
                    "na pauta interna."
                ),
                "Datas_Encontradas_Pauta": "",
                "Horarios_Encontrados_Pauta": "",
            }
        )

    registros_processo = indice_pauta[
        processo
    ]

    datas_encontradas = formatar_lista(
        registros_processo[
            "Data_Pauta"
        ].tolist()
    )

    horarios_encontrados_processo = formatar_lista(
        registros_processo[
            "Hora_Normalizada"
        ].tolist()
    )

    registros_mesma_data = registros_processo[
        registros_processo[
            "Data_Normalizada"
        ].eq(data_trt)
    ]

    if registros_mesma_data.empty:
        return pd.Series(
            {
                "Status_Conferencia": (
                    "DIVERGÊNCIA DE DATA"
                ),
                "Descricao_Divergencia": (
                    "O processo foi localizado na pauta interna, "
                    "mas não existe registro na mesma data "
                    "informada pelo TRT."
                ),
                "Datas_Encontradas_Pauta": (
                    datas_encontradas
                ),
                "Horarios_Encontrados_Pauta": (
                    horarios_encontrados_processo
                ),
            }
        )

    horarios_mesma_data = formatar_lista(
        registros_mesma_data[
            "Hora_Normalizada"
        ].tolist()
    )

    horario_exato = (
        registros_mesma_data[
            "Hora_Normalizada"
        ].eq(hora_trt)
    ).any()

    if not horario_exato:
        return pd.Series(
            {
                "Status_Conferencia": (
                    "DIVERGÊNCIA DE HORÁRIO"
                ),
                "Descricao_Divergencia": (
                    "O processo e a data foram localizados, "
                    "mas o horário da pauta interna é diferente "
                    "do horário informado pelo TRT."
                ),
                "Datas_Encontradas_Pauta": (
                    formatar_lista(
                        registros_mesma_data[
                            "Data_Pauta"
                        ].tolist()
                    )
                ),
                "Horarios_Encontrados_Pauta": (
                    horarios_mesma_data
                ),
            }
        )

    return pd.Series(
        {
            "Status_Conferencia": "CONFERIDA",
            "Descricao_Divergencia": "",
            "Datas_Encontradas_Pauta": (
                formatar_lista(
                    registros_mesma_data[
                        "Data_Pauta"
                    ].tolist()
                )
            ),
            "Horarios_Encontrados_Pauta": (
                horarios_mesma_data
            ),
        }
    )


def montar_resultado_exibicao(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Seleciona, organiza e renomeia as colunas
    apresentadas na tela e no Excel.
    """
    colunas_base = [
        "Processo_Normalizado",
        "Cliente",
        "Data_TRT",
        "Hora_TRT",
        "Datas_Encontradas_Pauta",
        "Horarios_Encontrados_Pauta",
        "Status_Conferencia",
        "Descricao_Divergencia",
    ]

    colunas_opcionais = []

    nomes_colunas_opcionais = [
        ["Órgão Julgador", "Orgao Julgador"],
        ["Classe Judicial"],
        ["Polo Ativo"],
        ["Polo Passivo"],
        ["Status do Processo"],
    ]

    for nomes in nomes_colunas_opcionais:
        coluna = localizar_coluna(
            dataframe,
            nomes,
        )

        if (
            coluna is not None
            and coluna not in colunas_opcionais
        ):
            colunas_opcionais.append(
                coluna
            )

    colunas_desejadas = (
        colunas_base
        + colunas_opcionais
    )

    colunas_existentes = [
        coluna
        for coluna in colunas_desejadas
        if coluna in dataframe.columns
    ]

    resultado = dataframe[
        colunas_existentes
    ].copy()

    resultado = resultado.rename(
        columns={
            "Processo_Normalizado": "Processo",
            "Data_TRT": "Data da Audiência - TRT",
            "Hora_TRT": "Hora da Audiência - TRT",
            "Datas_Encontradas_Pauta": (
                "Data(s) encontrada(s) na Pauta Interna"
            ),
            "Horarios_Encontrados_Pauta": (
                "Horário(s) encontrado(s) na Pauta Interna"
            ),
            "Status_Conferencia": (
                "Status da Conferência"
            ),
            "Descricao_Divergencia": (
                "Descrição da Divergência"
            ),
        }
    )

    return resultado


def realizar_conferencia(
    carteira: pd.DataFrame,
    trt: pd.DataFrame,
    pauta_interna: pd.DataFrame,
) -> dict:
    """
    Executa a conferência integral das audiências.
    """
    (
        carteira_preparada,
        coluna_cliente,
    ) = preparar_carteira(
        carteira
    )

    trt_preparado = preparar_base_trt(
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
    else:
        audiencias_carteira[
            "Cliente"
        ] = ""

    indice_pauta = construir_indice_pauta(
        pauta_preparada
    )

    diagnosticos = audiencias_carteira.apply(
        lambda linha: diagnosticar_audiencia(
            linha,
            indice_pauta,
        ),
        axis=1,
    )

    audiencias_carteira = pd.concat(
        [
            audiencias_carteira.reset_index(
                drop=True
            ),
            diagnosticos.reset_index(
                drop=True
            ),
        ],
        axis=1,
    )

    mascara_ausentes = audiencias_carteira[
        "Status_Conferencia"
    ].eq(
        "PROCESSO AUSENTE DA PAUTA INTERNA"
    )

    mascara_data = audiencias_carteira[
        "Status_Conferencia"
    ].eq(
        "DIVERGÊNCIA DE DATA"
    )

    mascara_horario = audiencias_carteira[
        "Status_Conferencia"
    ].eq(
        "DIVERGÊNCIA DE HORÁRIO"
    )

    mascara_conferidas = audiencias_carteira[
        "Status_Conferencia"
    ].eq(
        "CONFERIDA"
    )

    ausentes_bruto = audiencias_carteira[
        mascara_ausentes
    ].copy()

    divergencias_data_bruto = audiencias_carteira[
        mascara_data
    ].copy()

    divergencias_horario_bruto = audiencias_carteira[
        mascara_horario
    ].copy()

    conferidas_bruto = audiencias_carteira[
        mascara_conferidas
    ].copy()

    inconsistencias_bruto = audiencias_carteira[
        ~mascara_conferidas
    ].copy()

    resultado_completo = montar_resultado_exibicao(
        audiencias_carteira
    )

    ausentes = montar_resultado_exibicao(
        ausentes_bruto
    )

    divergencias_data = montar_resultado_exibicao(
        divergencias_data_bruto
    )

    divergencias_horario = montar_resultado_exibicao(
        divergencias_horario_bruto
    )

    conferidas = montar_resultado_exibicao(
        conferidas_bruto
    )

    inconsistencias = montar_resultado_exibicao(
        inconsistencias_bruto
    )

    return {
        "resultado_completo": resultado_completo,
        "inconsistencias": inconsistencias,
        "ausentes": ausentes,
        "divergencias_data": divergencias_data,
        "divergencias_horario": divergencias_horario,
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
        "total_divergencias_data": len(
            divergencias_data
        ),
        "total_divergencias_horario": len(
            divergencias_horario
        ),
        "total_inconsistencias": len(
            inconsistencias
        ),
        "total_conferidas": len(
            conferidas
        ),
    }


def ajustar_planilha_excel(
    writer: pd.ExcelWriter,
    nome_aba: str,
    dataframe: pd.DataFrame,
) -> None:
    """
    Ajusta largura, filtros e congelamento
    do cabeçalho no Excel exportado.
    """
    planilha = writer.sheets[
        nome_aba
    ]

    planilha.freeze_panes = "A2"
    planilha.auto_filter.ref = (
        planilha.dimensions
    )

    for indice, coluna in enumerate(
        dataframe.columns,
        start=1,
    ):
        maior_tamanho = len(
            str(coluna)
        )

        for valor in dataframe[
            coluna
        ].fillna("").astype(str):
            maior_tamanho = max(
                maior_tamanho,
                len(valor),
            )

        largura = min(
            maior_tamanho + 2,
            60,
        )

        letra_coluna = planilha.cell(
            row=1,
            column=indice,
        ).column_letter

        planilha.column_dimensions[
            letra_coluna
        ].width = largura


def gerar_excel_resultado(
    resultado: dict,
) -> bytes:
    """
    Gera o Excel final com todas as classificações.
    """
    arquivo_saida = BytesIO()

    abas = {
        "INCONSISTENCIAS": resultado[
            "inconsistencias"
        ],
        "PROCESSOS AUSENTES": resultado[
            "ausentes"
        ],
        "DIVERGENCIAS DATA": resultado[
            "divergencias_data"
        ],
        "DIVERGENCIAS HORARIO": resultado[
            "divergencias_horario"
        ],
        "CONFERIDAS": resultado[
            "conferidas"
        ],
        "RESULTADO COMPLETO": resultado[
            "resultado_completo"
        ],
    }

    with pd.ExcelWriter(
        arquivo_saida,
        engine="openpyxl",
    ) as writer:
        for nome_aba, dataframe in abas.items():
            dataframe.to_excel(
                writer,
                sheet_name=nome_aba,
                index=False,
            )

            ajustar_planilha_excel(
                writer,
                nome_aba,
                dataframe,
            )

    arquivo_saida.seek(0)

    return arquivo_saida.getvalue()
