"""Isolamento de falhas na ingestão (BUG-003).

A entrega envolvia os quatro laços de ``process_all`` em uma única transação:
qualquer erro descartava o trabalho dos quatro documentos, contrariando o
requisito não funcional de não encerrar todo o processamento por causa de um
único registro inválido.
"""
import json
import shutil
from pathlib import Path

import pytest

pytest.importorskip("sqlalchemy")
pytest.importorskip("pandas")

from src.database import create_session_factory, session_scope  # noqa: E402
from src.models import Atendimento, Documento, ErroProcessamento  # noqa: E402
from src.validation import extract_fields  # noqa: E402
from src.pipeline import (  # noqa: E402
    _metodo_do_documento,
    _persist_record,
    process_all,
    split_records,
)

PROJETO = Path(__file__).resolve().parents[1]

CATEGORIAS = {
    "categorias_oficiais": [{"nome": "Python e bibliotecas", "variacoes": ["python", "pip"]}],
    "status_validos": ["Concluido", "Pendente", "Em atendimento"],
}

CFG_CHUNK = {"embeddings": {"tamanho_chunk": 500, "sobreposicao": 80}}


def registro(protocolo: str) -> str:
    """Monta um registro no formato dos PDFs digitais."""
    return (
        f"Protocolo {protocolo} Data 06/07/2026 Solicitante Ana Maria "
        "E-mail ana.maria@aluno.exemplo.br Categoria python Status Concluido "
        "CEP / cidade 78550-000 - Sinop/MT Tempo 19 min "
        "Problema pip nao e reconhecido no terminal. "
        "Solucao O ambiente foi ativado. Observacoes Registro de teste."
    )


def test_falha_de_integridade_isola_apenas_o_registro(monkeypatch):
    """Um registro que viola a integridade não derruba os demais do lote."""
    factory = create_session_factory("sqlite:///:memory:")
    linhas: list[dict] = []

    # texto_limpo é obrigatório; devolver None no segundo registro força um
    # IntegrityError no meio do lote, que é exatamente o caso não tratado.
    def preprocess_defeituoso(texto: str):
        return None if "AT-902" in texto else "texto limpo"

    monkeypatch.setattr("src.pipeline.preprocess", preprocess_defeituoso)

    with session_scope(factory) as sessao:
        doc = Documento(nome_arquivo="t.pdf", hash_sha256="h", total_paginas=1, metodo="extracao_direta")
        sessao.add(doc)
        sessao.flush()
        pagina = {"pagina": 1, "texto": "", "metodo": "extracao_direta"}
        for protocolo in ("AT-901", "AT-902", "AT-903"):
            _persist_record(
                sessao, doc, Path("t.pdf"), pagina,
                {"campos": extract_fields(registro(protocolo)), "ilegiveis": set(),
                 "texto": registro(protocolo)},
                CFG_CHUNK, CATEGORIAS, linhas,
            )

    with session_scope(factory) as sessao:
        persistidos = {a.protocolo for a in sessao.query(Atendimento).all()}
        erros = sessao.query(ErroProcessamento).filter_by(etapa="persistencia").all()

    assert persistidos == {"AT-901", "AT-903"}, "os registros sãos precisam sobreviver"
    assert len(erros) == 1 and "AT-902" in erros[0].mensagem
    assert len(linhas) == 3, "o registro problemático continua no relatório"
    assert "persistencia_falhou" in linhas[1]["motivos"]


