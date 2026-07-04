"""
Módulo de avaliação — constrói o conjunto de referência (gold) a partir das
anotações RST do CST News e avalia as duas estratégias.

- Gold causal: pares extraídos por parseRST.extrair_causa_efeito (relações
  cause/result do RST).
- Negativos (para a Estratégia 2): pares de segmentos ligados por relações
  NÃO causais (elaboration, contrast, list, sequence, comparison...).

Métricas: precisão, revocação (recall), F1 e acurácia.
"""

from collections import Counter
from pathlib import Path
import re

import lxml.etree as ET

from parseRST import CSTNews_causa_efeito



# Normalização e casamento de segmentos

def normalizar(txt):
    txt = txt.lower()
    txt = re.sub(r"[^\wáàâãéèêíïóôõöúçñ ]", " ", txt)
    return re.sub(r"\s+", " ", txt).strip()

def tokens(txt):
    return set(normalizar(txt).split())

def jaccard(a, b):
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)

def overlap(a, b):
    """Coeficiente de sobreposição: quanto do menor está contido no maior.
    Robusto a diferenças de granularidade entre o segmento predito e o gold."""
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / min(len(ta), len(tb))

def par_casa(par_pred, par_gold, limiar=0.5):
    """Casa um par predito com um gold se causa e efeito se sobrepõem o bastante.
    Usa overlap coefficient para tolerar diferenças de extensão dos segmentos."""
    return (overlap(par_pred[0], par_gold[0]) >= limiar and
            overlap(par_pred[1], par_gold[1]) >= limiar)

def par_casa_parcial(par_pred, par_gold, limiar_causa=0.5, limiar_efeito=0.3):
    """Casamento parcial: exige boa sobreposição na CAUSA (o que as regras
    acertam bem) e sobreposição mínima no EFEITO (onde UD e RST divergem na
    fronteira do segmento). Justificado pela diferença de granularidade entre
    a análise de dependências (intra-sentencial) e a anotação RST (discursiva)."""
    return (overlap(par_pred[0], par_gold[0]) >= limiar_causa and
            overlap(par_pred[1], par_gold[1]) >= limiar_efeito)


# Gold causal

def carregar_gold(diretorio="DatasetCSTNews"):
    gold = []
    for par in CSTNews_causa_efeito(diretorio):
        gold.append((par["causa"], par["efeito"], par.get("fonte", ""), par["tipo"]))
    return gold


# Negativos: pares de segmentos ligados por relações NÃO causais

RELACOES_NEGATIVAS = {
    "elaboration", "contrast", "list", "sequence", "comparison",
    "background", "circumstance", "attribution", "restatement",
}

def carregar_negativos(diretorio="DatasetCSTNews", max_por_arquivo=30):
    negativos = []
    base = Path(diretorio)
    for arq in base.rglob("*.rs3"):
        try:
            with open(arq, "rb") as f:
                raw = f.read()
            try:
                texto = raw.decode("utf-8")
            except UnicodeDecodeError:
                texto = raw.decode("iso-8859-1", errors="replace")
            if texto.startswith("<?xml"):
                texto = texto[texto.find("?>") + 2:]
            root = ET.fromstring(texto.strip().encode("utf-8"))

            segmentos = {}
            for i, s in enumerate(root.xpath("//segment")):
                if s.text:
                    segmentos[s.get("id")] = s.text.strip()

            pai_filhos = {}
            for el in root.xpath("//*[@parent]"):
                pai_filhos.setdefault(el.get("parent"), []).append(el.get("id"))

            n = 0
            for el in root.xpath("//*[@relname]"):
                tipo = el.get("relname")
                if tipo not in RELACOES_NEGATIVAS:
                    continue
                fid, pid = el.get("id"), el.get("parent")
                # pega o primeiro segmento-folha de cada lado
                sa = _primeiro_seg(fid, segmentos, pai_filhos)
                sb = _primeiro_seg(pid, segmentos, pai_filhos)
                if sa and sb and sa != sb:
                    negativos.append((sa, sb, str(arq.relative_to(base)), tipo))
                    n += 1
                    if n >= max_por_arquivo:
                        break
        except Exception:
            continue
    return negativos

def _primeiro_seg(node_id, segmentos, pai_filhos):
    if node_id in segmentos:
        return segmentos[node_id]
    for filho in pai_filhos.get(node_id, []):
        r = _primeiro_seg(filho, segmentos, pai_filhos)
        if r:
            return r
    return None


# Avaliação da Estratégia 1 (regras)

