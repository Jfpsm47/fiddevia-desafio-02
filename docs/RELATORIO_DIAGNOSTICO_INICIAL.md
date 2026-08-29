# Relatório de Diagnóstico Inicial

**Sistema auditado:** `solucao_referencia_desafio_final_python_ia`
**Desafio 2 — Introdução a Python para IA · FIC_DEV, Programador de Sistemas com IA**
**Data da auditoria:** 29 de agosto de 2026
**Etapa do desafio:** 1 — Diagnóstico inicial

---

## 1. Objetivo e escopo

Registrar o **estado inicial** da solução recebida, antes de qualquer alteração no código-fonte.

Este relatório cobre exclusivamente a Etapa 1 do desafio:

- inspeção da estrutura, tecnologias e dependências;
- identificação dos pontos de entrada e componentes externos;
- execução dos testes existentes;
- tentativa de iniciar pipeline, FastAPI e Streamlit;
- registro de erros, advertências e comportamentos inesperados;
- evidências de execução.

O plano de correção, o plano de melhoria e o roteiro de implantação são tratados em documentos próprios.

### 1.1 Regra de trabalho adotada

**Nenhuma linha do código-fonte foi modificada durante o diagnóstico.** Todos os arquivos em `src/`, `tests/`, `config.json` e `requirements.txt` permanecem exatamente como entregues. Os únicos artefatos criados foram os gerados pela própria execução do sistema (`.venv/`, `database/atendimentos.db`, `database/chroma/`, `output/`) e este documento.

Todo número apresentado neste relatório vem de **execução real**, não de leitura de código. Onde uma conclusão vem apenas de inspeção estática, isso está dito explicitamente.

---

## 2. Ambiente de auditoria

| Item | Valor |
|---|---|
| Sistema operacional | Windows 11 Home Single Language 10.0.26200 |
| Shell | PowerShell / Git Bash |
| Python | 3.13.5 |
| Ambiente virtual | `.venv` criado na raiz do projeto |
| Tesseract OCR | **não instalado** (`tesseract` não encontrado no PATH) |
| Poppler (`pdftoppm`) | **não instalado** (não encontrado no PATH) |
| `OPENAI_API_KEY` | não configurada (modo de recuperação local) |
| Rede | disponível (download de dependências e do modelo de embeddings) |

A ausência de Tesseract e Poppler **não é um defeito do sistema** — são pré-requisitos legítimos. Ela é registrada aqui porque determina o comportamento observado na Seção 7 e porque a forma como o sistema reage à ausência deles **é** um achado relevante.

---

## 3. Método

A auditoria seguiu esta ordem, deliberadamente:

1. **Inventário estático** — estrutura de arquivos, dependências declaradas, leitura integral dos 15 módulos.
2. **Leitura dos dados oficiais** — extração do texto dos 4 PDFs para estabelecer, de forma independente, o que o sistema *deveria* produzir.
3. **Execução da suíte de testes** — antes de rodar a aplicação.
4. **Execução do pipeline** — em cópia limpa e em reexecução.
5. **Execução da API e da interface.**
6. **Execução da camada vetorial e do RAG.**
7. **Inspeção das saídas** — banco SQLite, CSV, JSON de indicadores, log e gráficos.

A ordem importa: o *esperado* foi derivado dos PDFs **antes** de olhar para o que o sistema produz, para que o resultado obtido não contaminasse a expectativa.

---

## 4. Inventário do projeto

### 4.1 Estrutura

```
solucao_referencia_desafio_final_python_ia/
├── README.md                  87 linhas
├── requirements.txt           21 dependências
├── config.json                parâmetros e caminhos
├── .env.example               3 variáveis
├── .gitignore                 12 entradas
├── data/
│   ├── auxiliares/
│   │   ├── categorias.json         7 categorias oficiais + variações
│   │   └── config_original.json    cópia de config.json
│   ├── auxiliares_categorias.json  cópia de categorias.json
│   └── pdfs/                       4 documentos oficiais
├── src/                       15 módulos, 500 linhas
└── tests/                     3 arquivos, 5 testes
```

**Total: 856 linhas** entre código, testes e configuração.

**Diretórios ausentes na entrega:** `database/` e `output/`. Ambos são criados em tempo de execução — mas com consequências diferentes, tratadas na Seção 7.1.

### 4.2 Divergências em relação à estrutura do enunciado

| Enunciado (Seção 9) | Entrega | Observação |
|---|---|---|
| `data/categorias.json` | `data/auxiliares/categorias.json` | caminho fixo em `pipeline.py:29`, não vem do `config.json` |
| — | `data/auxiliares_categorias.json` | **cópia byte-idêntica** de `categorias.json` |
| — | `data/auxiliares/config_original.json` | **cópia idêntica** de `config.json` |
| `tests/test_pdf_processor.py` | **ausente** | previsto na estrutura, não existe |
| `database/`, `output/` | ausentes | não versionáveis (ver 7.1) |