def test_documento_corrompido_nao_derruba_os_demais(tmp_path):
    """Um PDF ilegível é registrado como erro; os demais são processados."""
    (tmp_path / "data" / "auxiliares").mkdir(parents=True)
    (tmp_path / "data" / "auxiliares" / "categorias.json").write_text(
        (PROJETO / "data" / "auxiliares" / "categorias.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    pdfs = tmp_path / "data" / "pdfs"
    pdfs.mkdir(parents=True)
    shutil.copy(PROJETO / "data" / "pdfs" / "atendimentos_incompletos.pdf", pdfs / "aa_valido.pdf")
    (pdfs / "zz_corrompido.pdf").write_bytes(b"isto nao e um PDF")

    banco = tmp_path / "database" / "atendimentos.db"
    cfg = {
        "_root": str(tmp_path),
        "entrada": {"diretorio_pdfs": "data/pdfs", "padrao": "*.pdf"},
        "saida": {
            "diretorio": "output", "csv": "processados.csv",
            "indicadores": "indicadores.json", "log": "processamento.log",
            "graficos": "output/graficos",
        },
        "banco": {"url": f"sqlite:///{banco.as_posix()}"},
        "ocr": {"idioma": "por", "dpi": 300, "min_caracteres_extracao_direta": 40},
        "embeddings": {"tamanho_chunk": 500, "sobreposicao": 80},
    }

    df = process_all(cfg)

    factory = create_session_factory(cfg["banco"]["url"])
    with session_scope(factory) as sessao:
        documentos = [d.nome_arquivo for d in sessao.query(Documento).all()]
        atendimentos = sessao.query(Atendimento).count()
        falhas = sessao.query(ErroProcessamento).filter_by(etapa="documento").all()

    assert documentos == ["aa_valido.pdf"], "só o documento legível é persistido"
    assert atendimentos > 0, "o documento legível precisa ter sido processado"
    assert len(falhas) == 1 and "zz_corrompido.pdf" in falhas[0].mensagem
    assert set(df["documento"]) == {"aa_valido.pdf"}, "o CSV não pode citar o documento revertido"
    assert (tmp_path / "output" / "processados.csv").exists()


def test_linhas_do_documento_revertido_saem_do_relatorio(tmp_path, monkeypatch):
    """Se a transação de um documento é revertida, suas linhas somem do CSV."""
    (tmp_path / "data" / "auxiliares").mkdir(parents=True)
    (tmp_path / "data" / "auxiliares" / "categorias.json").write_text(
        json.dumps(CATEGORIAS), encoding="utf-8"
    )
    pdfs = tmp_path / "data" / "pdfs"
    pdfs.mkdir(parents=True)
    shutil.copy(PROJETO / "data" / "pdfs" / "atendimentos_incompletos.pdf", pdfs / "unico.pdf")

    original = split_records

    def explode_na_segunda_pagina(texto: str):
        resultado = original(texto)
        if "pagina 2" in texto:
            raise RuntimeError("falha simulada no meio do documento")
        return resultado

    monkeypatch.setattr("src.pipeline.split_records", explode_na_segunda_pagina)

    cfg = {
        "_root": str(tmp_path),
        "entrada": {"diretorio_pdfs": "data/pdfs", "padrao": "*.pdf"},
        "saida": {
            "diretorio": "output", "csv": "processados.csv",
            "indicadores": "indicadores.json", "log": "processamento.log",
            "graficos": "output/graficos",
        },
        "banco": {"url": f"sqlite:///{(tmp_path / 'database' / 'a.db').as_posix()}"},
        "ocr": {"idioma": "por", "dpi": 300, "min_caracteres_extracao_direta": 40},
        "embeddings": {"tamanho_chunk": 500, "sobreposicao": 80},
    }

    df = process_all(cfg)

    assert df.empty, "nenhuma linha deve sobrar de um documento revertido"
    factory = create_session_factory(cfg["banco"]["url"])
    with session_scope(factory) as sessao:
        assert sessao.query(Documento).count() == 0
        assert sessao.query(ErroProcessamento).filter_by(etapa="documento").count() == 1


def test_split_records_separa_registros_e_descarta_cabecalho():
    cabecalho = "FIC_DEV - Programador de Sistemas com IA | Dados ficticios "
    texto = cabecalho + registro("AT-001") + " " + registro("AT-002")
    partes = split_records(texto)
    assert len(partes) == 2
    assert partes[0].startswith("Protocolo AT-001")
    assert partes[1].startswith("Protocolo AT-002")


def registro_sem_protocolo(sufixo: str) -> str:
    """Registro cujo protocolo saiu ilegível da digitalização."""
    return registro("PROTOCOLO?").replace("Registro de teste.", f"Registro {sufixo}.")


def test_protocolos_ilegiveis_nao_viram_falsa_duplicata():
    """Dois `PROTOCOLO?` distintos recebiam a mesma chave e o segundo era
    classificado como duplicado em vez de inválido (BUG-006)."""
    factory = create_session_factory("sqlite:///:memory:")
    linhas: list[dict] = []
    with session_scope(factory) as sessao:
        doc = Documento(nome_arquivo="t.pdf", hash_sha256="h", total_paginas=1, metodo="pendente")
        sessao.add(doc)
        sessao.flush()
        for numero, sufixo in ((1, "um"), (2, "dois")):
            _persist_record(
                sessao, doc, Path("t.pdf"), {"pagina": numero, "texto": "", "metodo": "extracao_direta"},
                {"campos": extract_fields(registro_sem_protocolo(sufixo)), "ilegiveis": set(),
                 "texto": registro_sem_protocolo(sufixo)},
                CFG_CHUNK, CATEGORIAS, linhas,
            )

    assert [linha["classificacao"] for linha in linhas] == ["invalido", "invalido"]
    chaves = {linha["protocolo"] for linha in linhas}
    assert len(chaves) == 2, "cada registro ilegível precisa de uma chave própria"
    assert all(chave.startswith("SEM-PROTOCOLO-") for chave in chaves)
    assert all(linha["protocolo_bruto"] == "PROTOCOLO?" for linha in linhas), "o valor lido é preservado"
    assert all(len(chave) <= 30 for chave in chaves), "a coluna protocolo tem 30 caracteres"


@pytest.mark.parametrize(
    "metodos,esperado",
    [
        (["extracao_direta", "extracao_direta"], "extracao_direta"),
        (["ocr", "ocr"], "ocr"),
        (["ocr_pendente", "ocr_pendente"], "falhou"),
        (["ocr", "ocr_pendente"], "misto"),
        (["extracao_direta", "ocr"], "misto"),
    ],
)
def test_metodo_do_documento_reflete_o_resultado(metodos, esperado):
    """O método era decidido antes de processar: um documento cujo OCR falhou
    inteiro ficava gravado como "ocr" (BUG-022)."""
    paginas = [{"metodo": m} for m in metodos]
    assert _metodo_do_documento(paginas) == esperado
