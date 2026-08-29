# Catálogo de Defeitos

**Sistema auditado:** `solucao_referencia_desafio_final_python_ia`
**Desafio 2 — Introdução a Python para IA · FIC_DEV, Programador de Sistemas com IA**
**Data:** 29 de agosto de 2026
**Etapa do desafio:** 4 — Correção dos defeitos (registro prévio)
**Documento de origem:** `docs/RELATORIO_DIAGNOSTICO_INICIAL.md`

**Total: 34 defeitos** — 3 P0, 13 P1, 15 P2, 3 P3. Todos com status **Aberto** nesta versão.

---

## Como ler este catálogo

Cada ficha traz os campos abaixo. Os dois primeiros são o mínimo exigido pelo enunciado; os demais existem para que a correção possa começar sem reabrir a investigação.

| Campo | Conteúdo |
|---|---|
| **Identificador** | `BUG-0NN`, estável — não reaproveitar números |
| **Descrição** | comportamento observado, em termos do que o sistema faz |
| **Prioridade** | P0 a P3, conforme a tabela abaixo |
| **Local** | arquivo e linha na entrega original |
| **Evidência** | como o defeito foi constatado |
| **Causa raiz** | o mecanismo, quando identificado |
| **Impacto** | o que se perde enquanto o defeito existir |
| **Correção proposta** | direção técnica, não implementação fechada |
| **Requisito violado** | RF/RNF do enunciado |
| **Critério de aceite** | como provar que a correção funcionou |
| **Status** | Aberto · Em correção · Corrigido · Não será corrigido |

### Prioridades

| | Significado |
|---|---|
| **P0** | Correção imediata: segurança, perda de dados ou indisponibilidade crítica |
| **P1** | Necessária para funcionamento confiável |
| **P2** | Melhoria importante de qualidade, desempenho ou manutenção |
| **P3** | Evolução futura ou conveniência |

### Origem da constatação

Trinta e um defeitos foram **reproduzidos em execução**. Três vêm de **inspeção estática** e estão marcados como tal na ficha: `BUG-003`, `BUG-032` e `BUG-029`. A distinção importa: os estáticos precisam ser confirmados durante a correção.

### Linha de base preservada

O estado "antes das correções" está em `old_database/` e `old_output/`, na raiz do desafio. É a evidência que sustenta a comparação da Etapa 3 — não sobrescrever.

---

## Índice