Há ainda dois módulos não previstos no enunciado — `cep_client.py` e `indexer.py` —, o que é legítimo: o enunciado permite adaptar a divisão desde que as responsabilidades permaneçam evidentes.

### 4.3 Dependências declaradas

21 pacotes em `requirements.txt`, **todos com `>=` e nenhum fixado**. Consequência: duas instalações em datas diferentes podem produzir ambientes distintos — o requisito de execução reproduzível fica dependente do momento do `pip install`.

Verificação de uso real (busca de `import` em `src/` e `tests/`):

| Dependência | Importada em | Situação |
|---|---|---|
| `nltk` | — | **declarada e nunca usada** |
| `pdfplumber` | — | **declarada e nunca usada** |
| `pypdf` | `pdf_processor.py` | usada |
| `pdf2image`, `pytesseract` | `ocr_processor.py` | usadas (carregamento tardio) |
| `sqlalchemy` | `models.py`, `database.py`, `indexer.py`, `pipeline.py` | usada |
| `pandas`, `numpy`, `matplotlib` | `analytics.py`, `pipeline.py` | usadas |
| `requests` | `cep_client.py`, `app_streamlit.py` | usada |
| `sentence-transformers` | `embeddings.py` | usada (carregamento tardio) |
| `chromadb` | `vector_store.py` | usada (carregamento tardio) |
| `fastapi`, `uvicorn` | `api.py` | usadas |
| `streamlit` | `app_streamlit.py` | usada |
| `langchain`, `langchain-openai` | `rag.py` | usadas (carregamento tardio) |
| `python-dotenv`, `pydantic` | `config.py`, `api.py` | usadas |
| `pytest`, `httpx` | testes | usadas |

O `requirements.txt` pesa **~2,5 GB instalado**, quase todo em `torch`, puxado por `sentence-transformers`. Dois dos pacotes desse conjunto não servem a nada.

**Observação sobre `nltk`:** o RF05 exige documentar a biblioteca de PLN escolhida. O `nltk` está declarado como se fosse ela, mas o processamento de linguagem é feito à mão em `text_processor.py`: uma lista de **19 stopwords** e uma "lematização leve" por remoção de sufixos. É uma decisão defensável — o próprio README a assume —, mas a dependência declarada contradiz o código e a decisão não está documentada onde o requisito pede.

### 4.4 Padrão de carregamento de dependências

Um acerto de projeto que vale registrar: `chromadb`, `sentence-transformers`, `pdf2image`, `pytesseract` e `langchain` são importados **dentro** das funções que os usam, não no topo do módulo. Por isso a API sobe e responde `/health` mesmo sem a pilha vetorial instalada. É a razão de o diagnóstico ter conseguido avançar por etapas.

---

## 5. Pontos de entrada e componentes externos

### 5.1 Pontos de entrada

| Interface | Comando | Módulo |
|---|---|---|
| CLI | `python -m src.main [--indexar] [--pergunta "..."] [--top-k N]` | `src/main.py` |
| HTTP | `uvicorn src.api:app` → `GET /health`, `POST /ask`, `GET /docs` | `src/api.py` |
| Interface | `streamlit run src/app_streamlit.py` | `src/app_streamlit.py` |

### 5.2 Componentes externos

| Componente | Tipo | Obrigatório | Falha tratada |
|---|---|---|---|
| Tesseract OCR | binário de sistema | para PDFs digitalizados | sim, por página (com ressalva — Seção 7.2) |
| Poppler | binário de sistema | exigido por `pdf2image` | idem |
| ViaCEP (`viacep.com.br`) | API HTTP pública | não | sim, cliente tolerante — **mas nunca chamado** |
| OpenAI API | API HTTP autenticada | não | sim, cai para modo local |
| Hugging Face Hub | download de modelo | na primeira indexação | não tratada |

O modelo `paraphrase-multilingual-MiniLM-L12-v2` (~470 MB) é baixado na primeira execução com `--indexar`. Não há verificação prévia de conectividade nem mensagem antecipando o download.

### 5.3 Controle de versão

**A entrega não é um repositório Git.** Existe `.gitignore`, mas não existe `.git`, nem commits, nem branch de desenvolvimento, nem merge, nem a tag `v1.0.0` — todos exigidos pelo RF17. O README reconhece a limitação e a atribui ao formato de entrega em ZIP.

---

## 6. Execução dos testes existentes

### 6.1 Comando publicado no README

```
$ pytest -q
E   ModuleNotFoundError: No module named 'src'
!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in 0.16s
```

**O comando documentado não funciona.** Não há `conftest.py`, `pytest.ini`, `setup.cfg` nem `pyproject.toml` que coloque a raiz do projeto no `sys.path`.

### 6.2 Comando alternativo

```
$ python -m pytest -q
tests\test_api.py:2: in <module>
    from src.api import app
src\api.py:7: in <module>
    from .indexer import semantic_query
src\indexer.py:5: in <module>
    from sqlalchemy import create_engine, select
E   ModuleNotFoundError: No module named 'sqlalchemy'
!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
```

