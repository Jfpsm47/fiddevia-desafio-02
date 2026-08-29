"""Indicadores e gráficos (RF08, RF09, Seção 8 do enunciado)."""
import json

import pytest

pytest.importorskip("pandas")
pytest.importorskip("matplotlib")

import pandas as pd  # noqa: E402

from src.analytics import base_util, build_indicators, export_results, generate_charts  # noqa: E402

#: Indicadores que a Seção 8 do enunciado exige.
OBRIGATORIOS = (
    "total_documentos", "total_paginas", "por_classificacao",
    "percentual_por_classificacao", "por_categoria", "por_status",
    "categoria_maior_volume", "categoria_maior_tempo_medio",
    "tempo_medio", "tempo_mediano", "tempo_desvio_padrao",
    "percentual_paginas_ocr", "erros_por_etapa", "erros_por_tipo",
    "por_municipio",
)


def amostra() -> pd.DataFrame:
    return pd.DataFrame([
        {"classificacao": "valido", "categoria": "Python e bibliotecas", "status": "Concluido",
         "municipio": "Sinop", "uf": "MT", "tempo_minutos": 10, "metodo": "extracao_direta"},
        {"classificacao": "valido", "categoria": "Python e bibliotecas", "status": "Pendente",
         "municipio": "Sinop", "uf": "MT", "tempo_minutos": 20, "metodo": "extracao_direta"},
        {"classificacao": "incompleto", "categoria": "Acesso e senha", "status": "Pendente",
         "municipio": "Cuiabá", "uf": "MT", "tempo_minutos": 60, "metodo": "ocr"},
        {"classificacao": "invalido", "categoria": None, "status": "Concluido",
         "municipio": None, "uf": None, "tempo_minutos": 999, "metodo": "extracao_direta"},
        {"classificacao": "duplicado", "categoria": "Python e bibliotecas", "status": "Concluido",
         "municipio": "Sinop", "uf": "MT", "tempo_minutos": 999, "metodo": "extracao_direta"},
        # incompleto vindo de OCR, com a categoria ilegível
        {"classificacao": "incompleto", "categoria": None, "status": "Pendente",
         "municipio": None, "uf": "MT", "tempo_minutos": 30, "metodo": "ocr"},
    ])


def test_todos_os_indicadores_obrigatorios_existem():
    indicadores = build_indicators(amostra(), total_documentos=2, total_paginas=10)
    faltando = [chave for chave in OBRIGATORIOS if chave not in indicadores]
    assert not faltando, f"indicadores ausentes: {faltando}"


def test_duplicados_e_invalidos_ficam_fora_das_estatisticas():
    """Eles inflavam categorias, status e médias de tempo (BUG-016)."""
    df = amostra()
    assert len(base_util(df)) == 4

    indicadores = build_indicators(df)

    assert indicadores["total_registros"] == 6
    assert indicadores["base_util"] == 4
    assert indicadores["por_categoria"]["Python e bibliotecas"] == 2, "sem a duplicata"
    assert indicadores["tempo_medio"] == 30.0, "os 999 dos rejeitados não entram"


def test_categoria_nao_oficial_nao_se_mistura_as_oficiais():
    """"categoria desconhecida" era plotada junto das sete oficiais (BUG-017)."""
    indicadores = build_indicators(amostra())
    assert "Não classificada" in indicadores["por_categoria"]
    assert indicadores["categoria_maior_volume"] == "Python e bibliotecas"


def test_desvio_padrao_e_amostral():
    """A entrega usava np.std sem ddof, devolvendo o populacional (BUG-018)."""
    df = amostra()
    indicadores = build_indicators(df)
    esperado = pd.Series([10.0, 20.0, 60.0, 30.0]).std()  # pandas usa ddof=1
    assert indicadores["tempo_desvio_padrao"] == pytest.approx(esperado)


def test_desvio_padrao_com_um_unico_registro_nao_quebra():
    df = pd.DataFrame([{"classificacao": "valido", "categoria": "X", "tempo_minutos": 5}])
    assert build_indicators(df)["tempo_desvio_padrao"] is None


def test_percentual_de_ocr_e_medido_sobre_paginas():
    """O enunciado pede páginas; a entrega media registros (BUG-009)."""
    indicadores = build_indicators(
        amostra(), total_documentos=4, total_paginas=27,
        paginas_por_metodo={"extracao_direta": 20, "ocr": 7},
    )
    assert indicadores["percentual_paginas_ocr"] == 25.93
    assert indicadores["total_paginas"] == 27


def test_percentuais_por_classificacao_somam_cem():
    indicadores = build_indicators(amostra())
    assert sum(indicadores["percentual_por_classificacao"].values()) == pytest.approx(100.0)


def test_erros_agregados_por_etapa_e_por_tipo():
    erros = [
        {"etapa": "ocr", "tipo": "TesseractError"},
        {"etapa": "ocr", "tipo": "TesseractError"},
        {"etapa": "deduplicacao", "tipo": "Duplicidade"},
    ]
    indicadores = build_indicators(amostra(), erros=erros)
    assert indicadores["total_erros"] == 3
    assert indicadores["erros_por_etapa"] == {"ocr": 2, "deduplicacao": 1}
    assert indicadores["erros_por_tipo"] == {"TesseractError": 2, "Duplicidade": 1}


def test_dataframe_vazio_nao_quebra():
    indicadores = build_indicators(pd.DataFrame())
    assert indicadores["total_registros"] == 0
    assert indicadores["tempo_medio"] is None
    assert indicadores["categoria_maior_volume"] is None


def test_exportacao_em_utf8(tmp_path):
    indicadores = export_results(
        amostra(), tmp_path, "dados.csv", "indicadores.json", total_documentos=2, total_paginas=10
    )
    csv = (tmp_path / "dados.csv").read_text(encoding="utf-8")
    salvo = json.loads((tmp_path / "indicadores.json").read_text(encoding="utf-8"))
    assert "Cuiabá" in csv
    assert salvo["total_documentos"] == indicadores["total_documentos"] == 2


def test_tres_graficos_com_municipio(tmp_path):
    gerados = generate_charts(amostra(), tmp_path)
    nomes = {caminho.name for caminho in gerados}
    assert len(gerados) == 3
    assert nomes == {
        "atendimentos_categoria.png", "tempo_medio_categoria.png", "atendimentos_municipio.png",
    }
    assert all(caminho.stat().st_size > 0 for caminho in gerados)


def test_sem_municipio_o_terceiro_grafico_recai_sobre_status(tmp_path):
    df = amostra().assign(municipio=None)
    nomes = {caminho.name for caminho in generate_charts(df, tmp_path)}
    assert "atendimentos_status.png" in nomes
    assert "atendimentos_municipio.png" not in nomes


def test_base_vazia_nao_gera_grafico(tmp_path):
    df = amostra()
    df = df[df.classificacao == "duplicado"]
    assert generate_charts(df, tmp_path) == []
