"""Entrada de linha de comando."""
from __future__ import annotations

import argparse
import sys

from .config import load_config
from .indexer import build_index, semantic_query
from .pipeline import console_utf8, descartar_base, documentos_sem_registros, process_all
from .rag import answer


def responder(cfg: dict, pergunta: str, top_k: int) -> None:
    """Consulta a base e imprime a resposta com suas fontes."""
    from .indexer import ColecaoVazia

    try:
        fontes = semantic_query(cfg, pergunta, top_k)
    except ColecaoVazia as exc:
        print(str(exc), file=sys.stderr)
        return
    resultado = answer(pergunta, fontes)
    print(resultado["resposta"])
    for fonte in resultado.get("fontes", []):
        print(
            "  - {0} ({1}, p.{2}) similaridade {3}".format(
                fonte.get("protocolo"), fonte.get("documento"),
                fonte.get("pagina"), fonte.get("similaridade"),
            )
        )


def main() -> int:
    """Executa o pipeline e, opcionalmente, a indexação e uma consulta.

    Returns:
    Sem argumentos, processa os PDFs. Com ``--pergunta`` ou ``--indexar``, só
    executa o que foi pedido, a menos que ``--processar`` seja informado.

    Returns:
        ``0`` em caso de sucesso; ``1`` quando algum documento não produziu
        nenhum registro — a perda silenciosa que fazia o sistema anunciar
        sucesso enquanto descartava um PDF inteiro (BUG-002).
    """
    parser = argparse.ArgumentParser(description="Processa e consulta os atendimentos")
    parser.add_argument("--processar", action="store_true", help="força o processamento dos PDFs")
    parser.add_argument("--indexar", action="store_true", help="indexa os chunks no ChromaDB")
    parser.add_argument("--pergunta", help="consulta em linguagem natural")
    parser.add_argument("--top-k", type=int, default=5, help="quantidade de fontes na resposta")
    parser.add_argument(
        "--recriar",
        action="store_true",
        help="descarta banco e coleção vetorial antes de processar",
    )
    args = parser.parse_args()

    sys.stdout = console_utf8(sys.stdout)
    sys.stderr = console_utf8(sys.stderr)
    cfg = load_config()
    if args.recriar:
        for removido in descartar_base(cfg):
            print(f"Removido: {removido}")

    # Consultar não deve reprocessar os PDFs: `--pergunta` sozinho atravessava
    # o pipeline inteiro antes de responder (BUG-026). `--indexar` continua
    # processando antes, como o README documenta.
    if args.pergunta and not args.processar:
        if args.indexar:
            print(f"Chunks indexados: {build_index(cfg)}")
        responder(cfg, args.pergunta, args.top_k)
        return 0

    df = process_all(cfg)
    print(f"Registros encontrados: {len(df)}")

    if not df.empty:
        por_metodo = df["metodo"].value_counts().to_dict()
        print(f"Registros por método de leitura: {por_metodo}")

    vazios = documentos_sem_registros(cfg)
    if vazios:
        print(
            "ATENÇÃO: nenhum registro foi extraído de "
            + ", ".join(vazios)
            + ". Consulte output/processamento.log e a tabela erros_processamento.",
            file=sys.stderr,
        )

    if args.indexar:
        print(f"Chunks indexados: {build_index(cfg)}")
    if args.pergunta:
        responder(cfg, args.pergunta, args.top_k)

    return 1 if vazios else 0


if __name__ == "__main__":
    raise SystemExit(main())