`python -m pytest` funciona apenas por efeito colateral: o `-m` insere o diretório atual no `sys.path`. Mesmo assim a suíte é **interrompida na coleta** — um `ImportError` em um arquivo impede a execução de **todos** os testes, inclusive os que passariam.

### 6.3 Testes que efetivamente executam

```
$ python -m pytest -q tests/test_validation.py tests/test_text_processor.py
....                                                                     [100%]
4 passed in 0.02s
```

Após a instalação completa das dependências, os 5 testes passam.

### 6.4 Cobertura da suíte

| Módulo | Testado |
|---|---|
| `validation.py` | parcialmente (2 testes: registro válido, e-mail inválido) |
| `text_processor.py` | parcialmente (2 testes: chunking, stopwords) |
| `api.py` | superficialmente (2 testes: `/health`, validação de entrada) |
| `pipeline.py`, `analytics.py`, `cep_client.py`, `embeddings.py`, `vector_store.py`, `indexer.py`, `rag.py`, `ocr_processor.py`, `pdf_processor.py`, `database.py`, `models.py`, `config.py` | **nenhum** |

**5 testes para 15 módulos.** Nenhum teste exercita orquestração, OCR, deduplicação, indicadores, gráficos, consumo de API externa ou persistência. Nenhum usa os dados oficiais. O caso de teste de registro válido usa um dicionário construído à mão, não um registro real extraído de PDF — razão pela qual os defeitos de classificação da Seção 9 passaram despercebidos.

Advertência emitida na coleta:

```
StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated;
install `httpx2` instead.
```

---

## 7. Execução do pipeline

### 7.1 Primeira execução em cópia limpa — falha

```
$ python -m src.main
sqlite3.OperationalError: unable to open database file
sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) unable to open database file
(Background on this error at: https://sqlalche.me/e/20/e3q8)
```

**Causa raiz.** O `config.json` aponta o banco para `sqlite:///database/atendimentos.db`. O SQLite **não cria o diretório** do arquivo de banco — verificado isoladamente:

```
>>> sqlite3.connect('.../inexistente/sub/x.db')
OperationalError: unable to open database file
```

O diretório `database/` estava presente, vazio, na pasta entregue — por isso a execução avançou nesta auditoria. Mas **um diretório vazio não é versionável pelo Git**, e o `.gitignore` ainda exclui `database/*.db` e `database/chroma/`. Logo: **todo `git clone` do projeto falhará neste ponto**, e o requisito de execução reproduzível a partir do README não se sustenta.

Confirmado experimentalmente renomeando `database/` e reexecutando.

O diretório `output/` **não** tem o mesmo problema: `configure_logging` chama `path.parent.mkdir(parents=True, exist_ok=True)` antes de escrever o log. A proteção existe para a saída e não para o banco.

### 7.2 Execução com o diretório presente

```
$ python -m src.main
ERROR OCR falhou: atendimentos_digitalizados.pdf p.1
  RuntimeError: Instale pdf2image e pytesseract para executar OCR
ERROR OCR falhou: atendimentos_digitalizados.pdf p.2
  ... (idêntico para as páginas 3, 4, 5, 6 e 7)
Registros encontrados: 75
```

Três comportamentos inesperados nesta saída:

1. **Um documento inteiro é perdido e o processo termina com código de saída zero.** As 7 páginas de `atendimentos_digitalizados.pdf` — 25 registros — falham, os erros são gravados em `erros_processamento`, e a mensagem final anuncia sucesso. Nada no resumo indica perda.

2. **O rastreamento completo é impresso 7 vezes no console e gravado 7 vezes no log**, incluindo caminhos absolutos da máquina do desenvolvedor. São cerca de 120 linhas de rastreamento para uma condição que se resume a "dependência de OCR ausente".

3. **A mensagem de erro é imprecisa.** Diz "Instale pdf2image e pytesseract", mas o problema real, neste ambiente, envolveria também o binário Tesseract e o Poppler. Instalar os dois pacotes Python não resolveria.

### 7.3 Codificação do console

```
INFO Documento j? processado; ignorando: atendimentos_digitais.pdf
```

`configure_logging` cria `logging.StreamHandler()` sem `encoding`. No console do Windows os acentos são corrompidos. O arquivo `output/processamento.log` sai correto em UTF-8 — o defeito é só no terminal, que é justamente onde o operador acompanha a execução.

### 7.4 Reexecução

```
$ python -m src.main          # segunda execução, sem alterar nada
INFO Documento j? processado; ignorando: atendimentos_digitais.pdf
INFO Documento j? processado; ignorando: atendimentos_digitalizados.pdf
INFO Documento j? processado; ignorando: atendimentos_duplicados.pdf
INFO Documento j? processado; ignorando: atendimentos_incompletos.pdf
Registros encontrados: 0
```

A deduplicação por hash SHA-256 funciona — os documentos já processados são corretamente ignorados. O problema é o que acontece em seguida: o `DataFrame` sai vazio, `export_results` e `generate_charts` **não são chamados**, e o operador fica com CSV, indicadores e gráficos da execução anterior, sem nenhum aviso de que estão desatualizados. A mensagem `Registros encontrados: 0` sugere falha onde houve reaproveitamento correto.

