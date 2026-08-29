"""Similaridade de cosseno e seleção dos trechos mais próximos (RF11)."""
import numpy as np
import pytest

from src.embeddings import cosine_scores, top_k


def test_vetores_identicos_tem_similaridade_um():
    consulta = np.array([1.0, 0.0, 0.0])
    matriz = np.array([[1.0, 0.0, 0.0]])
    assert cosine_scores(consulta, matriz)[0] == pytest.approx(1.0)


def test_vetores_ortogonais_tem_similaridade_zero():
    consulta = np.array([1.0, 0.0])
    matriz = np.array([[0.0, 1.0]])
    assert cosine_scores(consulta, matriz)[0] == pytest.approx(0.0)


def test_vetores_opostos_tem_similaridade_negativa():
    consulta = np.array([1.0, 0.0])
    matriz = np.array([[-1.0, 0.0]])
    assert cosine_scores(consulta, matriz)[0] == pytest.approx(-1.0)


def test_vetor_nulo_nao_divide_por_zero():
    """Sem a guarda, um chunk vazio produziria NaN e contaminaria a ordenação."""
    resultado = cosine_scores(np.array([1.0, 0.0]), np.array([[0.0, 0.0]]))
    assert not np.isnan(resultado).any()


def test_escala_do_vetor_nao_altera_a_similaridade():
    consulta = np.array([1.0, 2.0, 3.0])
    matriz = np.array([[2.0, 4.0, 6.0], [10.0, 20.0, 30.0]])
    notas = cosine_scores(consulta, matriz)
    assert notas[0] == pytest.approx(notas[1])


class ServicoFalso:
    """Serviço de embeddings determinístico, sem carregar modelo."""

    def encode(self, texts):
        # Cada texto vira um vetor de acordo com a inicial, o que torna a
        # ordenação previsível sem depender do modelo real.
        tabela = {"a": [1.0, 0.0], "b": [0.0, 1.0], "c": [0.7, 0.7]}
        return np.array([tabela.get(t[:1].lower(), [0.5, 0.5]) for t in texts])


def test_top_k_ordena_do_mais_para_o_menos_semelhante():
    resultado = top_k("a", ["a-igual", "b-ortogonal", "c-proximo"], ServicoFalso(), k=3)
    indices = [i for i, _ in resultado]
    notas = [n for _, n in resultado]
    assert indices[0] == 0, "o texto idêntico vem primeiro"
    assert notas == sorted(notas, reverse=True)


def test_top_k_respeita_a_quantidade_pedida():
    assert len(top_k("a", ["a", "b", "c"], ServicoFalso(), k=2)) == 2


def test_top_k_sem_candidatos_devolve_lista_vazia():
    assert top_k("a", [], ServicoFalso()) == []
