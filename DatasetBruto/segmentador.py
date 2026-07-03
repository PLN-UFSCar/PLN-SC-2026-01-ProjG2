import os
import re
import spacy
import xml.etree.ElementTree as ET
from xml.dom import minidom

try:
    nlp = spacy.load("pt_core_news_sm")
except OSError:
    print("Modelo 'pt_core_news_sm' não encontrado. Instale-o executando: python -m spacy download pt_core_news_sm")
    exit()

def quebrar_em_edus(texto):
    """
    Usa o spaCy para quebrar o texto em sentenças e separa 
    as orações (EDUs) mantendo os conectores no início da nova EDU.
    """
    doc = nlp(texto)
    edus = []
    
    # Conjunções discursivas comuns
    conectores = r"\b(porque|pois|como|mas|porém|contudo|embora|se|caso|para que|afim de que)\b"
    
    for sent in doc.sents:
        sent_texto = sent.text.strip()
        if not sent_texto:
            continue
            
        # Divide mantendo os delimitadores na lista
        partes = re.split(f"(,|;|{conectores})", sent_texto)
        
        buffer_edu = ""
        for parte in partes:
            if not parte:
                continue
                
            # Se encontrar um delimitador e o buffer já tiver texto, fecha a EDU anterior
            if parte.strip() in [",", ";"] or re.match(conectores, parte.strip(), re.IGNORECASE):
                if buffer_edu.strip() and len(buffer_edu.strip()) > 5:
                    edus.append(buffer_edu.strip())
                    buffer_edu = ""
                buffer_edu += parte
            else:
                buffer_edu += parte
                
        if buffer_edu.strip():
            edus.append(buffer_edu.strip())
            
    return edus

def salvar_como_rs3(edus, caminho_saida):
    """Gera a estrutura XML .rs3 para uma lista de EDUs."""
    root = ET.Element("analysis")
    
    header = ET.SubElement(root, "header")
    relations = ET.SubElement(header, "relations")
    ET.SubElement(relations, "rel", name="antithesis", type="rst")
    ET.SubElement(relations, "rel", name="attribution", type="rst")
    ET.SubElement(relations, "rel", name="circumstance", type="rst")
    ET.SubElement(relations, "rel", name="comparison", type="rst")
    ET.SubElement(relations, "rel", name="concession", type="rst")
    ET.SubElement(relations, "rel", name="conclusion", type="rst")
    ET.SubElement(relations, "rel", name="condition", type="rst")
    ET.SubElement(relations, "rel", name="elaboration", type="rst")
    ET.SubElement(relations, "rel", name="enablement", type="rst")
    ET.SubElement(relations, "rel", name="explanation", type="rst")
    ET.SubElement(relations, "rel", name="evaluation", type="rst")
    ET.SubElement(relations, "rel", name="evidence", type="rst")
    ET.SubElement(relations, "rel", name="interpretation", type="rst")
    ET.SubElement(relations, "rel", name="elaboration", type="rst")
    ET.SubElement(relations, "rel", name="non-volitional-cause", type="rst")
    ET.SubElement(relations, "rel", name="non-volitional-result", type="rst")
    ET.SubElement(relations, "rel", name="volitional-cause", type="rst")
    ET.SubElement(relations, "rel", name="volitional-result", type="rst")
    
    # Corpo onde ficam os segmentos
    rst_body = ET.SubElement(root, "rst")
    
    for i, edu_texto in enumerate(edus, start=1):
        segment = ET.SubElement(rst_body, "segment", id=str(i))
        segment.text = edu_texto
        
    # Formatação
    xml_str = ET.tostring(root, encoding="utf-8")
    parsed_xml = minidom.parseString(xml_str)
    xml_formatado = parsed_xml.toprettyxml(indent="  ")
    
    # Remove a declaração <?xml ...?>
    if xml_formatado.startswith("<?xml"):
        xml_formatado = "\n".join(xml_formatado.split("\n")[1:])
        
    with open(caminho_saida, "w", encoding="utf-8") as f:
        f.write(xml_formatado.strip())

def segmentar_lote_arquivos(pasta_origem="textos_limpos", pasta_destino="textos_segmentados"):
    """
    Lê todos os arquivos .txt de uma pasta, segmenta em EDUs e salva como .rs3
    """
    if not os.path.exists(pasta_origem):
        print(f"Erro: A pasta de origem '{pasta_origem}' não existe.")
        return

    if not os.path.exists(pasta_destino):
        os.makedirs(pasta_destino)
        print(f"Pasta de destino '{pasta_destino}' criada com sucesso.")

    # Lista todos os arquivos .txt da pasta
    arquivos = [f for f in os.listdir(pasta_origem) if f.endswith('.txt')]
    
    if not arquivos:
        print(f"Nenhum arquivo .txt encontrado na pasta '{pasta_origem}'.")
        return

    print(f"Encontrados {len(arquivos)} arquivos para segmentar. Processando...")

    for nome_arquivo in arquivos:
        caminho_entrada = os.path.join(pasta_origem, nome_arquivo)
        
        # Define o nome de saída trocando .txt por .rs3
        nome_saida = nome_arquivo.replace(".txt", ".rs3")
        caminho_saida = os.path.join(pasta_destino, nome_saida)
        
        print(f" -> Segmentando: {nome_arquivo}...")
        
        # Abre o arquivo tratando possíveis problemas de encoding
        with open(caminho_entrada, 'r', encoding='utf-8', errors='ignore') as f:
            conteudo = f.read()
            
        # Executa a quebra linguística
        edus_extraidas = quebrar_em_edus(conteudo)
        
        # Salva o arquivo final .rs3
        salvar_como_rs3(edus_extraidas, caminho_saida)

PASTA_BRUTO = "Folha" 
SEG = PASTA_BRUTO + "_segmentado"
segmentar_lote_arquivos(pasta_origem=PASTA_BRUTO, pasta_destino=SEG)