Não existe opção de recriar a base. Para reprocessar é preciso apagar `database/` manualmente.

### 7.5 Escopo transacional

Achado por inspeção estática, não reproduzido:

`session_scope(factory)` envolve **todos os quatro laços aninhados** de `process_all` — documentos, páginas, registros e chunks — e só faz `commit` ao final. Um `rollback` disparado no último registro do último documento descartaria o trabalho dos quatro documentos.

Indício corroborante: `IntegrityError` é importado em `pipeline.py:8` e **nunca é utilizado** no arquivo. O tratamento por registro foi previsto e não implementado.

Isso contraria diretamente o requisito não funcional: *"A aplicação não poderá encerrar todo o processamento por causa de um único registro inválido."*

---

## 8. Estado dos dados produzidos

### 8.1 Banco SQLite

| Tabela | Linhas | Observação |
|---|---:|---|
| `documentos` | 4 | 27 páginas somadas |
| `atendimentos` | 64 | duplicados não são persistidos, por decisão de projeto documentada no README |
| `chunks` | 64 | **exatamente 1 por atendimento** |
| `erros_processamento` | 18 | 7 de OCR, 11 de deduplicação |

Consultas de verificação:

```sql
SELECT classificacao, count(*) FROM atendimentos GROUP BY 1;
-- ('invalido', 13) ('valido', 51)     -- a classe 'incompleto' não aparece

SELECT count(*) FROM atendimentos WHERE municipio IS NOT NULL;
-- 0

SELECT etapa, tipo, count(*) FROM erros_processamento GROUP BY 1,2;
-- ('deduplicacao', 'Duplicidade', 11) ('ocr', 'RuntimeError', 7)
```

**Sobre o chunking:** o comprimento médio de `texto_original` é de **382 caracteres** (máximo 459), contra um `tamanho_chunk` configurado de 500. Nenhum registro atinge o corte, então a sobreposição de 80 caracteres **nunca é exercida** e o parâmetro é decorativo. Não é um erro de implementação, mas o RF10 pede que o tamanho e a estratégia de divisão sejam explicados — e a explicação honesta é "um chunk por atendimento", o que muda a discussão sobre recuperação.

**Metadado incorreto:** `atendimentos_digitalizados.pdf` está gravado com `metodo = "ocr"` embora as 7 páginas tenham falhado e nenhum texto tenha sido extraído. O método é derivado da *intenção* de processar, não do resultado.

### 8.2 Indicadores gerados

`output/indicadores.json`, integralmente:

```json
{
  "total_registros": 75,
  "por_classificacao": { "valido": 51, "invalido": 13, "duplicado": 11 },
  "por_categoria": {
    "Python e bibliotecas": 12, "Conectividade": 11, "VSCode e ferramentas": 11,
    "Atividades e arquivos": 10, "Instalacao de software": 10, "Acesso e senha": 10,
    "Ambiente virtual": 9, "categoria desconhecida": 2
  },
  "por_status": { "Pendente": 26, "Em atendimento": 25, "Concluido": 24 },
  "tempo_medio": 50.82608695652174,
  "tempo_mediano": 48.0,
  "tempo_desvio_padrao": 22.7716811939355,
  "percentual_ocr": 0.0
}
```

Confrontando com a Seção 8 do enunciado, **7 indicadores obrigatórios não existem**: total de documentos, total de páginas, *percentual* por classificação, categoria com maior volume, categoria com maior tempo médio, erros por tipo e por etapa, atendimentos por município ou UF.

Três observações sobre os que existem:

- `"categoria desconhecida"` é um valor bruto não oficial, contabilizado junto das sete categorias válidas — porque o pipeline grava `categoria_normalizada or categoria_bruta`.
- As estatísticas de tempo são calculadas sobre os 75 registros, **incluindo os 11 duplicados e os 13 inválidos**.
- `tempo_desvio_padrao` usa `np.std` sem `ddof`, devolvendo desvio populacional onde se espera o amostral.

### 8.3 Arquivos exportados

| Arquivo | Situação |
|---|---|
| `output/atendimentos_processados.csv` | 75 linhas, 16 colunas, UTF-8 — **sem colunas `municipio` e `uf`** |
| `output/indicadores.json` | gerado, incompleto (8.2) |
| `output/processamento.log` | gerado em UTF-8; contém 7 rastreamentos com caminhos absolutos |
| `output/graficos/atendimentos_categoria.png` | legível, com título e eixo identificado |
| `output/graficos/atendimentos_status.png` | legível |
| `output/graficos/tempo_medio_categoria.png` | legível |

Os três gráficos atendem ao RF09 em forma — título, eixos, unidades e dimensões legíveis. O conteúdo herda os problemas de 8.2.

---

## 9. Confronto com os dados oficiais

