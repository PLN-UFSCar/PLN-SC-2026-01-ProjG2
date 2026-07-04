import lxml.etree as ET
from pathlib import Path

def extrair_causa_efeito(caminho_arquivo, limite_segmentos=5):
    with open(caminho_arquivo, 'rb') as f:
        raw = f.read()
    try:
        texto = raw.decode('utf-8')
    except UnicodeDecodeError:
        texto = raw.decode('iso-8859-1', errors='replace')

    if texto.startswith('<?xml'):
        texto = texto[texto.find('?>') + 2:]

    root = ET.fromstring(texto.strip().encode('utf-8'))
    ids_nucleos = set(root.xpath('//*[@relname="span" or @relname="same-unit"]/@id'))

    # Mapeamento dos segmentos
    segmentos = {}
    for index, s in enumerate(root.xpath('//segment')):
        if s.text:
            segmentos[s.get('id')] = (s.text.strip(), index)

    pai_para_filhos = {}
    for el in root.xpath('//*[@parent]'):
        pai_para_filhos.setdefault(el.get('parent'), []).append(el.get('id'))

    # Coleta os IDs relacionados
    cache_todos = {}
    def get_ids(node_id):
        if node_id in cache_todos:
            return cache_todos[node_id]
            
        ids = set([node_id]) if node_id in segmentos else set()
        for filho_id in pai_para_filhos.get(node_id, []):
            ids.update(get_ids(filho_id))
            
        cache_todos[node_id] = ids
        return ids

    # Coleta os segmentos significativos
    cache_significativos = {}
    def get_ids_significativos(node_id):
        if node_id in cache_significativos:
            return cache_significativos[node_id]

        ids = set([node_id]) if node_id in segmentos else set()
        filhos = pai_para_filhos.get(node_id, [])
        for filho_id in filhos:
            if filho_id in segmentos:
                if filho_id in ids_nucleos:
                    ids.add(filho_id)
            else:
                ids.update(get_ids_significativos(filho_id))

        if not ids and filhos:
            primeiro_filho = filhos[0]
            if primeiro_filho in segmentos:
                ids.add(primeiro_filho)
            else:
                ids.update(get_ids_significativos(primeiro_filho))

        cache_significativos[node_id] = ids
        return ids

    relacoes_alvo = {'cause', 'result', 'volitional-cause', 'non-volitional-cause',
                     'volitional-result', 'non-volitional-result'}

    pares = []

    # Processamento de relações
    for elemento in root.xpath('//*[@relname]'):
        tipo = elemento.get('relname')
        if tipo not in relacoes_alvo:
            continue

        id_filho, id_pai = elemento.get('id'), elemento.get('parent')
        
        ids_filho = get_ids(id_filho)
        ids_pai = get_ids(id_pai)

        if ids_filho < ids_pai:
            ids_pai = ids_pai - ids_filho
        elif ids_pai < ids_filho:
            ids_filho = ids_filho - ids_pai

        if not ids_filho or not ids_pai:
            continue

        if len(ids_filho) > limite_segmentos or len(ids_pai) > limite_segmentos:
            continue

        ids_filho_sig = get_ids_significativos(id_filho)
        ids_pai_sig = get_ids_significativos(id_pai)

        if ids_filho_sig < ids_pai_sig:
            ids_pai_sig = ids_pai_sig - ids_filho_sig
        elif ids_pai_sig < ids_filho_sig:
            ids_filho_sig = ids_filho_sig - ids_pai_sig

        if not ids_filho_sig or not ids_pai_sig:
            continue

        texto_filho = " ".join(segmentos[i][0] for i in sorted(ids_filho_sig, key=lambda x: segmentos[x][1]))
        texto_pai = " ".join(segmentos[i][0] for i in sorted(ids_pai_sig, key=lambda x: segmentos[x][1]))

        if 'cause' in tipo:
            pares.append({"causa": texto_filho, "efeito": texto_pai, "tipo": tipo})
        else:
            pares.append({"causa": texto_pai, "efeito": texto_filho, "tipo": tipo})

    return pares

def CSTNews_causa_efeito(diretorio_base="Dataset"):
    """
    Gerador que varre o dataset e entrega par a par
    """
    caminho_base = Path(diretorio_base)
    for arquivo_rs3 in caminho_base.rglob('*.rs3'):
        try:
            pares = extrair_causa_efeito(str(arquivo_rs3))
            for par in pares:
                # Adiciona metadados do arquivo de origem
                par["fonte"] = str(arquivo_rs3.relative_to(caminho_base))
                yield par
        except Exception:
            continue
