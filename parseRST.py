import lxml.etree as ET
from pathlib import Path

def extrair_causa_efeito(caminho_arquivo):
    with open(caminho_arquivo, 'rb') as f:
        raw = f.read()
    try:
        texto = raw.decode('utf-8')
    except UnicodeDecodeError:
        texto = raw.decode('iso-8859-1', errors='replace')
        
    if texto.startswith('<?xml'):
        texto = texto[texto.find('?>') + 2:]
        
    root = ET.fromstring(texto.strip().encode('utf-8'))
    
    # Mapeamento de segmentos
    segmentos = {}
    ordem_segmentos = {}
    for index, s in enumerate(root.xpath('//segment')):
        if s.text:
            s_id = s.get('id')
            segmentos[s_id] = s.text.strip()
            ordem_segmentos[s_id] = index
    
    pai_para_filhos = {}
    for el in root.xpath('//*[@parent]'):
        pai_para_filhos.setdefault(el.get('parent'), []).append(el.get('id'))
        
    # Busca de ids relacionados
    cache_ids = {}
    def get_ids(node_id):
        if node_id in cache_ids:
            return cache_ids[node_id]
        
        ids = set([node_id]) if node_id in segmentos else set()
        for filho in pai_para_filhos.get(node_id, []):
            ids.update(get_ids(filho))
            
        cache_ids[node_id] = ids
        return ids

    relacoes_alvo = {'cause', 'result', 'volitional-cause', 'non-volitional-cause', 
                     'volitional-result', 'non-volitional-result'}
    
    pares = []
    
    # Processamento das relações obtidas
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
            
        # Ordenação dos segmentos
        texto_filho = " ".join(segmentos[i] for i in sorted(ids_filho, key=lambda x: ordem_segmentos[x]))
        texto_pai = " ".join(segmentos[i] for i in sorted(ids_pai, key=lambda x: ordem_segmentos[x]))
        
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