O esperado foi derivado da leitura direta dos quatro PDFs, registro a registro. Os cabeçalhos dos próprios documentos declaram os totais: **50 digitais + 25 digitalizados + 15 incompletos + 10 duplicados = 100 registros em 27 páginas.**

| Indicador | Esperado | Obtido | Divergência |
|---|---:|---:|---|
| Registros processados | 100 | **75** | 25 registros do PDF digitalizado nunca entram no pipeline |
| Documentos / páginas | 4 / 27 | 4 / 27 | lidos corretamente, mas não exportados como indicador |
| Válidos | 75 | **51** | faltam os 25 do OCR; e um registro sem solicitante entrou como válido |
| Incompletos | 2 | **0** | classe inalcançável na implementação atual |
| Inválidos | 13 | 13 | total coincide **por compensação de dois erros** |
| Duplicados | 10 | **11** | dois protocolos ilegíveis colidem entre si |
| Páginas por OCR | 25,93% | **0,0%** | 7 de 27 páginas |
| Por município / UF | disponível | **ausente** | cliente de CEP nunca chamado |

### 9.1 Perda dos 25 registros digitalizados

`atendimentos_digitalizados.pdf` tem 7 páginas, todas sem texto selecionável, contendo os protocolos AT-051 a AT-075. O pipeline as encaminha corretamente para OCR; o OCR falha por ausência de dependência; as 7 falhas são registradas; o processo continua e reporta sucesso.

Inspeção adicional das páginas revelou que **cada uma contém exatamente uma imagem JPEG de 1241×1754 pixels embutida**, acessível diretamente por `pypdf` (`page.images[0].image`). A rasterização via `pdf2image` — e portanto o Poppler — é dispensável para este conjunto de dados. Além disso, `config.json` pede `dpi: 300` para rasterizar uma imagem que tem cerca de 150 DPI: é ampliação sem ganho de informação.

### 9.2 Classe "incompleto" inalcançável

Os PDFs marcam campos ausentes com o literal **`[vazio]`**:

```
Solicitante
[vazio]
...
Tempo
[vazio] min
```

`validate_record` testa apenas string vazia (`if not r.get(required,"").strip()`). A string `"[vazio]"` é não vazia, logo passa como campo preenchido.

Consequência verificada no CSV:

```
AT-081 | [vazio] | rafael.batista@aluno.exemplo.br | 26.0 | 78550-000 | valido | (sem motivos)
```

**Um registro sem solicitante foi classificado como válido e entrou na base limpa.**

Há um segundo problema, independente: `Tempo [vazio] min` produz o motivo `tempo_invalido` em vez de `tempo_ausente`. E a regra de precedência é

```python
"valido" if not reasons else ("incompleto" if any(x.endswith("_ausente") for x in reasons) else "invalido")
```

— ou seja, um registro simultaneamente incompleto **e** inválido é rotulado **incompleto**, mascarando o erro mais grave. As duas causas somadas explicam o zero absoluto de registros incompletos.

### 9.3 Colisão de protocolos ilegíveis

Dois registros distintos trazem `PROTOCOLO?` no campo de protocolo. Verificado no CSV:

```
linha 66 | atendimentos_incompletos.pdf p.2 | PROTOCOLO? | invalido
linha 73 | atendimentos_incompletos.pdf p.4 | PROTOCOLO? | duplicado   <-- incorreto
```

O segundo é classificado como **duplicata do primeiro**, inflando o total de duplicados de 10 para 11 e criando uma duplicidade que não existe nos dados.

A causa está em `pipeline.py:51`:

```python
protocol = normalized.get("protocolo") or f"INVALIDO-{doc.id}-{page['pagina']}-{len(rows)+1}"
```

Como `normalized["protocolo"]` vale `"PROTOCOLO?"` — verdadeiro em contexto booleano — o `or` nunca dispara. **O fallback é código morto e jamais executa.**

### 9.4 Enriquecimento por CEP nunca executado

`cep_client.lookup_cep` está implementado e bem escrito: normaliza a entrada, aplica timeout, verifica a chave `erro` no corpo da resposta e devolve `None` em vez de propagar exceção. **Nenhum outro módulo o importa.**

O pipeline grava literalmente `municipio=None, uf=None` na criação de cada `Atendimento`. Verificado: 0 de 64 atendimentos com município preenchido; as colunas sequer aparecem no CSV. Isso torna impossível um indicador obrigatório da Seção 8 do enunciado.

### 9.5 Risco identificado para a correção do OCR

Registrado aqui porque muda o esforço estimado da correção.

O PDF digitalizado usa um **layout diferente dos demais**: uma tabela de duas colunas com rótulo e valor lado a lado, e não a lista vertical dos outros arquivos. Além disso, a renderização da digitalização insere espaços dentro das palavras — visível na imagem original como `E-m ail`, `Tem po`, `Program ador de Sistem as`.

Os padrões atuais `E-mail\s+(\S+)` e `Tempo\s+(-?\d+)?\s*min` **não casarão** com esse texto. Instalar o Tesseract, isoladamente, não recuperará os 25 registros: será preciso uma etapa de normalização do texto de OCR antes da extração.