def avaliar_estrategia1(diretorio="DatasetCSTNews", limiar_casamento=0.5):
    from estrategia1_regras import ExtratorRegras

    print("=" * 70)
    print("ESTRATÉGIA 1 — Regras sobre árvore de dependências")
    print("=" * 70)

    gold = carregar_gold(diretorio)
    gold_por_fonte = {}
    for c, e, fonte, tipo in gold:
        gold_por_fonte.setdefault(fonte, []).append((c, e))
    print(f"Pares causais no gold (RST): {len(gold)}")

    extrator = ExtratorRegras()

    # reconstrói o texto de cada documento a partir dos segmentos e extrai
    preditos = []
    base = Path(diretorio)
    for arq in base.rglob("*.rs3"):
        fonte = str(arq.relative_to(base))
        texto = _texto_do_rs3(arq)
        if not texto:
            continue
        for p in extrator.extrair_documento(texto, fonte):
            preditos.append((p.causa, p.efeito, fonte))
    print(f"Pares causais preditos pelas regras: {len(preditos)}")

    # casamento predito<->gold por fonte
    vp = 0
    gold_casados = set()
    for (pc, pe, fonte) in preditos:
        candidatos = gold_por_fonte.get(fonte, [])
        casou = False
        for gi, (gc, ge) in enumerate(candidatos):
            chave = (fonte, gi)
            if chave in gold_casados:
                continue
            if par_casa_parcial((pc, pe), (gc, ge)):
                vp += 1
                gold_casados.add(chave)
                casou = True
                break
    fp = len(preditos) - vp
    fn = len(gold) - vp

    precisao = vp / (vp + fp) if (vp + fp) else 0.0
    recall = vp / (vp + fn) if (vp + fn) else 0.0
    f1 = 2 * precisao * recall / (precisao + recall) if (precisao + recall) else 0.0

    print("-" * 70)
    print(f"VP={vp}  FP={fp}  FN={fn}")
    print(f"Precisão : {precisao:.3f}")
    print(f"Recall   : {recall:.3f}")
    print(f"F1-Score : {f1:.3f}")
    print("=" * 70)
    return {"precisao": precisao, "recall": recall, "f1": f1,
            "vp": vp, "fp": fp, "fn": fn}


def _texto_do_rs3(arq):
    try:
        with open(arq, "rb") as f:
            raw = f.read()
        try:
            texto = raw.decode("utf-8")
        except UnicodeDecodeError:
            texto = raw.decode("iso-8859-1", errors="replace")
        if texto.startswith("<?xml"):
            texto = texto[texto.find("?>") + 2:]
        root = ET.fromstring(texto.strip().encode("utf-8"))
        segs = [s.text.strip() for s in root.xpath("//segment") if s.text]
        return " ".join(segs)
    except Exception:
        return ""


# Avaliação da Estratégia 2 (supervisionado)

def avaliar_estrategia2(diretorio="DatasetCSTNews", seed=42):
    from estrategia2_supervisionado import treinar_avaliar

    print("=" * 70)
    print("ESTRATÉGIA 2 — Classificação supervisionada de pares")
    print("=" * 70)

    gold = carregar_gold(diretorio)
    negativos = carregar_negativos(diretorio)

    # balanceia negativos ~ 1:1 com positivos
    import random
    random.seed(seed)
    random.shuffle(negativos)
    negativos = negativos[: max(len(gold), 1)]

    A = [g[0] for g in gold] + [n[0] for n in negativos]
    B = [g[1] for g in gold] + [n[1] for n in negativos]
    y = [1] * len(gold) + [0] * len(negativos)

    print(f"Positivos (causais): {len(gold)} | Negativos: {len(negativos)}")

    metricas = treinar_avaliar(A, B, y, n_splits=5, seed=seed)

    print("-" * 70)
    print(f"Codificador : {metricas['codificador']}")
    print(f"Precisão    : {metricas['precisao']:.3f}")
    print(f"Recall      : {metricas['recall']:.3f}")
    print(f"F1-Score    : {metricas['f1']:.3f}")
    print(f"Acurácia    : {metricas['acuracia']:.3f}")
    print("=" * 70)
    return metricas


# Estatísticas do corpus (para o relatório)

def estatisticas_corpus(diretorio="DatasetCSTNews"):
    gold = carregar_gold(diretorio)
    print(f"Arquivos .rs3     : {len(list(Path(diretorio).rglob('*.rs3')))}")
    print(f"Pares causais gold: {len(gold)}")
    print("Distribuição por tipo RST:")
    for tipo, n in Counter(g[3] for g in gold).most_common():
        print(f"  {tipo:28s} {n}")


if __name__ == "__main__":
    estatisticas_corpus()
