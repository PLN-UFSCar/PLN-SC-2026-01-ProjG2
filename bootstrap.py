class ExtratorBootstrapping:
    def __init__(self, pasta_cstnews="DatasetCSTNews", pasta_bruto="DatasetBrutos", limite_segmentos=5):
        self.caminho_cstnews = pasta_cstnews
        self.caminho_bruto = pasta_bruto
        self.limite_segmentos = limite_segmentos
        
        self.pares_conhecidos = []
        self.padroes_conhecidos = []
        self.textos_brutos = []
        self.textos_cstnews = []

    def _limpar_texto(self, texto):
        """Normaliza espaços, quebras de linha e tabulações."""
        if not texto: return ""
        return " ".join(texto.split())

    def _tratar_decodificacao_xml(self, caminho_arquivo):
        with open(caminho_arquivo, 'rb') as f:
            raw = f.read()
        try:
            texto = raw.decode('utf-8')
        except UnicodeDecodeError:
            texto = raw.decode('iso-8859-1', errors='replace')
        if texto.startswith('<?xml'):
            texto = texto[texto.find('?>') + 2:]
        return texto.strip().encode('utf-8')

    def extrair_sementes_e_textos_cstnews(self):
        arquivos = list(self.caminho_cstnews.rglob('*.rs3'))
        
        if not arquivos:
            print(f"   Erro: Nenhum arquivo encontrado em {self.caminho_cstnews.name}.")
            return

        for arquivo_rs3 in arquivos:
            try:
                xml_puro = self._tratar_decodificacao_xml(str(arquivo_rs3))
                root = ET.fromstring(xml_puro)
                
                ids_nucleos = set(root.xpath('//*[@relname="span" or @relname="same-unit"]/@id'))
                segmentos = {}
                for index, s in enumerate(root.xpath('//segment')):
                    if s.text:
                        segmentos[s.get('id')] = (self._limpar_texto(s.text), index)

                # Monta e limpa o texto linear
                segmentos_ordenados = sorted(segmentos.values(), key=lambda x: x[1])
                texto_linear_cst = self._limpar_texto(" ".join([seg[0] for seg in segmentos_ordenados]))
                if texto_linear_cst:
                    self.textos_cstnews.append(texto_linear_cst)

                pai_para_filhos = {}
                for el in root.xpath('//*[@parent]'):
                    pai_para_filhos.setdefault(el.get('parent'), []).append(el.get('id'))

                cache_todos = {}
                def get_ids(node_id):
                    if node_id in cache_todos: return cache_todos[node_id]
                    ids = set([node_id]) if node_id in segmentos else set()
                    for filho_id in pai_para_filhos.get(node_id, []): ids.update(get_ids(filho_id))
                    cache_todos[node_id] = ids
                    return ids

                cache_significativos = {}
                def get_ids_significativos(node_id):
                    if node_id in cache_significativos: return cache_significativos[node_id]
                    ids = set([node_id]) if node_id in segmentos else set()
                    filhos = pai_para_filhos.get(node_id, [])
                    for filho_id in filhos:
                        if filho_id in segmentos:
                            if filho_id in ids_nucleos: ids.add(filho_id)
                        else:
                            ids.update(get_ids_significativos(filho_id))
                    if not ids and filhos:
                        primeiro_filho = filhos[0]
                        if primeiro_filho in segmentos: ids.add(primeiro_filho)
                        else: ids.update(get_ids_significativos(primeiro_filho))
                    cache_significativos[node_id] = ids
                    return ids

                relacoes_alvo = {'cause', 'result', 'volitional-cause', 'non-volitional-cause',
                                 'volitional-result', 'non-volitional-result'}

                for elemento in root.xpath('//*[@relname]'):
                    tipo = elemento.get('relname')
                    if tipo not in relacoes_alvo: continue

                    id_filho, id_pai = elemento.get('id'), elemento.get('parent')
                    ids_filho, ids_pai = get_ids(id_filho), get_ids(id_pai)

                    if ids_filho < ids_pai: ids_pai = ids_pai - ids_filho
                    elif ids_pai < ids_filho: ids_filho = ids_filho - ids_pai

                    if not ids_filho or not ids_pai: continue
                    if len(ids_filho) > self.limite_segmentos or len(ids_pai) > self.limite_segmentos: continue

                    ids_filho_sig, ids_pai_sig = get_ids_significativos(id_filho), get_ids_significativos(id_pai)

                    if ids_filho_sig < ids_pai_sig: ids_pai_sig = ids_pai_sig - ids_filho_sig
                    elif ids_pai_sig < ids_filho_sig: ids_filho_sig = ids_filho_sig - ids_pai_sig

                    if not ids_filho_sig or not ids_pai_sig: continue

                    texto_filho = self._limpar_texto(" ".join(segmentos[i][0] for i in sorted(ids_filho_sig, key=lambda x: segmentos[x][1])))
                    texto_pai = self._limpar_texto(" ".join(segmentos[i][0] for i in sorted(ids_pai_sig, key=lambda x: segmentos[x][1])))

                    if 'cause' in tipo:
                        par = {"causa": texto_filho, "efeito": texto_pai, "origem": "CSTNews"}
                    else:
                        par = {"causa": texto_pai, "efeito": texto_filho, "origem": "CSTNews"}
                    
                    if par not in self.pares_conhecidos:
                        self.pares_conhecidos.append(par)
            except Exception:
                continue
                
    def carregar_textos_brutos_alvo(self):
        arquivos = list(self.caminho_bruto.rglob('*.rs3'))
        
        if not arquivos:
            print(f"   Erro: Nenhum arquivo encontrado em {self.caminho_bruto.name}.")
            return

        contagem = 0
        for arquivo_rs3 in arquivos:
            try:
                xml_puro = self._tratar_decodificacao_xml(str(arquivo_rs3))
                root = ET.fromstring(xml_puro)
                
                segmentos = {}
                for index, s in enumerate(root.xpath('//segment')):
                    if s.text:
                        segmentos[s.get('id')] = (self._limpar_texto(s.text), index)
                
                segmentos_ordenados = sorted(segmentos.values(), key=lambda x: x[1])
                texto_completo = self._limpar_texto(" ".join([seg[0] for seg in segmentos_ordenados]))
                
                if texto_completo:
                    self.textos_brutos.append(texto_completo)
                    contagem += 1
            except Exception:
                continue
                
    def extrair_padroes(self, base_de_textos):
        novos = 0
        for texto in base_de_textos:
            for par in self.pares_conhecidos:
                causa = par['causa']
                efeito = par['efeito']
                
                if causa in texto and efeito in texto:
                    inicio_causa = texto.find(causa)
                    fim_causa = inicio_causa + len(causa)
                    
                    inicio_efeito = texto.find(efeito)
                    fim_efeito = inicio_efeito + len(efeito)
                    
                    if fim_causa <= inicio_efeito:
                        padrao = texto[fim_causa:inicio_efeito]
                        ordem = "C-E"
                    elif fim_efeito <= inicio_causa:
                        padrao = texto[fim_efeito:inicio_causa]
                        ordem = "E-C"
                    else:
                        continue
                    
                    padrao = padrao.strip(".,;:()\"'[]{}«»-–— ")
                    
                    if 1 < len(padrao) < 35:
                        novo_padrao = {'texto_ponte': padrao, 'ordem': ordem}
                        if novo_padrao not in self.padroes_conhecidos:
                            self.padroes_conhecidos.append(novo_padrao)
                            novos += 1
        return novos

    def descobrir_novos_pares(self):
        """Varre o corpus alvo quebrando strings."""
        novos = 0
        for texto in self.textos_brutos:
            for padrao in self.padroes_conhecidos:
                ponte = f" {padrao['texto_ponte']} "
                if ponte in texto:
                    partes = texto.split(ponte)
                    if len(partes) >= 2:
                        parte_antes = partes[0].split(". ")[-1]
                        parte_depois = partes[1].split(". ")[0]
                        
                        parte_antes = self._limpar_texto(parte_antes)
                        parte_depois = self._limpar_texto(parte_depois)
                        
                        if len(parte_antes) > 10 and len(parte_depois) > 10:
                            if padrao['ordem'] == "C-E":
                                nova_causa, novo_efeito = parte_antes, parte_depois
                            else:
                                nova_causa, novo_efeito = parte_depois, parte_antes
                                
                            novo_par = {
                                'causa': nova_causa.strip("., "), 
                                'efeito': novo_efeito.strip("., "), 
                                'origem': 'Bootstrapping'
                            }
                            if novo_par not in self.pares_conhecidos:
                                self.pares_conhecidos.append(novo_par)
                                novos += 1
        return novos

    def visualizar_resultados(self, tamanho_amostra=5):
        print("\n" + "="*75)
        print("RELATÓRIO DO PIPELINE")
        print("="*75)
        
        print(f"\n PADRÕES TEXTUAIS APRENDIDOS ({len(self.padroes_conhecidos)} no total):")
        if self.padroes_conhecidos:
            df_padroes = pd.DataFrame(self.padroes_conhecidos)
            print(df_padroes.head(15).to_markdown(index=False))
        else:
            print("Nenhum padrão detectado.")

        print(f"\n AMOSTRA DE CONHECIMENTO (Total de Pares: {len(self.pares_conhecidos)}):")
        if self.pares_conhecidos:
            df_pares = pd.DataFrame(self.pares_conhecidos)
            
            print("\n-> Exemplos vindos do CSTNews:")
            cst_df = df_pares[df_pares['origem'] == 'CSTNews']
            if not cst_df.empty:
                print(cst_df.sample(n=min(tamanho_amostra, len(cst_df))).to_markdown(index=False))
                
            print("\n-> Novos pares pescados no seu Corpus Alvo:")
            boot_df = df_pares[df_pares['origem'] == 'Bootstrapping']
            if not boot_df.empty:
                print(boot_df.sample(n=min(tamanho_amostra, len(boot_df))).to_markdown(index=False))
            else:
                print("Nenhum par novo. Tente aumentar o número de iterações.")
        print("="*75)

    def executar(self, iteracoes=3):
        self.extrair_sementes_e_textos_cstnews()
        self.carregar_textos_brutos_alvo()
        
        if not self.pares_conhecidos or not self.textos_brutos:
            print("\nErro: Alimente as pastas com os arquivos antes de rodar.")
            return

        # Iteração 1: Foca no CSTNews para aprender as pontes textuais legítimas
        n_padroes = self.extrair_padroes(self.textos_cstnews)
        # print(f"   -> Aprendidos {n_padroes} padrões iniciais baseados nas sementes estruturais.")
        
        n_pares = self.descobrir_novos_pares()
        # print(f"   -> Encontrados {n_pares} novos pares no corpus alvo.")
        
        # Iterações seguintes: expande o conhecimento usando os textos brutos
        for i in range(1, iteracoes):
            self.extrair_padroes(self.textos_brutos)
            self.descobrir_novos_pares()
            # print(f"   >> Status: {len(self.padroes_conhecidos)} padrões totais | {len(self.pares_conhecidos)} pares totais.")

        self.visualizar_resultados()

# Execução
extrator = ExtratorBootstrapping()
extrator.executar(iteracoes=3)