Este achado vem de inspeção da imagem embutida, não de execução do Tesseract — deve ser confirmado assim que o OCR estiver operacional.

---

## 10. Execução da API

```
GET  /health                               200  {'status':'ok','modo':'recuperacao_local'}
POST /ask  {"pergunta":"x"}                422  validação Pydantic — correto
POST /ask  {} (sem pergunta)               422  correto
POST /ask  {"pergunta":"Quais problemas…"} 503  {"detail":"Consulta indisponível: ModuleNotFoundError"}
```

O último caso ocorreu antes da instalação da pilha vetorial. O comportamento é o achado: **`except Exception` converte qualquer falha no mesmo `503`**, e a exceção original é descartada sem ser registrada em log. Dependência ausente, coleção não indexada e falha de rede produzem resposta idêntica. Não há como diagnosticar a causa a partir da resposta nem do log.

Com a pilha completa instalada, `/ask` responde `200` corretamente.

`GET /docs` funciona; a documentação interativa é gerada pelo FastAPI sem configuração adicional.

---

## 11. Execução da interface Streamlit

```
$ streamlit run src/app_streamlit.py --server.headless true --server.port 8599
  Local URL:    http://localhost:8599
  Network URL:  http://192.168.1.10:8599
  External URL: http://160.20.20.126:8599

$ curl -o /dev/null -w "%{http_code}" http://127.0.0.1:8599/
200
```

A interface sobe e renderiza. Dois pontos:

- **A URL da API está fixa no código** (`http://127.0.0.1:8000`), sem variável de ambiente. Mudar porta ou host exige editar o fonte.
- **O Streamlit escuta em todas as interfaces por padrão** e anuncia uma URL externa. Em rede compartilhada, a interface fica acessível a terceiros sem autenticação. Não é um defeito do código entregue, mas precisa constar das limitações conhecidas.

O tratamento de erro de conexão está correto: `requests.RequestException` é capturada e exibida como mensagem legível, conforme o RF16.

---

## 12. Execução da camada vetorial e do RAG

Esta é a parte mais bem resolvida da entrega. Indexação e busca semântica **funcionam de ponta a ponta**.

```
build_index()                        64 chunks indexados em 93,8s
semantic_query() direto              5,7s
POST /ask  (primeira chamada)       15,3s
POST /ask  (chamada seguinte)        5,5s
POST /ask  com filtro de categoria    200  — RF12 atendido
```

Fontes devolvidas para *"Como resolver erro de pip nao reconhecido?"*:

```
AT-003  sim=0.5714   válido
AT-084  sim=0.5052   INVÁLIDO — recuperado sem qualquer marcação
AT-027  sim=0.4881   válido
```

Três achados:

1. **A API recarrega o modelo de embeddings a cada requisição.** `semantic_query` constrói um `SentenceTransformer` e abre um `PersistentClient` do ChromaDB a cada chamada. Daí os 5,5 s constantes mesmo em requisições subsequentes, sem que nada mude entre elas.

2. **Registros inválidos são devolvidos como fonte sem marcação.** A classificação não vai para os metadados do chunk, então não há como filtrar nem sinalizar. Uma resposta pode ser fundamentada em um registro que o próprio sistema classificou como inválido.

3. **O modo local nunca responde.** O campo `resposta` traz sempre o mesmo texto fixo — *"Modo local: foram recuperados os trechos mais semelhantes. Configure OPENAI_API_KEY para gerar uma síntese."* — independentemente do que foi recuperado. O RF13 pede gerar resposta a partir do contexto e informar quando os documentos não a sustentam; sem chave de API, nenhuma das duas coisas acontece.

---

## 13. Qualidade de código

Medições sobre `src/`:

| Métrica | Valor |
|---|---:|
| Funções com docstring | **0 de 41** |
| Funções com anotação de retorno | 32 de 41 |
| Linhas com mais de 120 colunas | **30** |
| Maior linha | **499 caracteres** (`pipeline.py:57`) |
| Módulos com linhas longas | 10 de 15 |

O requisito não funcional é explícito: *"Funções relevantes deverão possuir docstrings e type hints"* e *"O projeto deverá seguir convenções PEP 8"*. Os type hints estão parcialmente presentes; as docstrings, ausentes por completo.

O estilo predominante encadeia comandos com ponto e vírgula em linha única. Não é apenas questão estética: o defeito da Seção 9.3 está escondido no meio de uma linha de 250 caracteres, e a linha de 499 caracteres de `pipeline.py:57` constrói o objeto `Atendimento` inteiro — 17 argumentos — em uma expressão só.

---

## 14. Cobertura dos requisitos

Legenda: **A** atende · **P** atende parcialmente · **N** não atende

