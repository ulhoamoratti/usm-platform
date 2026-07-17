import re
import unicodedata
from io import BytesIO
from typing import Optional

import pandas as pd


PADRAO_PROCESSO_CNJ = re.compile(
    r"\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}"
)


# ============================================================
# FUNÇÕES GERAIS
# ============================================================

def normalizar_texto(valor: object) -> str:
    """
    Normaliza textos para comparação de nomes de colunas.
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
    Localiza uma coluna ignorando acentos, maiúsculas
    e espaços externos.
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
    Extrai o número CNJ completo de uma célula.
    """
    if pd.isna(valor):
        return None

    correspondencia = PADRAO_PROCESSO_CNJ.search(
        str(valor).strip()
    )

    if correspondencia:
        return correspondencia.group(0)

    return None


def normalizar_hora(valor: object) -> Optional[str]:
    """
    Converte diferentes formatos de horário para HH:MM.
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
        hora = int(correspondencia.group(1))
        minuto = correspondencia.group(2)

        return f"{hora:02d}:{minuto}"

    convertido = pd.to_datetime(
        texto,
        errors="coerce",
    )

    if pd.notna(convertido):
        return convertido.strftime("%H:%M")

    return None


def hora_em_minutos(valor: object) -> Optional[int]:
    """
    Converte HH:MM em minutos, para localizar o horário
    mais próximo quando houver divergência.
    """
    horario = normalizar_hora(valor)

    if horario is None:
        return None

    hora, minuto = horario.split(":")

    return int(hora) * 60 + int(minuto)


def formatar_valor(valor: object) -> str:
    """
    Evita exibição de NaN e NaT.
    """
    if pd.isna(valor):
        return ""

    return str(valor)


# ============================================================
# PREPARAÇÃO DAS BASES
# ============================================================

def preparar_carteira(
    carteira: pd.DataFrame,
) -> tuple[pd.DataFrame, Optional[str]]:
    """
    Valida e prepara a carteira.
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
    Prepara a base do TRT e mantém apenas audiências
    com processo, data e horário válidos.
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

    resultado["Data_DT"] = pd.to_datetime(
        resultado[coluna_data],
        errors="coerce",
        dayfirst=True,
    ).dt.normalize()

    resultado["Data_TRT"] = resultado[
        "Data_DT"
    ].dt.strftime("%d/%m/%Y")

    resultado["Hora_TRT"] = resultado[
        coluna_hora
    ].apply(normalizar_hora)

    resultado["Hora_Minutos_TRT"] = resultado[
        "Hora_TRT"
    ].apply(hora_em_minutos)

    resultado = resultado.dropna(
        subset=[
            "Processo_Normalizado",
            "Data_DT",
            "Hora_TRT",
        ]
    ).copy()

    resultado["ID_Evento_TRT"] = range(
        1,
        len(resultado) + 1,
    )

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

    coluna_assunto = localizar_coluna(
        pauta,
        [
            "Assunto",
            "Tipo de audiência",
            "Tipo de Audiencia",
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

    resultado["DataHora_DT"] = pd.to_datetime(
        resultado[coluna_data_hora],
        errors="coerce",
        dayfirst=True,
    )

    resultado["Data_DT"] = resultado[
        "DataHora_DT"
    ].dt.normalize()

    resultado["Data_Pauta"] = resultado[
        "DataHora_DT"
    ].dt.strftime("%d/%m/%Y")

    resultado["Hora_Pauta"] = resultado[
        "DataHora_DT"
    ].dt.strftime("%H:%M")

    resultado["Hora_Minutos_Pauta"] = resultado[
        "Hora_Pauta"
    ].apply(hora_em_minutos)

    if coluna_assunto is not None:
        resultado["Assunto_Pauta"] = resultado[
            coluna_assunto
        ].fillna("").astype(str)
    else:
        resultado["Assunto_Pauta"] = ""

    resultado = resultado.dropna(
        subset=[
            "Processo_Normalizado",
            "Data_DT",
            "Hora_Pauta",
        ]
    ).copy()

    resultado["ID_Evento_Pauta"] = range(
        1,
        len(resultado) + 1,
    )

    return resultado


# ============================================================
# CONCILIAÇÃO UM A UM
# ============================================================

def criar_diagnostico(
    linha_trt: pd.Series,
    status: str,
    descricao: str,
    linha_pauta: Optional[pd.Series] = None,
) -> dict:
    """
    Cria o diagnóstico de uma audiência.
    """
    if linha_pauta is None:
        data_pauta = ""
        hora_pauta = ""
        assunto_pauta = ""
        id_evento_pauta = ""
    else:
        data_pauta = formatar_valor(
            linha_pauta.get("Data_Pauta", "")
        )

        hora_pauta = formatar_valor(
            linha_pauta.get("Hora_Pauta", "")
        )

        assunto_pauta = formatar_valor(
            linha_pauta.get("Assunto_Pauta", "")
        )

        id_evento_pauta = formatar_valor(
            linha_pauta.get("ID_Evento_Pauta", "")
        )

    return {
        "ID_Evento_TRT": linha_trt["ID_Evento_TRT"],
        "Status_Conferencia": status,
        "Descricao_Divergencia": descricao,
        "Data_Encontrada_Pauta": data_pauta,
        "Hora_Encontrada_Pauta": hora_pauta,
        "Assunto_Encontrado_Pauta": assunto_pauta,
        "ID_Evento_Pauta_Utilizado": id_evento_pauta,
    }


def conciliar_processo(
    trt_processo: pd.DataFrame,
    pauta_processo: pd.DataFrame,
) -> list[dict]:
    """
    Concilia as audiências de um único processo.

    Cada linha da pauta interna só pode ser utilizada uma vez.
    """
    diagnosticos = []

    trt_ordenado = trt_processo.sort_values(
        by=[
            "Data_DT",
            "Hora_Minutos_TRT",
            "ID_Evento_TRT",
        ]
    ).copy()

    pauta_disponivel = pauta_processo.sort_values(
        by=[
            "Data_DT",
            "Hora_Minutos_Pauta",
            "ID_Evento_Pauta",
        ]
    ).copy()

    ids_trt_conciliados = set()
    ids_pauta_utilizados = set()

    # --------------------------------------------------------
    # ETAPA 1: correspondências exatas
    # --------------------------------------------------------

    for _, linha_trt in trt_ordenado.iterrows():
        candidatos = pauta_disponivel[
            ~pauta_disponivel[
                "ID_Evento_Pauta"
            ].isin(ids_pauta_utilizados)
            & pauta_disponivel[
                "Data_DT"
            ].eq(linha_trt["Data_DT"])
            & pauta_disponivel[
                "Hora_Pauta"
            ].eq(linha_trt["Hora_TRT"])
        ]

        if candidatos.empty:
            continue

        linha_pauta = candidatos.iloc[0]

        ids_trt_conciliados.add(
            linha_trt["ID_Evento_TRT"]
        )

        ids_pauta_utilizados.add(
            linha_pauta["ID_Evento_Pauta"]
        )

        diagnosticos.append(
            criar_diagnostico(
                linha_trt=linha_trt,
                status="CONFERIDA",
                descricao=(
                    "Processo, data e horário correspondem "
                    "a um evento disponível na pauta interna."
                ),
                linha_pauta=linha_pauta,
            )
        )

    # --------------------------------------------------------
    # ETAPA 2: eventos do TRT ainda não conciliados
    # --------------------------------------------------------

    trt_restante = trt_ordenado[
        ~trt_ordenado[
            "ID_Evento_TRT"
        ].isin(ids_trt_conciliados)
    ]

    for _, linha_trt in trt_restante.iterrows():
        pauta_restante = pauta_disponivel[
            ~pauta_disponivel[
                "ID_Evento_Pauta"
            ].isin(ids_pauta_utilizados)
        ].copy()

        # O processo existe na pauta, mas todas as linhas
        # já foram consumidas por outras audiências.
        if pauta_restante.empty:
            diagnosticos.append(
                criar_diagnostico(
                    linha_trt=linha_trt,
                    status=(
                        "AUDIÊNCIA ADICIONAL NÃO CADASTRADA"
                    ),
                    descricao=(
                        "O processo existe na pauta interna, "
                        "mas não há outro evento disponível para "
                        "corresponder a esta audiência do TRT."
                    ),
                )
            )

            continue

        # Mesmo processo e mesma data: divergência de horário.
        candidatos_mesma_data = pauta_restante[
            pauta_restante[
                "Data_DT"
            ].eq(linha_trt["Data_DT"])
        ].copy()

        if not candidatos_mesma_data.empty:
            hora_trt_minutos = linha_trt[
                "Hora_Minutos_TRT"
            ]

            candidatos_mesma_data[
                "Diferenca_Horario"
            ] = candidatos_mesma_data[
                "Hora_Minutos_Pauta"
            ].apply(
                lambda valor: (
                    abs(valor - hora_trt_minutos)
                    if pd.notna(valor)
                    and hora_trt_minutos is not None
                    else 999999
                )
            )

            linha_pauta = candidatos_mesma_data.sort_values(
                by=[
                    "Diferenca_Horario",
                    "ID_Evento_Pauta",
                ]
            ).iloc[0]

            ids_pauta_utilizados.add(
                linha_pauta["ID_Evento_Pauta"]
            )

            diagnosticos.append(
                criar_diagnostico(
                    linha_trt=linha_trt,
                    status="DIVERGÊNCIA DE HORÁRIO",
                    descricao=(
                        "O processo e a data foram localizados, "
                        "mas o horário do evento disponível na "
                        "pauta interna é diferente do horário do TRT."
                    ),
                    linha_pauta=linha_pauta,
                )
            )

            continue

        # Processo existe, mas não há evento na mesma data.
        pauta_restante[
            "Diferenca_Dias"
        ] = pauta_restante[
            "Data_DT"
        ].apply(
            lambda valor: abs(
                (valor - linha_trt["Data_DT"]).days
            )
        )

        linha_pauta = pauta_restante.sort_values(
            by=[
                "Diferenca_Dias",
                "Hora_Minutos_Pauta",
                "ID_Evento_Pauta",
            ]
        ).iloc[0]

        ids_pauta_utilizados.add(
            linha_pauta["ID_Evento_Pauta"]
        )

        diagnosticos.append(
            criar_diagnostico(
                linha_trt=linha_trt,
                status="DIVERGÊNCIA DE DATA",
                descricao=(
                    "O processo foi localizado na pauta interna, "
                    "mas o evento disponível está registrado "
                    "em data diferente da informada pelo TRT."
                ),
                linha_pauta=linha_pauta,
            )
        )

    return diagnosticos


def executar_conciliacao(
    audiencias_carteira: pd.DataFrame,
    pauta_preparada: pd.DataFrame,
) -> pd.DataFrame:
    """
    Executa a conciliação processo por processo.
    """
    diagnosticos = []

    processos_pauta = set(
        pauta_preparada[
            "Processo_Normalizado"
        ].unique()
    )

    for processo, trt_processo in audiencias_carteira.groupby(
        "Processo_Normalizado",
        sort=False,
    ):
        if processo not in processos_pauta:
            for _, linha_trt in trt_processo.iterrows():
                diagnosticos.append(
                    criar_diagnostico(
                        linha_trt=linha_trt,
                        status=(
                            "PROCESSO AUSENTE DA PAUTA INTERNA"
                        ),
                        descricao=(
                            "O número do processo não foi localizado "
                            "em nenhuma linha da pauta interna."
                        ),
                    )
                )

            continue

        pauta_processo = pauta_preparada[
            pauta_preparada[
                "Processo_Normalizado"
            ].eq(processo)
        ].copy()

        diagnosticos.extend(
            conciliar_processo(
                trt_processo=trt_processo,
                pauta_processo=pauta_processo,
            )
        )

    diagnosticos_df = pd.DataFrame(
        diagnosticos
    )

    resultado = audiencias_carteira.merge(
        diagnosticos_df,
        how="left",
        on="ID_Evento_TRT",
    )

    return resultado


# ============================================================
# ORGANIZAÇÃO DO RESULTADO
# ============================================================

def montar_resultado_exibicao(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Seleciona e renomeia as colunas do resultado.
    """
    colunas_base = [
        "Processo_Normalizado",
        "Cliente",
        "Data_TRT",
        "Hora_TRT",
        "Data_Encontrada_Pauta",
        "Hora_Encontrada_Pauta",
        "Assunto_Encontrado_Pauta",
        "Status_Conferencia",
        "Descricao_Divergencia",
    ]

    colunas_opcionais = []

    conjuntos_opcionais = [
        ["Órgão Julgador", "Orgao Julgador"],
        ["Classe Judicial"],
        ["Polo Ativo"],
        ["Polo Passivo"],
        ["Status do Processo"],
    ]

    for nomes in conjuntos_opcionais:
        coluna = localizar_coluna(
            dataframe,
            nomes,
        )

        if coluna is not None:
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
            "Data_Encontrada_Pauta": (
                "Data encontrada na Pauta Interna"
            ),
            "Hora_Encontrada_Pauta": (
                "Hora encontrada na Pauta Interna"
            ),
            "Assunto_Encontrado_Pauta": (
                "Assunto encontrado na Pauta Interna"
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
    Executa toda a conferência.
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

    conciliacao = executar_conciliacao(
        audiencias_carteira=audiencias_carteira,
        pauta_preparada=pauta_preparada,
    )

    status = conciliacao[
        "Status_Conferencia"
    ]

    ausentes_bruto = conciliacao[
        status.eq(
            "PROCESSO AUSENTE DA PAUTA INTERNA"
        )
    ].copy()

    adicionais_bruto = conciliacao[
        status.eq(
            "AUDIÊNCIA ADICIONAL NÃO CADASTRADA"
        )
    ].copy()

    divergencias_data_bruto = conciliacao[
        status.eq(
            "DIVERGÊNCIA DE DATA"
        )
    ].copy()

    divergencias_horario_bruto = conciliacao[
        status.eq(
            "DIVERGÊNCIA DE HORÁRIO"
        )
    ].copy()

    conferidas_bruto = conciliacao[
        status.eq(
            "CONFERIDA"
        )
    ].copy()

    inconsistencias_bruto = conciliacao[
        ~status.eq(
            "CONFERIDA"
        )
    ].copy()

    resultado_completo = montar_resultado_exibicao(
        conciliacao
    )

    inconsistencias = montar_resultado_exibicao(
        inconsistencias_bruto
    )

    ausentes = montar_resultado_exibicao(
        ausentes_bruto
    )

    adicionais = montar_resultado_exibicao(
        adicionais_bruto
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

    return {
        "resultado_completo": resultado_completo,
        "inconsistencias": inconsistencias,
        "ausentes": ausentes,
        "adicionais": adicionais,
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
        "total_adicionais": len(
            adicionais
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


# ============================================================
# EXPORTAÇÃO PARA EXCEL
# ============================================================

def ajustar_planilha_excel(
    writer: pd.ExcelWriter,
    nome_aba: str,
    dataframe: pd.DataFrame,
) -> None:
    """
    Ajusta filtros, cabeçalho e largura das colunas.
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
            65,
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
    Gera o Excel completo da conferência.
    """
    arquivo_saida = BytesIO()

    abas = {
        "INCONSISTENCIAS": resultado[
            "inconsistencias"
        ],
        "PROCESSOS AUSENTES": resultado[
            "ausentes"
        ],
        "AUDIENCIAS ADICIONAIS": resultado[
            "adicionais"
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