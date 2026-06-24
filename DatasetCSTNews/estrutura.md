Dataset na versão 6.0 obtido em: https://sites.icmc.usp.br/taspardo/sucinto/cstnews.html

> [!NOTE]
> Cada notícia é um *cluster*, composto por documentos, em que cada um é um texto escrito por um jornal sobre a notícia. 

# *Cluster* 
Cada *cluster* é representado por uma pasta (CX_Tema_NomeCurto) composta pelas pastas:

## Textos-fonte
Textos originais e o título de cada um (_titulo.txt). O nome de cada documento é composto por seu número e o do seu *cluster*, o jornal fonte, e o dia, mês, ano e hora de publicação no momento da criação do *corpus* (Dn_CX_Jornal_dd-mm-aaaa_xxhxx).

## Textos-fonte segmentados
Textos originais com sentenças delimitadas pelo caractere de nova linha.

## Sumarios
- Resumo manual de cada documento no *cluster* (_sumario_humano.txt)
- Informações sobre cada documento - a essência do texto (gist), o tamanho do texto em número de palavras, o tamanho esperado do súmario (30% do texto fonte), o sumário, e seu tamanho real - fornecidas por um humano (_dados.txt)
- O resumo manual da notícia do *cluster* (_sumario_humano.txt)
- Extratos obtidos manualmente dos textos, correspondem ao resumo (_extrato_humano.txt)
- Um resumo automático da notícia produzido pelo sistema CSTSumm (_sumario_automatico_CSTSumm.txt)
- A versão com sentenças manualmente ordenadas do resumo automático (_sumario_automatico_CSTSumm_ordenado_manuamente.txt)
- A pasta "Novos sumários" contém 5 resumos e 5 extratos produzidos manualmente, separados nas subpastas "Abstracts" e "Extratos"

## Expressoes temporais
Expressões temporais manualmente identificadas e normalizadas (com tags XML) para cada documento de acordo com a proposta em [Baptista et al. (2008)](http://www.linguateca.pt/HAREM/actas/LivroSegundoHAREM.html)

## RST
A anotação RST de cada documento obtida pela [RSTTool](http://www.wagsoft.com/RSTTool/) de Michael O'Donnell - os documentos que foram usados para concordância de anotação computacional RST têm seu *cluster* sinalizado por "-concordanciaRST", além de haver a subpasta chamada "concordancia" neste diretório

## CST
A anotação CST do *cluster* (para todos pares possíveis de documentos) a partir da CSTTool - os *clusters* que foram usados para concordância de anotação computacional CST são sinalizados por "-concordanciaCST", além de haver a subpasta chamada "concordancia" neste mesmo diretório

## dls
Na subpasta "noun", os arquivos anotam 10% dos substantivos mais frequentes, e na "verb" todos os verbos: 
- Os textos fonte com os termos acompanhados pelo seus números de identificação do Princeton Wordnet synset (.dls) 
- Um arquivo XML para todos documentos que mostra os detalhes da anotação manual de sentido das palavras (como as possíveis traduções de Português para Inglês, se elas foram feitas manualmente ou automaticamente, os possíveis synsets e o que foi escolhido)
- Um arquivo XML com ontologias dos termos correspondentes composto pelos synsets selecionados na Princeton Wordnet (_ontology_all.xml)

## CX_Tópicos
- Um arquivo para cada documento, contendo a segmentação manual em subtópicos (na tag do tipo xml "t") assim como as palavras-chave (no atributo "label") que representam o subtópico correspondente (logo acima da tag tipo xml), além de um identificador único para cada subtópico (no atributo "top") o que permite a busca por outras ocorrências de um mesmo subtópico em outros documentos do *cluster* (uma vez que também possuem o mesmo identificador único);
- Um arquivo "notasCX.txt", que armazena informações sobre a lista de trechos pertencentes a cada subtópico, o número de sentenças e palavras de cada subtópico, e a presença de cada subtópico no resumo manual da notícia (não entendi qual deles)
- Um arquivo "_agrupamento_manual.txt", que resume a distribuição de subtópicos nos textos (a primeira coluna indica o id do subtópico, a segunda coluna indica o id do documento, e a terceira coluna indica o id da sentença que pertence ao subtópico indicado)

## Analise_sintatica
Arquivos `xml` para cada texto fonte e cada título correspondente com sua análise sintática, que foi automaticamente produzida pelo [parser PALAVRAS](http://visl.sdu.dk/) (Bick, 2000)

## Alignment
Um arquivo `txt` com formato semelhante a `xml` que indica as sentenças do documento que foram alinhadas a cada sentença do resumo da notícia criado manualmente, assim como o tipo de relação de cada alinhamento e os avaliadores humanos que o indicaram

## Aspectos
Um arquivo `txt` com o resumo manual de todos documentos com as sentenças anotadas de acordo com seus aspectos; nesse caso, aspectos se referem às informações que as sentenças passam, por exemplo, O QUE, ONDE e QUANDO do evento (baseado na proposta TAC para tarefa de resumo guiado - http://www.nist.gov/tac/2010/Summarization/Guided-Summ.2010.guidelines.html)

# For all the clusters
A anotação de coreferência (nominal) (de acordo com a tarefa de anotação [IberEval 2017](https://sites.icmc.usp.br/taspardo/IberEval2017-PardoEtAl.pdf) - http://ontolp.inf.pucrs.br/corref/ibereval2017/) e as ontologias produzidas durante a anotação DLS.
O *corpus* completo produzido durante a tarefa IberEval 2017 e informações relacionadas podem ser encontradas em http://www.inf.pucrs.br/linatural/wordpress/index.php/recursos-e-ferramentas/corref-pt/