| ID | Pri. | Título | Local principal |
|---|:--:|---|---|
| [BUG-001](#bug-001) | P0 | O pipeline não inicia em cópia limpa do repositório | `database.py:8` |
| [BUG-002](#bug-002) | P0 | 25 registros descartados em silêncio: o OCR nunca executa | `ocr_processor.py` |
| [BUG-003](#bug-003) | P0 | Toda a ingestão roda em uma única transação | `pipeline.py:35` |
| [BUG-004](#bug-004) | P1 | `[vazio]` é tratado como valor legítimo | `validation.py:60` |
| [BUG-005](#bug-005) | P1 | A classificação "incompleto" é inalcançável | `validation.py:55` |
| [BUG-006](#bug-006) | P1 | Protocolos ilegíveis colidem e viram falsas duplicatas | `pipeline.py:51` |
| [BUG-007](#bug-007) | P1 | O enriquecimento por CEP nunca é executado | `cep_client.py` |
| [BUG-008](#bug-008) | P1 | Sete indicadores obrigatórios não existem | `analytics.py:9` |
| [BUG-009](#bug-009) | P1 | `percentual_ocr` mede registros, não páginas | `analytics.py:19` |
| [BUG-010](#bug-010) | P1 | O comando de teste do README não funciona | raiz do projeto |
| [BUG-011](#bug-011) | P1 | Um import quebrado derruba a suíte inteira | `test_api.py:2` |
| [BUG-012](#bug-012) | P1 | `/ask` engole a causa real de qualquer falha | `api.py:26` |
| [BUG-013](#bug-013) | P1 | A API recarrega o modelo de embeddings a cada requisição | `indexer.py:22` |
| [BUG-014](#bug-014) | P1 | Reexecutar não atualiza as saídas e reporta zero | `pipeline.py:62` |
| [BUG-015](#bug-015) | P1 | Nenhuma função documentada; PEP 8 amplamente violada | todo `src/` |
| [BUG-032](#bug-032) | P1 | Os padrões de extração não sobreviverão ao texto do OCR | `validation.py:9` |
| [BUG-016](#bug-016) | P2 | Duplicados contaminam os indicadores | `pipeline.py:53` |
| [BUG-017](#bug-017) | P2 | Categorias não oficiais vazam para indicadores e gráficos | `pipeline.py:53` |
| [BUG-018](#bug-018) | P2 | Desvio-padrão populacional onde se espera o amostral | `analytics.py:18` |
| [BUG-019](#bug-019) | P2 | Caminho de `categorias.json` fixo no código e arquivo duplicado | `pipeline.py:29` |
| [BUG-020](#bug-020) | P2 | Acentuação corrompida no console do Windows | `pipeline.py:18` |
| [BUG-021](#bug-021) | P2 | O log de entrega contém caminhos absolutos da máquina | `pipeline.py:48` |
| [BUG-022](#bug-022) | P2 | `Documento.metodo` grava um metadado falso | `pipeline.py:41` |
| [BUG-023](#bug-023) | P2 | `split_chunks` degenera com sobreposição alta | `text_processor.py:24` |
| [BUG-024](#bug-024) | P2 | Dependências não usadas e versões não fixadas | `requirements.txt` |
| [BUG-025](#bug-025) | P2 | `observacoes` é extraído mas não chega ao banco | `models.py:20` |
| [BUG-026](#bug-026) | P2 | `--pergunta` reprocessa os quatro PDFs antes de responder | `main.py:13` |
| [BUG-027](#bug-027) | P2 | URL da API fixa no código do Streamlit | `app_streamlit.py:11` |
| [BUG-031](#bug-031) | P2 | A entrega não é um repositório Git | raiz do projeto |
| [BUG-033](#bug-033) | P2 | O RAG cita registros inválidos como fonte, sem marcação | `pipeline.py:60` |
| [BUG-034](#bug-034) | P2 | O modo local nunca responde a partir do contexto | `rag.py:7` |
| [BUG-028](#bug-028) | P3 | `datetime.utcnow` depreciado | `models.py:17` |
| [BUG-029](#bug-029) | P3 | Ramo morto na resolução da URL do banco | `pipeline.py:31` |
| [BUG-030](#bug-030) | P3 | Suíte de testes insuficiente e arquivo previsto ausente | `tests/` |

---

# Prioridade P0

<a id="bug-001"></a>
## BUG-001 — O pipeline não inicia em cópia limpa do repositório

| | |
|---|---|
| **Prioridade** | P0 |
| **Local** | `src/database.py:8-11`; `config.json` → `banco.url`; `.gitignore` |
| **Status** | Aberto |

**Descrição.** Com o diretório `database/` ausente, `create_engine` falha imediatamente e nada é processado:

```
sqlite3.OperationalError: unable to open database file
sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) unable to open database file
```

**Evidência.** Reproduzido renomeando `database/` e reexecutando `python -m src.main`. Verificado isoladamente que o SQLite não cria o diretório do arquivo de banco.

**Causa raiz.** Três fatos que só produzem o defeito quando combinados: o SQLite não cria diretórios; o Git não versiona diretórios vazios; e o `.gitignore` exclui `database/*.db` e `database/chroma/`. O diretório existia, vazio, na pasta entregue — por isso a execução avançou nesta auditoria. Após um `git clone`, ele não existirá.

Note o contraste: `configure_logging` chama `mkdir(parents=True, exist_ok=True)` para o diretório de saída. A proteção foi escrita para `output/` e não para `database/`.

**Impacto.** Todo clone novo do projeto falha na primeira execução. O requisito de execução reproduzível a partir do README não se sustenta.

**Correção proposta.** Criar o diretório-pai do arquivo de banco em `create_session_factory`, antes de abrir a conexão. Versionar `database/.gitkeep` e `output/.gitkeep`. Extrair a resolução da URL do SQLite para uma função pura e testável (ver `BUG-029`).

**Requisito violado.** RF01 · RNF — execução reproduzível a partir do README.

**Critério de aceite.** A sequência `git clone` → `pip install -r requirements.txt` → `python -m src.main` conclui sem nenhum passo manual de criação de diretório.

---

<a id="bug-002"></a>
## BUG-002 — 25 registros descartados em silêncio: o OCR nunca executa

| | |
|---|---|
| **Prioridade** | P0 |
| **Local** | `src/ocr_processor.py`; `src/pipeline.py:45-48`; `src/main.py:13` |
| **Status** | Aberto |

**Descrição.** As 7 páginas de `atendimentos_digitalizados.pdf` — protocolos AT-051 a AT-075 — falham no OCR. As falhas são gravadas em `erros_processamento`, o processo continua e termina com **código de saída zero** e a mensagem `Registros encontrados: 75`. Nada no resumo indica que um documento inteiro ficou de fora.

**Evidência.**

```
ERROR OCR falhou: atendimentos_digitalizados.pdf p.1
  RuntimeError: Instale pdf2image e pytesseract para executar OCR
... (idêntico para as páginas 2 a 7)
Registros encontrados: 75
```

Confirmado no banco: `documentos` = 4, mas `atendimentos_digitalizados.pdf` contribuiu com 0 atendimentos.

**Causa raiz.** Dupla, e as duas partes precisam ser corrigidas.

1. `ocr_processor` depende de `pdf2image`, que exige o binário **Poppler** — dependência de sistema pesada. Nada verifica a presença de Poppler ou Tesseract antes de começar a processar; a descoberta acontece página a página, sete vezes.
2. O resumo final não distingue "processado com sucesso" de "processado com um documento inteiro perdido". Erros são registrados mas não influenciam o código de saída, a mensagem final nem os indicadores.

A segunda parte é a mais grave: é o mecanismo pelo qual a perda passa despercebida.

**Impacto.** 25% da base oficial não chega ao banco. Todos os indicadores derivados ficam errados. Um operador que visse `Registros encontrados: 75` e abrisse os gráficos concluiria que o sistema funciona.

**Correção proposta.** Extrair a imagem embutida diretamente com `pypdf`: cada página escaneada contém exatamente um JPEG de 1241×1754 acessível por `page.images[0].image`, o que **elimina a dependência de Poppler** e a rasterização a 300 DPI de uma imagem que tem cerca de 150 DPI. Manter `pdf2image` como caminho alternativo. Verificar Tesseract na inicialização, com mensagem acionável. Encerrar com código diferente de zero quando um documento perder 100% das páginas.

Ver `BUG-032`: corrigir este defeito isoladamente **não** recupera os 25 registros.

**Requisito violado.** RF03 · RNF — mensagens claras e úteis para diagnóstico.

**Critério de aceite.** `atendimentos_digitalizados.pdf` produz 25 registros; o pipeline reporta explicitamente páginas por método e encerra com código diferente de zero se houver perda total em algum documento.

---

<a id="bug-003"></a>
## BUG-003 — Toda a ingestão roda em uma única transação

| | |
|---|---|
| **Prioridade** | P0 |
| **Local** | `src/pipeline.py:35-61`; `src/database.py:13-23` |
| **Status** | Aberto — **constatado por inspeção estática, não reproduzido** |

**Descrição.** `session_scope(factory)` envolve os quatro laços aninhados de `process_all` — documentos, páginas, registros e chunks — e só faz `commit` ao final. Uma exceção no último registro do último documento dispara `rollback` e descarta o trabalho dos quatro documentos. Não há `try/except` por registro.

**Evidência.** Leitura de `pipeline.py:35-61`. Indício corroborante: `IntegrityError` é importado em `pipeline.py:8` e **nunca utilizado** — o tratamento por registro foi previsto e não implementado.

**Impacto.** Contraria diretamente um requisito não funcional explícito. Além do risco de perda total, é o que impede tratar registros defeituosos de forma isolada — a arquitetura atual não tem onde encaixar esse tratamento.

**Correção proposta.** Uma transação por documento. `session.begin_nested()` (SAVEPOINT) em volta de cada inserção de atendimento, com `except` gravando `ErroProcessamento` e seguindo para o próximo registro. Capturar `IntegrityError` explicitamente, que é o caso previsto e não tratado.

**Requisito violado.** RNF — *"A aplicação não poderá encerrar todo o processamento por causa de um único registro inválido."*

**Critério de aceite.** Teste que injeta um registro que viola a restrição de unicidade no meio do lote e verifica que os demais registros e documentos foram persistidos.

---

# Prioridade P1

<a id="bug-004"></a>
## BUG-004 — `[vazio]` é tratado como valor legítimo

| | |
|---|---|
| **Prioridade** | P1 |
| **Local** | `src/validation.py:44-62` |
| **Status** | Aberto |

**Descrição.** Os PDFs marcam campos ausentes com o literal `[vazio]`. A validação testa apenas string vazia (`if not r.get(required,"").strip()`), e `"[vazio]"` é não vazia — logo passa como campo preenchido.

**Evidência.** Linha do CSV do estado inicial:

```
AT-081 | [vazio] | rafael.batista@aluno.exemplo.br | 26.0 | 78550-000 | valido | (sem motivos)
```

**Um registro sem solicitante foi classificado como válido** e entrou na base limpa. O mesmo ocorre com AT-088.

**Impacto.** Registros sem responsável identificado passam pela validação e são contabilizados como válidos. É a causa direta de metade do `BUG-005`.

**Correção proposta.** Função única de normalização de sentinelas — `[vazio]`, `N/A`, `-`, `--`, `?`, string em branco — aplicada a todos os campos antes da validação, devolvendo valor ausente.

**Requisito violado.** RF04.

**Critério de aceite.** AT-081 e AT-088 classificados como `incompleto` com motivo `solicitante_ausente`.

---

<a id="bug-005"></a>
## BUG-005 — A classificação "incompleto" é inalcançável

| | |
|---|---|
| **Prioridade** | P1 |
| **Local** | `src/validation.py:55-62` |
| **Status** | Aberto |

**Descrição.** Zero registros classificados como `incompleto` em 75 processados, embora `atendimentos_incompletos.pdf` exista justamente para exercitar essa classe. O sistema entrega três das quatro classificações exigidas.

**Evidência.**

```sql
SELECT classificacao, count(*) FROM atendimentos GROUP BY 1;
-- ('invalido', 13) ('valido', 51)
```

**Causa raiz.** Duas causas somadas, mais um terceiro problema independente:

1. Os sentinelas `[vazio]` escapam da detecção de ausência (`BUG-004`).
2. `Tempo [vazio] min` produz o motivo `tempo_invalido` em vez de `tempo_ausente` — o bloco `try/except` em torno de `float()` não distingue "campo vazio" de "valor malformado".
3. A precedência está invertida:

```python
"valido" if not reasons else ("incompleto" if any(x.endswith("_ausente") for x in reasons) else "invalido")
```

Um registro simultaneamente inválido **e** incompleto é rotulado `incompleto`, mascarando o erro mais grave.

**Impacto.** Um dos quatro estados exigidos pelo RF04 nunca ocorre. A separação entre "faltou informação" e "informação errada" — que é o objetivo do requisito — não existe.

**Correção proposta.** Emitir motivos `*_ausente` e `*_invalido` de forma independente para cada campo. Inverter a precedência: qualquer motivo `_invalido` classifica como inválido; só motivos de ausência classificam como incompleto.

**Convenção adotada e a registrar no README:** campo ausente → incompleto; campo presente porém malformado → inválido; havendo ambos, prevalece inválido. Por essa regra AT-076 (e-mail inválido *e* tempo vazio) fica como inválido. Qualquer outra convenção muda os totais esperados.

**Requisito violado.** RF04 — classificar como válido, incompleto, inválido ou duplicado.

**Critério de aceite.** `atendimentos_incompletos.pdf` produz 2 incompletos e 13 inválidos.

---

<a id="bug-006"></a>
## BUG-006 — Protocolos ilegíveis colidem e viram falsas duplicatas

| | |
|---|---|
| **Prioridade** | P1 |
| **Local** | `src/pipeline.py:51-52` |
| **Status** | Aberto |

**Descrição.** Dois registros distintos trazem `PROTOCOLO?` no campo de protocolo. Ambos recebem a mesma chave; o segundo é classificado **duplicado** em vez de **inválido**.

**Evidência.** CSV do estado inicial:

```
linha 66 | atendimentos_incompletos.pdf p.2 | PROTOCOLO? | invalido
linha 73 | atendimentos_incompletos.pdf p.4 | PROTOCOLO? | duplicado   <-- incorreto
```

**Causa raiz.**

```python
protocol = normalized.get("protocolo") or f"INVALIDO-{doc.id}-{page['pagina']}-{len(rows)+1}"
```

Como `normalized["protocolo"]` vale `"PROTOCOLO?"` — verdadeiro em contexto booleano — o `or` nunca dispara. **O fallback é código morto e jamais executa.** A condição correta seria "não casa com `PROTO_RE`", não "é falsy".

**Impacto.** Infla o total de duplicados de 10 para 11 e cria uma duplicidade que não existe nos dados. Também impede que o segundo registro seja persistido, já que duplicados não vão para o banco.

**Correção proposta.** Trocar a condição por `if not PROTO_RE.fullmatch(protocolo)`, gerando a chave sintética a partir de documento, página e índice.

**Requisito violado.** RF04 · RF06 — impedir duplicidade de protocolo.

**Critério de aceite.** Os dois registros com `PROTOCOLO?` classificados como `invalido`, com chaves distintas, e total de duplicados igual a 10.

---

<a id="bug-007"></a>
## BUG-007 — O enriquecimento por CEP nunca é executado

| | |
|---|---|
| **Prioridade** | P1 |
| **Local** | `src/cep_client.py` (não referenciado); `src/pipeline.py:57` |
| **Status** | Aberto |

**Descrição.** `cep_client.lookup_cep` está implementado, é tolerante a falhas e **nenhum outro módulo o importa**. O pipeline grava literalmente `municipio=None, uf=None` na criação de cada `Atendimento`.

**Evidência.**

```sql
SELECT count(*) FROM atendimentos WHERE municipio IS NOT NULL;
-- 0
```

As colunas `municipio` e `uf` também não aparecem no CSV exportado.

**Impacto.** Torna impossível o indicador obrigatório "atendimentos por município ou UF" e o terceiro gráfico sugerido pelo enunciado. Um módulo inteiro do sistema é código morto.

**Correção proposta.** Chamar `lookup_cep` para cada CEP válido, com cache em memória por CEP — os dados repetem cerca de 8 CEPs em 100 registros, reduzindo de 100 para 8 requisições. Respeitar `api.timeout_segundos`, registrar falhas em `ErroProcessamento`, nunca interromper o pipeline e reportar quantos CEPs foram resolvidos.

**Ressalva.** Se o ViaCEP estiver indisponível ou bloqueado, os indicadores por município ficarão parciais. O comportamento correto é degradar, não falhar — e o relatório precisa dizer quantos foram resolvidos.

**Requisito violado.** RF07 · RF08 · RF09.

**Critério de aceite.** Com rede disponível, os atendimentos com CEP válido têm `municipio` e `uf` preenchidos, as colunas constam do CSV e o indicador por município existe. Com rede indisponível, o pipeline conclui e registra as falhas.

---

<a id="bug-008"></a>
## BUG-008 — Sete indicadores obrigatórios não existem

| | |
|---|---|
| **Prioridade** | P1 |
| **Local** | `src/analytics.py:9-20` |
| **Status** | Aberto |

**Descrição.** `indicadores.json` traz 8 chaves. Confrontando com a Seção 8 do enunciado, faltam:

1. total de documentos processados
2. total de páginas processadas
3. **percentual** por classificação (só há contagem absoluta)
4. categoria com maior volume
5. categoria com maior tempo médio
6. erros por tipo e por etapa
7. atendimentos por município ou UF

**Evidência.** Conteúdo integral do `indicadores.json` do estado inicial, em `old_output/`.

**Causa raiz.** `build_indicators` recebe apenas o `DataFrame` de registros. Totais de documento e página e o agregado de erros existem dentro de `process_all` e não são repassados.

**Impacto.** Metade dos indicadores obrigatórios da avaliação não é produzida. Os dados existem no banco — falta agregá-los.

**Correção proposta.** Estender a assinatura de `build_indicators` para receber também os totais de documento/página e o agregado de erros. O item 7 depende de `BUG-007`.

**Requisito violado.** RF08 · Seção 8 do enunciado.

**Critério de aceite.** `indicadores.json` cobre os oito itens da Seção 8.

---

<a id="bug-009"></a>
## BUG-009 — `percentual_ocr` mede registros, não páginas

| | |
|---|---|
| **Prioridade** | P1 |
| **Local** | `src/analytics.py:19` |
| **Status** | Aberto |

**Descrição.** O enunciado pede o percentual de **páginas** processadas por OCR. O cálculo é `(df["metodo"] == "ocr").mean() * 100` — a proporção de **registros**. Valor esperado: 7/27 = 25,93%; valor obtido: 0,0%.

**Causa raiz.** Além do denominador errado, há um problema estrutural: páginas que falham no OCR não produzem registro algum, então o indicador nunca as enxerga. Mesmo com o OCR funcionando, um documento com falha parcial seria contabilizado incorretamente.

**Impacto.** Indicador obrigatório com valor errado, e errado de um modo que esconde exatamente a falha que deveria expor.

**Correção proposta.** Contabilizar o método por página durante a extração e calcular o percentual sobre o total de páginas dos documentos, não sobre o `DataFrame` de registros.

**Requisito violado.** RF08 · Seção 8 do enunciado.

**Critério de aceite.** Após `BUG-002`, `percentual_ocr` = 25,93% (7 de 27 páginas).

---

<a id="bug-010"></a>
## BUG-010 — O comando de teste do README não funciona

| | |
|---|---|
| **Prioridade** | P1 |
| **Local** | raiz do projeto (ausência de `pyproject.toml` / `conftest.py`); `README.md` |
| **Status** | Aberto |

**Descrição.** O comando publicado no README falha:

```
$ pytest -q
E   ModuleNotFoundError: No module named 'src'
!!! Interrupted: 1 error during collection !!!
```

**Causa raiz.** Não há `conftest.py`, `pytest.ini`, `setup.cfg` nem `pyproject.toml` que coloque a raiz do projeto no `sys.path`. `python -m pytest` funciona apenas por efeito colateral: o `-m` insere o diretório atual no `sys.path`.

**Impacto.** Quem segue o README não consegue rodar os testes. O requisito de execução reproduzível a partir da documentação não se sustenta.

**Correção proposta.** `pyproject.toml` com `[tool.pytest.ini_options] pythonpath = ["."]` — corrige as duas formas de invocação e fixa o `rootdir`.

**Requisito violado.** RNF — execução reproduzível a partir do README.

**Critério de aceite.** `pytest` puro, a partir da raiz, coleta e executa a suíte.

---

<a id="bug-011"></a>
## BUG-011 — Um import quebrado derruba a suíte inteira

| | |
|---|---|
| **Prioridade** | P1 |
| **Local** | `tests/test_api.py:2`; `src/api.py:7`; `src/indexer.py:5` |
| **Status** | Aberto |

**Descrição.** `test_api.py` importa `src.api`, que importa `src.indexer`, que importa `sqlalchemy` no topo do módulo. Sem SQLAlchemy instalado, a coleta é abortada e **nenhum** teste roda — nem os quatro que passariam.

**Evidência.**

```
src\indexer.py:5: in <module>
    from sqlalchemy import create_engine, select
E   ModuleNotFoundError: No module named 'sqlalchemy'
!!! Interrupted: 1 error during collection !!!
```

**Causa raiz.** Acoplamento desnecessário: `api.py` puxa a camada de persistência inteira só para conseguir responder `/health`. O padrão de carregamento tardio usado com acerto para `chromadb` e `sentence-transformers` não foi aplicado aqui.

**Impacto.** Um ambiente parcialmente instalado não consegue rodar nem os testes que não dependem da parte ausente — exatamente o cenário de um diagnóstico inicial.

**Correção proposta. `--continue-on-collection-errors` não resolve a causa.** Marcar os testes de API com `pytest.importorskip` e reduzir o acoplamento de `api.py`, adiando o import de `indexer` para dentro do handler de `/ask`.

**Requisito violado.** RNF — responsabilidades claras por módulo.

**Critério de aceite.** Com SQLAlchemy ausente, os testes de `validation` e `text_processor` executam normalmente e os de API são pulados com mensagem clara.

---

<a id="bug-012"></a>
## BUG-012 — `/ask` engole a causa real de qualquer falha

| | |
|---|---|
| **Prioridade** | P1 |
| **Local** | `src/api.py:26-27` |
| **Status** | Aberto |

**Descrição.** `except Exception` converte toda falha no mesmo `503 "Consulta indisponível: {tipo}"`, e a exceção original é descartada **sem ser registrada em log**.

**Evidência.**

```
POST /ask {"pergunta":"Quais problemas…"}  503  {"detail":"Consulta indisponível: ModuleNotFoundError"}
```

Dependência ausente, coleção não indexada e falha de rede produzem resposta idêntica.

**Impacto.** Não há como diagnosticar a causa a partir da resposta nem do log. Em uma demonstração ao vivo, qualquer problema vira a mesma mensagem inútil.

**Correção proposta.** Registrar a exceção com `logger.exception`. Separar os casos: coleção não indexada → 409 com instrução acionável (*"execute `python -m src.main --indexar`"*); indisponibilidade real → 503; inesperado → 500.

**Requisito violado.** RF15 — códigos HTTP adequados · RNF — logs úteis para diagnóstico.

**Critério de aceite.** Consulta com coleção vazia devolve código distinto de 503 e mensagem que diz o que fazer; toda exceção aparece no log com rastreamento.

---

<a id="bug-013"></a>
## BUG-013 — A API recarrega o modelo de embeddings a cada requisição

| | |
|---|---|
| **Prioridade** | P1 |
| **Local** | `src/indexer.py:21-26`; `src/api.py:24` |
| **Status** | Aberto |

**Descrição.** `semantic_query` instancia `EmbeddingService` — que constrói um `SentenceTransformer` — e abre um `PersistentClient` do ChromaDB **a cada chamada** de `/ask`.

**Evidência.** Medido com a pilha completa instalada:

```
POST /ask  (primeira chamada)   15,3s
POST /ask  (chamada seguinte)    5,5s
```

Os 5,5 s se repetem em todas as requisições subsequentes, sem que nada mude entre elas.

**Impacto.** Latência inaceitável para uma interface interativa. O modelo ocupa centenas de MB e é reconstruído por requisição; chamadas concorrentes multiplicam isso. A demonstração do pitch fica visivelmente lenta.

**Correção proposta.** Carregar modelo e coleção uma vez no `lifespan` do FastAPI e injetá-los na consulta. Manter uma fábrica com `functools.lru_cache` para o uso via CLI.

**Requisito violado.** RNF — desempenho e responsabilidades claras.

**Critério de aceite.** Segunda requisição a `/ask` responde em menos de 1 s.

---

<a id="bug-014"></a>
## BUG-014 — Reexecutar não atualiza as saídas e reporta zero

| | |
|---|---|
| **Prioridade** | P1 |
| **Local** | `src/pipeline.py:62-65`; `src/main.py:13` |
| **Status** | Aberto |

**Descrição.** Na segunda execução os quatro documentos são corretamente ignorados pelo hash, mas o `DataFrame` sai vazio, `export_results` e `generate_charts` **não são chamados**, e o operador fica com CSV, indicadores e gráficos da execução anterior sem nenhum aviso.

**Evidência.**

```
INFO Documento j? processado; ignorando: atendimentos_digitais.pdf
... (os quatro documentos)
Registros encontrados: 0
```

**Impacto.** A mensagem sugere falha onde houve reaproveitamento correto. Saídas desatualizadas passam por atuais — problema sério durante um ciclo de correção, em que o mesmo comando será executado muitas vezes. Não existe opção de recriar a base: é preciso apagar `database/` à mão.

**Correção proposta.** Quando não houver documento novo, reconstruir o `DataFrame` a partir do banco e reexportar. Informar `"N documentos já processados, M atendimentos em base"`. Acrescentar `--recriar` para descartar banco e coleção vetorial.

**Requisito violado.** RF06 — recriar ou reutilizar o banco de forma previsível.

**Critério de aceite.** Segunda execução reexporta as saídas e informa o estado real; `--recriar` reprocessa do zero.

---

<a id="bug-015"></a>
## BUG-015 — Nenhuma função documentada; PEP 8 amplamente violada

| | |
|---|---|
| **Prioridade** | P1 |
| **Local** | todo `src/` |
| **Status** | Aberto |

**Descrição.** Medições por AST sobre `src/`:

| Métrica | Valor |
|---|---:|
| Funções com docstring | **0 de 41** |
| Funções com anotação de retorno | 32 de 41 |
| Linhas com mais de 120 colunas | **30** |
| Maior linha | **499 caracteres** (`pipeline.py:57`) |
| Módulos com linhas longas | 10 de 15 |

**Impacto.** Além de violar dois requisitos não funcionais explícitos, é o que torna a revisão custosa. `BUG-006` está escondido no meio de uma linha de 250 caracteres, e a linha de 499 caracteres de `pipeline.py:57` constrói o objeto `Atendimento` inteiro — 17 argumentos — em uma expressão só.

**Correção proposta.** Adicionar `ruff` (`line-length = 100`, regras `E,F,I,D`). Quebrar as linhas compostas por ponto e vírgula. Documentar as funções públicas de cada módulo.

**Requisito violado.** RNF — docstrings e type hints · RNF — PEP 8.

**Critério de aceite.** `ruff check` sem apontamentos; todas as funções públicas com docstring.

---

<a id="bug-032"></a>
## BUG-032 — Os padrões de extração não sobreviverão ao texto do OCR

| | |
|---|---|
| **Prioridade** | P1 |
| **Local** | `src/validation.py:9-14` (`FIELD_PATTERNS`); `src/ocr_processor.py` |
| **Status** | Aberto — **constatado por inspeção da imagem, a confirmar com o Tesseract instalado** |

**Descrição.** `atendimentos_digitalizados.pdf` usa um **layout diferente dos demais**: tabela de duas colunas com rótulo e valor lado a lado, e não a lista vertical dos outros arquivos. Além disso, a renderização da digitalização insere espaços dentro das palavras — visível na imagem original como `E-m ail`, `Tem po`, `Program ador de Sistem as`.

Os padrões `E-mail\s+(\S+)` e `Tempo\s+(-?\d+)?\s*min` não casam com esse texto.

**Evidência.** Inspeção da imagem embutida na página 1, extraída com `pypdf` e renderizada. O README da entrega já admite: *"A extração por regex foi ajustada ao formulário fornecido."*

**Impacto.** Este é o defeito que pode fazer `BUG-002` parecer corrigido sem recuperar os 25 registros. Instalar o Tesseract, isoladamente, não resolve.

**Correção proposta.** Etapa de normalização do texto de OCR antes da extração: reunir letras separadas por espaço espúrio; corrigir confusões frequentes (`0`/`O`, `1`/`l`, `5`/`S`) **apenas dentro de campos numéricos**; tornar os rótulos tolerantes a espaço interno (`E\s*-?\s*m\s*ail`). Preservar o texto bruto, como exige o RF03.

**Alternativa a avaliar** (ver plano de melhoria, MEL-03): extrair por posição de tabela com `pdfplumber` em vez de regex sobre texto corrido — imune ao espaçamento e usando uma dependência já declarada e hoje ociosa.

**Requisito violado.** RF03 · RF04.

**Critério de aceite.** Ao menos 90% dos campos dos 25 registros digitalizados recuperados corretamente; protocolo, data e categoria em 100%.

---

# Prioridade P2

<a id="bug-016"></a>
## BUG-016 — Duplicados contaminam os indicadores

**Prioridade** P2 · **Local** `src/pipeline.py:53-56`, `src/analytics.py:9-20` · **Status** Aberto

**Descrição.** Os 11 registros duplicados entram no `DataFrame` e são contados em `por_categoria`, `por_status` e nas estatísticas de tempo, junto dos 13 inválidos. `tempo_medio = 50,83` é calculado sobre uma base que inclui registros que o próprio sistema rejeitou.

**Impacto.** Indicadores analíticos inflados e não comparáveis com a base persistida (75 no CSV × 64 no banco).

**Correção proposta.** Calcular indicadores analíticos sobre válidos + incompletos; reportar duplicados e inválidos separadamente, como contagens de qualidade.

**Requisito violado.** RF08. **Critério de aceite.** Indicadores de tempo e categoria calculados sobre a base útil, com a base de cálculo declarada no próprio JSON.

---

<a id="bug-017"></a>
## BUG-017 — Categorias não oficiais vazam para indicadores e gráficos

**Prioridade** P2 · **Local** `src/pipeline.py:53`, `src/analytics.py:31-34` · **Status** Aberto

**Descrição.** A linha do `DataFrame` grava `categoria_normalizada or categoria_bruta`. Quando a normalização falha, o valor bruto entra no lugar da categoria oficial. Resultado: `"categoria desconhecida"` aparece no `indicadores.json` e é plotada no gráfico oficial ao lado das sete categorias válidas.

**Impacto.** O gráfico de atendimentos por categoria mostra 8 barras onde existem 7 categorias oficiais.

**Correção proposta.** Manter `categoria` (oficial, podendo ser nula) e `categoria_bruta` em colunas distintas. Plotar apenas a oficial, com `"Não classificada"` como rótulo explícito.

**Requisito violado.** RF04 · RF09. **Critério de aceite.** Gráfico com no máximo 7 categorias oficiais mais um rótulo explícito de não classificadas.

---

<a id="bug-018"></a>
## BUG-018 — Desvio-padrão populacional onde se espera o amostral

**Prioridade** P2 · **Local** `src/analytics.py:18` · **Status** Aberto

**Descrição.** `np.std(times)` sem `ddof` devolve o desvio populacional. Para uma amostra de atendimentos, espera-se `ddof=1`.

**Correção proposta.** `np.std(times, ddof=1)` com guarda para `n < 2`.

**Requisito violado.** RF08. **Critério de aceite.** Valor confere com `pandas.Series.std()` sobre a mesma base.

---

<a id="bug-019"></a>
## BUG-019 — Caminho de `categorias.json` fixo no código e arquivo duplicado

**Prioridade** P2 · **Local** `src/pipeline.py:29`, `config.json`, `data/` · **Status** Aberto

**Descrição.** O caminho `data/auxiliares/categorias.json` está embutido em `pipeline.py`, fora do `config.json`, contrariando o RF01 (*"ler caminhos e parâmetros de config.json"*). O diretório `data/auxiliares/` também não consta da estrutura do enunciado, que prevê `data/categorias.json`. Além disso o arquivo está duplicado, byte a byte, em `data/auxiliares_categorias.json`, e `config.json` está duplicado em `data/auxiliares/config_original.json`.

**Impacto.** Quem seguir a estrutura do enunciado coloca o arquivo onde o código não procura. As cópias criam ambiguidade sobre qual é a fonte de verdade.

**Correção proposta.** Mover o caminho para `config.json`; remover as cópias redundantes.

**Requisito violado.** RF01. **Critério de aceite.** Alterar o caminho no `config.json` muda de onde as categorias são lidas, sem tocar no código.

---

<a id="bug-020"></a>
## BUG-020 — Acentuação corrompida no console do Windows

**Prioridade** P2 · **Local** `src/pipeline.py:18-20` · **Status** Aberto

**Descrição.** `logging.StreamHandler()` é criado sem `encoding`. No console do Windows os acentos são corrompidos: `Documento j? processado; ignorando: ...`. O arquivo `.log` sai correto em UTF-8 — o defeito é só no terminal, que é justamente onde o operador acompanha a execução.

**Correção proposta.** `logging.StreamHandler(io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace"))`.

**Requisito violado.** RNF — mensagens claras. **Critério de aceite.** Acentuação correta no console do Windows.

---

<a id="bug-021"></a>
## BUG-021 — O log de entrega contém caminhos absolutos da máquina

**Prioridade** P2 · **Local** `src/pipeline.py:48` · **Status** Aberto

**Descrição.** `logging.exception` grava o rastreamento completo, com caminhos absolutos da máquina do desenvolvedor, no `output/processamento.log` — que é um artefato de entrega. São cerca de 120 linhas de rastreamento para as sete falhas de OCR, todas com a mesma causa.

**Impacto.** O RNF proíbe explicitamente caminhos absolutos dependentes da máquina do discente. O log fica ilegível para diagnóstico.

**Correção proposta.** Mensagem curta e acionável no log de entrega; rastreamento completo apenas em modo `--verbose`. Agrupar falhas repetidas de mesma causa.

**Requisito violado.** RNF — sem caminhos absolutos dependentes da máquina · RNF — logs úteis. **Critério de aceite.** `processamento.log` sem caminhos absolutos.

---

<a id="bug-022"></a>
## BUG-022 — `Documento.metodo` grava um metadado falso

**Prioridade** P2 · **Local** `src/pipeline.py:41-42` · **Status** Aberto

**Descrição.** `atendimentos_digitalizados.pdf` está gravado com `metodo = "ocr"` embora as 7 páginas tenham falhado e nenhum texto tenha sido extraído. O método é derivado da *intenção* de processar, avaliada antes da execução, não do resultado.

**Impacto.** O banco afirma algo falso sobre o próprio processamento. Qualquer indicador derivado desse campo herda o erro.

**Correção proposta.** Derivar o método a partir das páginas efetivamente processadas, com valores `extracao_direta`, `ocr`, `misto` e `falhou`.

**Requisito violado.** RF02 — registrar documento, página e método de extração. **Critério de aceite.** Documento com OCR falho não é registrado como processado por OCR.

---

<a id="bug-023"></a>
## BUG-023 — `split_chunks` degenera com sobreposição alta

**Prioridade** P2 · **Local** `src/text_processor.py:22-34` · **Status** Aberto

**Descrição.** A validação aceita `overlap` até `size-1`. Com `overlap > size/2`, o avanço por iteração degenera: medido, `size=100, overlap=90` produz **189 chunks para 1.600 caracteres** — avanço de cerca de 8 caracteres por iteração.

**Impacto.** Latente com os valores atuais (500/80), mas ambos vêm do `config.json` e podem ser alterados sem aviso. Explosão quadrática de chunks e de custo de indexação.

**Correção proposta.** Exigir `overlap <= size // 2` e garantir avanço mínimo por iteração.

**Requisito violado.** RF10. **Critério de aceite.** Teste que rejeita `overlap` acima da metade e verifica avanço mínimo.

---

<a id="bug-024"></a>
## BUG-024 — Dependências não usadas e versões não fixadas

**Prioridade** P2 · **Local** `requirements.txt` · **Status** Aberto

**Descrição.** `nltk` e `pdfplumber` são declarados e **nunca importados** em `src/` ou `tests/`. Nenhuma das 21 dependências tem versão fixada — todas usam `>=`.

**Impacto.** Instalações em datas diferentes produzem ambientes distintos, o que contraria o requisito de reprodutibilidade. Sobre o `nltk`: o RF05 exige documentar a biblioteca de PLN escolhida, e a declarada não é a usada — o processamento é feito à mão em `text_processor.py`, com 19 stopwords e lematização heurística por sufixo.

**Correção proposta.** Remover as não usadas ou passar a usá-las (ver MEL-03 para `pdfplumber`). Gerar `requirements.lock.txt` com versões congeladas. Documentar a decisão de PLN no README.

**Requisito violado.** RF05 · RNF — reprodutibilidade. **Critério de aceite.** Toda dependência declarada é importada; existe arquivo de versões congeladas.

---

<a id="bug-025"></a>
## BUG-025 — `observacoes` é extraído mas não chega ao banco

**Prioridade** P2 · **Local** `src/models.py:20-43`, `src/pipeline.py:57` · **Status** Aberto

**Descrição.** `FIELD_PATTERNS` extrai `observacoes`, o campo é exportado no CSV, e o modelo `Atendimento` não tem coluna correspondente. A informação existe no arquivo de saída e não na base.

**Correção proposta.** Acrescentar a coluna ao modelo e persistir o campo.

**Requisito violado.** RF06. **Critério de aceite.** `observacoes` presente no banco e no CSV, com o mesmo conteúdo.

---

<a id="bug-026"></a>
## BUG-026 — `--pergunta` reprocessa os quatro PDFs antes de responder

**Prioridade** P2 · **Local** `src/main.py:13-16` · **Status** Aberto

**Descrição.** `main()` chama `process_all(cfg)` incondicionalmente, antes de tratar `--pergunta`. Consultar exige atravessar o pipeline inteiro.

**Impacto.** Consulta por linha de comando lenta e com efeito colateral inesperado — o usuário que quer perguntar algo acaba reprocessando a base.

**Correção proposta.** Tornar o processamento explícito (`--processar`) ou pulá-lo quando houver `--pergunta`.

**Requisito violado.** RNF — responsabilidades claras. **Critério de aceite.** `--pergunta` responde sem reprocessar os PDFs.

---

<a id="bug-027"></a>
## BUG-027 — URL da API fixa no código do Streamlit

**Prioridade** P2 · **Local** `src/app_streamlit.py:11` · **Status** Aberto

**Descrição.** `http://127.0.0.1:8000` está embutido na chamada `requests.post`. Mudar porta ou host exige editar o fonte.

**Correção proposta.** Ler de `API_BASE_URL`, com o valor atual como padrão.

**Nota relacionada, não é defeito do código:** o Streamlit escuta em todas as interfaces por padrão e anuncia uma URL externa ao subir. Em rede compartilhada, a interface fica acessível a terceiros sem autenticação. Usar `--server.address 127.0.0.1` na demonstração e registrar o ponto nas limitações conhecidas.

**Requisito violado.** RF16 · RNF — sem caminhos e endereços fixos. **Critério de aceite.** `API_BASE_URL` altera o destino sem editar código.

---

<a id="bug-031"></a>
## BUG-031 — A entrega não é um repositório Git

**Prioridade** P2 · **Local** raiz do projeto · **Status** Aberto

**Descrição.** Existe `.gitignore`, mas não existe `.git`, nem commits, nem branch de desenvolvimento, nem merge, nem a tag `v1.0.0`. O README reconhece a limitação e a atribui ao formato de entrega em ZIP.

**Impacto.** O RF17 é integralmente não atendido, e ele é avaliado.

**Correção proposta.** Inicializar o repositório no início da Onda 1, abrir a branch `correcao`, commitar por onda de correção, integrar à principal e criar a tag `v1.0.0` na entrega. O trabalho de correção gera naturalmente o histórico exigido.

**Requisito violado.** RF17. **Critério de aceite.** Repositório com ao menos três commits coerentes, uma branch de desenvolvimento integrada e a tag `v1.0.0`.

---

<a id="bug-033"></a>
## BUG-033 — O RAG cita registros inválidos como fonte, sem marcação

**Prioridade** P2 · **Local** `src/pipeline.py:60` (metadados do chunk), `src/indexer.py:26` · **Status** Aberto

**Descrição.** A recuperação semântica devolve como fonte registros classificados como inválidos, sem nenhuma indicação. Verificado: consulta *"Como resolver erro de pip nao reconhecido?"* devolveu `AT-084` (inválido, `sim=0.5052`) entre as três primeiras fontes.

**Causa raiz.** `classificacao` não vai para os metadados do chunk — só protocolo, documento, página e categoria. Não há como filtrar nem sinalizar.

**Impacto.** Uma resposta pode ser fundamentada em um registro que o próprio sistema rejeitou, sem que o usuário saiba.

**Correção proposta.** Gravar `classificacao` nos metadados do chunk, filtrar por padrão e exibir o rótulo junto de cada fonte.

**Requisito violado.** RF10 · RF13. **Critério de aceite.** Fontes trazem a classificação; registros inválidos ficam fora por padrão.

---

<a id="bug-034"></a>
## BUG-034 — O modo local nunca responde a partir do contexto

**Prioridade** P2 · **Local** `src/rag.py:7-8` · **Status** Aberto

**Descrição.** Sem `OPENAI_API_KEY`, o campo `resposta` traz sempre o mesmo texto fixo — *"Modo local: foram recuperados os trechos mais semelhantes. Configure OPENAI_API_KEY para gerar uma síntese."* — independentemente do que foi recuperado.

**Impacto.** O RF13 pede gerar resposta a partir do contexto **e** informar quando os documentos não a sustentam. Sem chave, nenhuma das duas coisas acontece. Como o modo sem chave é o modo padrão de avaliação, o requisito fica sem demonstração.

**Correção proposta.** Compor uma resposta extrativa a partir dos trechos de maior similaridade, citando protocolos, e declarar insuficiência quando a melhor pontuação ficar abaixo de um limiar.

**Requisito violado.** RF13 · RF14 — oferecer modo local de recuperação sem chamada ao modelo. **Critério de aceite.** Sem chave, `/ask` devolve texto derivado das fontes recuperadas; pergunta fora do domínio recebe declaração explícita de insuficiência.

---

# Prioridade P3

<a id="bug-028"></a>
## BUG-028 — `datetime.utcnow` depreciado

**Prioridade** P3 · **Local** `src/models.py:17` e `:64` · **Status** Aberto

**Descrição.** `datetime.utcnow` está depreciado no Python 3.12+ e emite `DeprecationWarning`. Dois usos, ambos como `default` de coluna.

**Correção proposta.** `lambda: datetime.now(timezone.utc)`.

**Critério de aceite.** Suíte sem `DeprecationWarning` originado no projeto.

---

<a id="bug-029"></a>
## BUG-029 — Ramo morto na resolução da URL do banco

**Prioridade** P3 · **Local** `src/pipeline.py:31` · **Status** Aberto — constatado por inspeção estática

**Descrição.** `if db_url.startswith("sqlite:/// ")` — com um espaço após as três barras — nunca é verdadeiro. A linha seguinte trata o caso real.

**Impacto.** Baixo isoladamente, mas a lógica de resolução da URL está duplicada entre `pipeline.py:31-32` e `indexer.py:13`, sem teste — é o tipo de duplicação que produz divergência silenciosa.

**Correção proposta.** Remover o ramo morto e extrair a resolução para uma função pura em `config.py`, usada pelos dois módulos e coberta por teste. Resolve junto parte de `BUG-001`.

**Critério de aceite.** Função única, testada, usada em `pipeline` e `indexer`.

---

<a id="bug-030"></a>
## BUG-030 — Suíte de testes insuficiente e arquivo previsto ausente

**Prioridade** P3 · **Local** `tests/` · **Status** Aberto

**Descrição.** 5 testes para 15 módulos. `tests/test_pdf_processor.py`, previsto na estrutura do enunciado, não existe. Sem cobertura: `pipeline`, `analytics`, `cep_client`, `embeddings`, `vector_store`, `indexer`, `rag`, `ocr_processor`, `pdf_processor`, `database`, `models`, `config`.

Nenhum teste usa os dados oficiais. O caso de "registro válido" monta um dicionário à mão em vez de partir de um registro real extraído de PDF — razão pela qual `BUG-004`, `BUG-005` e `BUG-006` passaram despercebidos.

**Prioridade.** Classificado P3 por ser evolução, não correção — **mas deve ser executado junto de cada onda**, não ao final. Cada defeito corrigido ganha o teste que o teria detectado.

**Correção proposta.** Criar `test_pdf_processor.py`. Elevar a suíte a cerca de 25 testes, incluindo um caso de ponta a ponta com PDF sintético e casos derivados dos dados oficiais.

**Requisito violado.** Seção 9 do enunciado — estrutura do projeto.

**Critério de aceite.** Cada defeito corrigido tem um teste que falha na versão anterior e passa na corrigida.

---

# Rastreabilidade

## Por módulo

| Módulo | Defeitos |
|---|---|
| `src/pipeline.py` | BUG-002, BUG-003, BUG-006, BUG-014, BUG-016, BUG-017, BUG-019, BUG-020, BUG-021, BUG-022, BUG-029, BUG-033 |
| `src/validation.py` | BUG-004, BUG-005, BUG-032 |
| `src/analytics.py` | BUG-008, BUG-009, BUG-016, BUG-017, BUG-018 |
| `src/api.py` | BUG-011, BUG-012, BUG-013 |
| `src/indexer.py` | BUG-011, BUG-013, BUG-029, BUG-033 |
| `src/ocr_processor.py` | BUG-002, BUG-032 |
| `src/database.py` | BUG-001, BUG-003 |
| `src/models.py` | BUG-025, BUG-028 |
| `src/rag.py` | BUG-034 |
| `src/main.py` | BUG-002, BUG-014, BUG-026 |
| `src/text_processor.py` | BUG-023 |
| `src/cep_client.py` | BUG-007 |
| `src/app_streamlit.py` | BUG-027 |
| `tests/` | BUG-011, BUG-030 |
| raiz / configuração | BUG-001, BUG-010, BUG-019, BUG-024, BUG-031 |

`src/config.py`, `src/embeddings.py`, `src/vector_store.py` e `src/pdf_processor.py` não acumulam defeitos próprios.

## Por requisito

| Requisito | Defeitos |
|---|---|
| RF01 Inicialização e configuração | BUG-001, BUG-019 |
| RF02 Detecção e extração de PDFs | BUG-022 |
| RF03 OCR | BUG-002, BUG-032 |
| RF04 Extração, validação e classificação | BUG-004, BUG-005, BUG-006, BUG-017 |
| RF05 Processamento de linguagem natural | BUG-024 |
| RF06 Persistência SQLite/SQLAlchemy | BUG-006, BUG-014, BUG-025 |
| RF07 Consumo de API HTTP (CEP) | BUG-007 |
| RF08 Análise de dados | BUG-007, BUG-008, BUG-009, BUG-016, BUG-018 |
| RF09 Visualização e exportação | BUG-007, BUG-017 |
| RF10 Chunking e metadados | BUG-023, BUG-033 |
| RF13 RAG | BUG-033, BUG-034 |
| RF14 OpenAI API e LangChain | BUG-034 |
| RF15 FastAPI | BUG-012 |
| RF16 Streamlit | BUG-027 |
| RF17 Controle de versão | BUG-031 |
| Seção 8 — indicadores obrigatórios | BUG-008, BUG-009 |
| Seção 9 — estrutura do projeto | BUG-019, BUG-030 |
| RNF — não encerrar por um registro inválido | BUG-003 |
| RNF — docstrings, type hints e PEP 8 | BUG-015 |
| RNF — mensagens e logs úteis | BUG-002, BUG-012, BUG-020, BUG-021 |
| RNF — sem caminhos absolutos da máquina | BUG-021 |
| RNF — execução reproduzível pelo README | BUG-001, BUG-010, BUG-024 |
| RNF — responsabilidades claras e desempenho | BUG-011, BUG-013, BUG-026 |

RF11 e RF12 não acumulam defeitos: a camada de embeddings e o ChromaDB foram verificados em execução e atendem.

## Ordem de correção

Ondas conforme o plano de correção. A ordem entre as Ondas 1 e 2 não é negociável: sem a Onda 1 não há execução repetível, e sem a Onda 2 os números da Onda 3 não significam nada.

| Onda | Objetivo | Defeitos |
|---|---|---|
| **1 — Destravar** | Fazer o sistema iniciar e testar em cópia limpa | BUG-001, BUG-003, BUG-010, BUG-011, BUG-029, BUG-031 |
| **2 — Recuperar os dados** | Chegar aos 100 registros com classificação correta | BUG-002, BUG-032, BUG-004, BUG-005, BUG-006, BUG-022 |
| **3 — Completar os indicadores** | Entregar os indicadores e gráficos exigidos | BUG-007, BUG-008, BUG-009, BUG-014, BUG-016, BUG-017, BUG-018, BUG-025 |
| **4 — Endurecer a entrega** | Qualidade de serviço, legibilidade e conformidade | BUG-012, BUG-013, BUG-015, BUG-019, BUG-020, BUG-021, BUG-023, BUG-024, BUG-026, BUG-027, BUG-028, BUG-030, BUG-033, BUG-034 |

`BUG-030` é exceção: os testes acompanham cada onda, não a última.

## Resultado esperado ao final das Ondas 1 a 3

| Indicador | Antes | Depois |
|---|---:|---:|
| Registros processados | 75 | **100** |
| Válidos | 51 | **75** |
| Incompletos | 0 | **2** |
| Inválidos | 13 | **13** |
| Duplicados | 11 | **10** |
| Páginas por OCR | 0,0% | **25,93%** |
| Atendimentos com município | 0 | **conforme resolução do ViaCEP** |
| Indicadores no JSON | 8 | **15** |

Linha de base do "antes" preservada em `old_database/` e `old_output/`.
