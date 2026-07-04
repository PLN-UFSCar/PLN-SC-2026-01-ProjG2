# Extração de Informação baseada em Sintaxe de Dependências
## Análise de Relações Causais em Notícias em Português

Projeto da disciplina de **Processamento de Linguagem Natural**

Identificação automática de relações causais (`O que causou o quê?`) em textos
jornalísticos em português, usando o corpus **CST News** (NILC/USP) e suas
anotações RST como fonte de supervisão.

## Resultados

| Estratégia | Precisão | Recall | F1 | Acurácia |
|---|---|---|---|---|
| **Estratégia 2** — Supervisionada (BERTimbau, 5-fold CV) | 0,758 | 0,774 | **0,766** | 0,763 |
| Estratégia 1 — Regras de dependência (casamento estrito) | 0,122 | 0,057 | 0,077 | — |

A Estratégia 2 é o resultado principal. O F1 baixo da Estratégia 1 sob casamento
estrito reflete a divergência entre a segmentação sintática (intra-sentencial) e
a anotação discursiva do RST — discutido no relatório.

## Arquivos

| Arquivo | Descrição |
|---|---|
| `parseRST.py` | Extrai os 283 pares causais de referência (gold) das anotações RST; inclui leitura robusta dos `.rs3` (UTF-8/ISO-8859-1) |
| `estrategia1_regras.py` | Estratégia 1: regras de dependência (spaCy `pt_core_news_lg`) — marcadores causais, locuções e verbos causativos |
| `estrategia2_supervisionado.py` | Estratégia 2: pares codificados por BERTimbau + Regressão Logística, validação cruzada 5-fold |
| `avaliacao.py` | Constrói gold/negativos, normaliza segmentos e avalia as duas estratégias |
| `bootstrap.py` | Bootstrapping exploratório de padrões causais (não integrado ao pipeline final) |
| `DatasetCSTNews/` | Corpus CST News (170 arquivos `.rs3`, 52 clusters) |

## Instalação

```bash
pip install -r requirements.txt
python -m spacy download pt_core_news_lg
```

## Execução

```bash
python avaliacao.py                     # estatísticas do corpus
python estrategia1_regras.py            # avalia Estratégia 1
python estrategia2_supervisionado.py    # avalia Estratégia 2 (baixa BERTimbau na 1ª vez)
```

## Dataset

CST News — NILC, USP/ICMC. https://sites.icmc.usp.br/taspardo/sucinto/cstnews.html
Corpus de livre disponibilização, incluído no repositório (`DatasetCSTNews/`).

## Equipe

Bruna Luiza Pereira (800325) · Pedro · Laura Mota Brentano (800522) · João Lucas Gomes Pelegrino (822033)