| Req. | | Observação |
|---|:--:|---|
| RF01 Inicialização e configuração | P | `python -m src.main` e `config.json` funcionam; caminho de `categorias.json` fixo no código; sem repositório Git |
| RF02 Detecção e extração de PDFs | A | `pathlib`, detecção por limiar de caracteres, `pypdf`, encaminhamento a OCR e registro de documento/página/método |
| RF03 OCR | N | 0 de 7 páginas processadas; a falha não interrompe os demais arquivos e é registrada — mas nenhum texto é recuperado |
| RF04 Extração, validação e classificação | P | regex e validações funcionam; classe "incompleto" inalcançável; colisão de protocolos ilegíveis |
| RF05 Processamento de linguagem natural | P | normaliza sem apagar o original, tokeniza, remove 19 stopwords, lematização heurística; biblioteca declarada (`nltk`) não é a usada; decisões não documentadas |
| RF06 Persistência SQLite/SQLAlchemy | P | 4 modelos, sessão e transação presentes; **operação de atualização não implementada**; recriação do banco não é previsível |
| RF07 Consumo de API HTTP (CEP) | N | cliente implementado e nunca chamado |
| RF08 Análise de dados | P | Pandas e NumPy usados; 7 indicadores obrigatórios ausentes; base contaminada por duplicados |
| RF09 Visualização e exportação | P | 3 gráficos legíveis, CSV, JSON e log gerados; conteúdo herda os problemas dos indicadores |
| RF10 Chunking e metadados | P | id único e metadados rastreáveis presentes; estratégia não calibrada (1 chunk por registro) nem explicada |
| RF11 Embeddings e busca semântica | A | `sentence-transformers`, cosseno, top-k configurável, pontuação e procedência exibidas |
| RF12 ChromaDB | A | coleção persistente, `upsert` idempotente, consulta e filtro por categoria verificados |
| RF13 RAG | P | recupera e cita fontes; **modo local não gera resposta nem declara insuficiência** |
| RF14 OpenAI API e LangChain | P | chave por variável de ambiente, cadeia LangChain, modo local presente; não verificável sem chave; tratamento de falha genérico |
| RF15 FastAPI | P | `/health`, `/ask`, `/docs` e validação corretos; `503` genérico para toda falha |
| RF16 Streamlit | A | campo de pergunta, consumo de `/ask`, resposta, fontes e erro de conexão tratados; URL fixa no código |
| RF17 Controle de versão | N | não há repositório, commits, branch, merge nem tag `v1.0.0` |

| Requisito não funcional | | Observação |
|---|:--:|---|
| Módulos com responsabilidades claras | P | boa separação entre arquivos; `process_all` concentra dez responsabilidades |
| Docstrings e type hints | N | 0 de 41 docstrings; 32 de 41 anotações de retorno |
| Não encerrar tudo por um registro inválido | N | transação única cobrindo os quatro documentos |
| Mensagens e logs claros e úteis | N | acentuação corrompida no console; `503` opaco; "0 registros" em reexecução bem-sucedida |
| Codificação UTF-8 nos arquivos gerados | A | CSV, JSON e log corretos |
| PEP 8, sem segredos nem caminhos absolutos | P | **nenhum segredo no código** — este ponto está correto; 30 linhas acima de 120 colunas; log contém caminhos absolutos |
| Execução reproduzível a partir do README | N | `pytest` documentado não funciona; `git clone` falha na criação do banco; README cobre apenas Linux |

---

## 15. Erros, advertências e comportamentos inesperados

Consolidado do que foi observado em execução.

### 15.1 Erros

| # | Evidência | Seção |
|---|---|---|
| 1 | `sqlite3.OperationalError: unable to open database file` em cópia limpa | 7.1 |
| 2 | `RuntimeError: Instale pdf2image e pytesseract` × 7 páginas | 7.2 |
| 3 | `ModuleNotFoundError: No module named 'src'` no `pytest` do README | 6.1 |
| 4 | `Interrupted: 1 error during collection` — suíte inteira abortada | 6.2 |
| 5 | `503 Consulta indisponível: ModuleNotFoundError` sem log da causa | 10 |

### 15.2 Advertências

| # | Evidência | Seção |
|---|---|---|
| 6 | `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated` | 6.4 |
| 7 | `datetime.utcnow()` depreciado no Python 3.12+ (`models.py`, dois usos) | inspeção |
| 8 | Aviso de symlink do Hugging Face no Windows durante o download do modelo | 12 |

### 15.3 Comportamentos inesperados

