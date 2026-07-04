import re
import xml.etree.ElementTree as ET
from collections import defaultdict, Counter
from pathlib import Path

class Bootstrapping:
    def __init__(self, sementes, diretorio_corpus):
        """
        Inicializa o sistema consumindo os arquivos .rs3 tanto para sementes como para o corpus.
        """
        self.pares = set()
        for par in sementes:
            if "causa" in par and "efeito" in par:
                self.pares.add((par["causa"].strip(), par["efeito"].strip()))
        
        # Carrega o corpus estruturado por documentos e seus segmentos nativos
        self.documentos = self._carregar_corpus_rs3(diretorio_corpus)
        self.padroes = Counter()
        self.indice = self._criar_indice_invertido()

    def _carregar_corpus_rs3(self, diretorio):
        """Varre o diretório do corpus e extrai o texto completo e os segmentos de cada arquivo."""
        docs = []
        caminho_base = Path(diretorio)
        for arq in caminho_base.rglob('*.rs3'):
            try:
                tree = ET.parse(arq)
                root = tree.getroot()
                segmentos = [seg.text.strip() for seg in root.findall('.//segment') if seg.text]
                if segmentos:
                    # Guarda o texto completo para busca listagem de segmentos
                    texto_completo = " ".join(segmentos)
                    docs.append({"texto": texto_completo, "segmentos": segmentos})
            except Exception:
                continue
        return docs

    def _criar_indice_invertido(self):
        indice = defaultdict(set)
        for idx, doc in enumerate(self.documentos):
            palavras = set(re.findall(r'\b\w{4,}\b', doc["texto"].lower()))
            for palavra in palavras:
                indice[palavra].add(idx)
        return indice

    def _obter_docs_relevantes(self, causa, efeito):
        p_causa = re.findall(r'\b\w{4,}\b', causa.lower())
        p_efeito = re.findall(r'\b\w{4,}\b', efeito.lower())
        if not p_causa or not p_efeito:
            return []
        
        ids = self.indice.get(max(p_causa, key=len), set()) & self.indice.get(max(p_efeito, key=len), set())
        return [self.documentos[i] for i in ids]

    def encontrar_padroes(self):
        novos_padroes = Counter()
        for causa, efeito in self.pares:
            docs_alvo = self._obter_docs_relevantes(causa, efeito)
            regex = re.compile(rf"{re.escape(causa)}(.*?){re.escape(efeito)}", re.IGNORECASE | re.DOTALL)
            
            for doc in docs_alvo:
                match = regex.search(doc["texto"])
                if match:
                    padrao = match.group(1).strip()
                    if padrao and len(padrao.split()) <= 8:
                        novos_padroes[padrao] += 1
                        
        self.padroes.update(novos_padroes)
        return {p for p, freq in novos_padroes.items() if freq > 0}

    def encontrar_novos_pares(self, padroes_fortes):
        novos_pares = set()
        
        for padrao in padroes_fortes:
            p_padrao = re.findall(r'\b\w{4,}\b', padrao.lower())
            if not p_padrao:
                continue
                
            ids = self.indice.get(max(p_padrao, key=len), set())
            docs_alvo = [self.documentos[i] for i in ids]
            
            regex = re.compile(rf"(.*?){re.escape(padrao)}(.*)", re.IGNORECASE | re.DOTALL)
            
            for doc in docs_alvo:
                match = regex.search(doc["texto"])
                if match:
                    pos_inicio_padrao = match.start(0) + doc["texto"][match.start(0):].index(padrao)
                    pos_fim_padrao = pos_inicio_padrao + len(padrao)
                    
                    nova_causa, novo_efeito = None, None
                    fim_acumulado = 0
                    
                    # Identifica qual segmento exato gerou a relação
                    for seg in doc["segmentos"]:
                        inicio_seg = doc["texto"].find(seg, fim_acumulado)
                        fim_seg = inicio_seg + len(seg)
                        fim_acumulado = fim_seg
                        
                        if inicio_seg <= pos_inicio_padrao and fim_seg <= pos_inicio_padrao + 5:
                            nova_causa = seg
                        if inicio_seg >= pos_fim_padrao - 5 and novo_efeito is None:
                            novo_efeito = seg
                            break
                    
                    if nova_causa and novo_efeito and nova_causa != novo_efeito:
                        novos_pares.add((nova_causa, novo_efeito))
                        
        pares_adicionados = novos_pares - self.pares
        self.pares.update(novos_pares)
        return pares_adicionados

    def executar_ciclos(self, num_ciclos):
        for _ in range(num_ciclos):
            padroes = self.encontrar_padroes()
            if not padroes: break
            novos_pares = self.encontrar_novos_pares(padroes)
            if not novos_pares: break
        return self.pares
