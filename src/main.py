"""Entrada de linha de comando."""
from __future__ import annotations

import argparse
import sys

from .config import load_config
from .indexer import build_index, semantic_query
from .pipeline import console_utf8, documentos_sem_registros, process_all
from .rag import answer


def main() -> int:
    """Executa o pipeline e, opcionalmente, a indexação e uma consulta.

    Returns:
        ``0`` em caso de sucesso; ``1`` quando algum documento não produziu
        nenhum registro — a perda silenciosa que fazia o sistema anunciar
        sucesso enquanto descartava um PDF inteiro (BUG-002).
    """
    parser = argparse.ArgumentParser(description="Processa e consulta os atendimentos")
    parser.add_argument("--indexar", action="store_true", help="indexa os chunks no ChromaDB")
    parser.add_argument("--pergunta", help="consulta em linguagem natural")
    parser.add_argument("--top-k", type=int, default=5, help="quantidade de fontes na resposta")
    args = parser.parse_args()

    sys.stdout = console_utf8(sys.stdout)
    sys.stderr = console_utf8(sys.stderr)
    cfg = load_config()
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
        sources = semantic_query(cfg, args.pergunta, args.top_k)
        print(answer(args.pergunta, sources))

    return 1 if vazios else 0


if __name__ == "__main__":
    raise SystemExit(main())