| # | Comportamento | Seção |
|---|---|---|
| 9 | Perda de 25 registros com código de saída zero e mensagem de sucesso | 7.2 / 9.1 |
| 10 | Registro com solicitante `[vazio]` classificado como **válido** | 9.2 |
| 11 | Classe "incompleto" com zero ocorrências em base que a exercita | 9.2 |
| 12 | Dois protocolos ilegíveis tratados como duplicata um do outro | 9.3 |
| 13 | Reexecução reporta `0` registros e mantém saídas desatualizadas em silêncio | 7.4 |
| 14 | Acentuação corrompida no console do Windows | 7.3 |
| 15 | `municipio` e `uf` sempre nulos; colunas ausentes do CSV | 9.4 |
| 16 | `metodo = "ocr"` gravado para documento cujo OCR falhou integralmente | 8.1 |
| 17 | Categoria não oficial contabilizada e plotada junto das oficiais | 8.2 |
| 18 | `/ask` leva 5,5 s por requisição mesmo aquecido | 12 |
| 19 | Registro inválido devolvido como fonte do RAG sem marcação | 12 |
| 20 | Modo local nunca produz resposta a partir do contexto | 12 |
| 21 | Fallback de protocolo em `pipeline.py:51` é código morto | 9.3 |
| 22 | `IntegrityError` importado e nunca usado | 7.5 |
| 23 | `nltk` e `pdfplumber` declarados e nunca importados | 4.3 |
| 24 | Ramo `db_url.startswith("sqlite:/// ")` — com espaço — nunca é verdadeiro | inspeção |

---

## 16. Síntese

**O sistema executa e produz saídas, o que faz com que pareça pronto. Não está.**

O ponto central do diagnóstico não é a quantidade de defeitos, e sim o **modo de falha**: nenhum dos problemas mais graves se manifesta como erro. Um quarto dos dados oficiais desaparece com o processo relatando sucesso. Uma das quatro classificações exigidas nunca ocorre, e o total de inválidos ainda assim "bate" — por compensação entre dois erros independentes. Um registro sem responsável passa pela validação. O enriquecimento por CEP simplesmente não acontece. Metade dos indicadores obrigatórios não existe.

Um operador que rodasse `python -m src.main`, visse `Registros encontrados: 75` e abrisse os gráficos concluiria que o sistema funciona.

**O que está sólido e deve ser preservado na correção:**

- a separação em módulos, com fronteiras claras entre extração, validação, persistência, análise e recuperação;
- o carregamento tardio das dependências pesadas, que permite operar em partes;
- a camada vetorial completa — indexação, busca por cosseno, metadados rastreáveis e filtro por categoria, todos verificados em execução;
- o modo sem chave de API, que é real e não apenas um aviso;
- a ausência de segredos no código, com `.env` corretamente ignorado e `.env.example` contendo apenas nomes de variáveis;
- o cliente de CEP, bem escrito — falta apenas chamá-lo.

**Prioridade imediata**, nesta ordem: tornar a execução repetível em cópia limpa; quebrar o escopo transacional único; recuperar os 25 registros digitalizados; tornar a classificação "incompleto" alcançável. As três primeiras são condição para que qualquer medição posterior signifique alguma coisa.

O registro individual dos 34 defeitos, o plano de correção priorizado, o plano de melhoria e o roteiro de implantação constam de documentos próprios.

---

## Anexo A — Comandos de reprodução

```powershell
# ambiente
cd "<raiz do projeto>"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

# testes — estado inicial
pytest -q                                     # falha: No module named 'src'
python -m pytest -q                           # falha na coleta de test_api.py
python -m pytest -q tests/test_validation.py tests/test_text_processor.py

# pipeline sem o diretório de banco
Rename-Item database database_bak
python -m src.main                            # OperationalError
Rename-Item database_bak database

# pipeline completo e reexecução
python -m src.main
python -m src.main                            # "Registros encontrados: 0"

# conferência das saídas
python -c "import json;d=json.load(open('output/indicadores.json',encoding='utf-8'));print(d['total_registros'],d['por_classificacao'])"
python -c "import sqlite3;print(sqlite3.connect('database/atendimentos.db').execute('select etapa,tipo,count(*) from erros_processamento group by 1,2').fetchall())"
python -c "import sqlite3;print(sqlite3.connect('database/atendimentos.db').execute('select count(*) from atendimentos where municipio is not null').fetchone())"

# API e interface
python -m src.main --indexar
uvicorn src.api:app --port 8000
streamlit run src/app_streamlit.py
```

Métricas de código da Seção 13 (docstrings e anotações, via AST):

```powershell
python -c "import ast,pathlib; f=[n for p in pathlib.Path('src').glob('*.py') for n in ast.walk(ast.parse(p.read_text(encoding='utf-8'))) if isinstance(n,ast.FunctionDef)]; print('funcoes',len(f),'docstring',sum(1 for n in f if ast.get_docstring(n)),'retorno',sum(1 for n in f if n.returns))"
```

---

## Anexo B — Artefatos gerados durante a auditoria

| Caminho | Origem |
|---|---|
| `.venv/` | ambiente virtual da auditoria |
| `database/atendimentos.db` | execução do pipeline — linha de base "antes das correções" |
| `database/chroma/` | indexação vetorial |
| `output/atendimentos_processados.csv` | 75 registros, estado inicial |
| `output/indicadores.json` | indicadores do estado inicial |
| `output/processamento.log` | log com as 7 falhas de OCR |
| `output/graficos/*.png` | 3 gráficos do estado inicial |

Recomenda-se **preservar cópia de `output/` e `database/` antes de iniciar as correções**, para sustentar a comparação exigida pela Etapa 3 do desafio.
