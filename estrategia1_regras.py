# -*- coding: utf-8 -*-
"""
Estratégia 1 — Extração de relações causais por regras sobre a árvore de dependências.

Abordagem baseada em regras linguísticas (Universal Dependencies) aplicadas com o
spaCy (modelo pt_core_news_lg). Não depende de dados rotulados para treinar: as regras
codificam construções causais típicas do português (marcadores explícitos, verbos
causativos e conectivos subordinativos).
"""

import re
from dataclasses import dataclass

try:
    import spacy
except ImportError:  # pragma: no cover
    spacy = None


# ---------------------------------------------------------------------------
# Léxico de marcadores causais em português
# ---------------------------------------------------------------------------

# Conectivos/preposições que introduzem a CAUSA (o filho aponta para a causa).
MARCADORES_CAUSA = {
    "porque", "porquanto", "pois", "já que", "uma vez que", "visto que",
    "devido a", "devido à", "devido ao", "graças a", "graças à",
    "por causa de", "em razão de", "em virtude de", "em decorrência de",
    "em consequência de", "por conta de", "dado que", "posto que",
    "como resultado de",
}

# Conectivos que introduzem o EFEITO/RESULTADO.
MARCADORES_EFEITO = {
    "portanto", "logo", "consequentemente", "por isso", "por conseguinte",
    "assim", "de modo que", "de forma que", "resultando em", "acarretando",
    "provocando", "gerando", "causando", "levando a",
}

# Verbos causativos: sujeito = causa, objeto = efeito.
VERBOS_CAUSATIVOS = {
    "causar", "provocar", "gerar", "acarretar", "ocasionar", "produzir",
    "desencadear", "resultar", "originar", "motivar", "levar",
    "contribuir", "deflagrar", "suscitar", "implicar",
}


@dataclass
class ParCausal:
    causa: str
    efeito: str
    marcador: str
    regra: str
    fonte: str = ""

    def as_dict(self):
        return {
            "causa": self.causa, "efeito": self.efeito,
            "marcador": self.marcador, "regra": self.regra, "fonte": self.fonte,
        }


class ExtratorRegras:
    """Aplica regras de dependência para extrair pares (causa, efeito)."""

    def __init__(self, modelo="pt_core_news_lg"):
        if spacy is None:
            raise RuntimeError(
                "spaCy não instalado. Rode: pip install spacy && "
                "python -m spacy download pt_core_news_lg"
            )
        try:
            self.nlp = spacy.load(modelo)
        except OSError as e:  # pragma: no cover
            raise RuntimeError(
                f"Modelo '{modelo}' não encontrado. "
                f"Rode: python -m spacy download {modelo}"
            ) from e

    # -- utilidades -------------------------------------------------------

    @staticmethod
    def _subarvore_texto(token):
        """Texto da subárvore de um token, em ordem de superfície."""
        toks = sorted(token.subtree, key=lambda t: t.i)
        return " ".join(t.text for t in toks).strip(" ,.;:")

    @staticmethod
    def _clausula_do_verbo(verbo):
        """Reconstrói a cláusula governada por um verbo (subárvore do verbo)."""
        toks = sorted(verbo.subtree, key=lambda t: t.i)
        return " ".join(t.text for t in toks).strip(" ,.;:")

    # -- regras -----------------------------------------------------------

    def _regra_marcador_causal(self, doc):
        """
        R1: marcador causal explícito (mark/case) ligando duas cláusulas.
        Ex.: 'Houve enchentes PORQUE choveu muito.'
             causa = cláusula do marcador ; efeito = cláusula matriz.
        """
        pares = []
        for tok in doc:
            lemma_seq = tok.text.lower()
            if tok.dep_ in ("mark", "case") and lemma_seq in _marcadores_uni(MARCADORES_CAUSA):
                verbo_sub = tok.head  # verbo/nome da cláusula subordinada (causa)
                # sobe até a raiz da cláusula matriz (efeito)
                matriz = verbo_sub.head if verbo_sub.head != verbo_sub else None
                if matriz is None or matriz == verbo_sub:
                    continue
                causa = self._subarvore_texto(verbo_sub)
                efeito = self._clausula_matriz(matriz, excluir=verbo_sub)
                # remove o marcador do inicio da causa (ex.: "porque ...")
                if causa.lower().startswith(lemma_seq + " "):
                    causa = causa[len(lemma_seq):].strip(" ,.;:")
                if causa and efeito and causa != efeito:
                    pares.append(ParCausal(causa, efeito, lemma_seq, "R1_marcador_causa"))
        return pares

    def _regra_locucao_causal(self, doc):
        """
        R2: locuções prepositivas multi-palavra ('devido a', 'em razão de'...).
        Detectadas por varredura de superfície + vínculo sintático do objeto.
        """
        pares = []
        texto = doc.text.lower()
        for loc in sorted(_multi(MARCADORES_CAUSA), key=len, reverse=True):
            for m in re.finditer(r"\b" + re.escape(loc) + r"\b", texto):
                # token cujo início casa logo após a locução
                tok0 = _token_apos(doc, m.end())
                if tok0 is None:
                    continue
                # se for artigo/determinante/preposição, sobe ao núcleo nominal
                nucleo = tok0
                if tok0.pos_ in ("DET", "ADP") or tok0.dep_ in ("det", "case"):
                    nucleo = tok0.head
                if nucleo is None:
                    continue
                # sobe ao verbo/predicado que rege a causa -> efeito é a matriz
                verbo = _verbo_governante(nucleo)
                if verbo is None:
                    continue
                causa = self._subarvore_texto(nucleo)
                efeito = self._clausula_matriz(verbo, excluir=nucleo)
                if causa and efeito and causa != efeito:
                    pares.append(ParCausal(causa, efeito, loc, "R2_locucao_causal"))
        return pares

    def _regra_verbo_causativo(self, doc):
        """
        R3: verbo causativo com sujeito (nsubj) e objeto (obj/xcomp).
        Ex.: 'As chuvas CAUSARAM enchentes.'  sujeito->causa, objeto->efeito.
        """
        pares = []
        for tok in doc:
            if tok.pos_ in ("VERB", "AUX") and tok.lemma_.lower() in VERBOS_CAUSATIVOS:
                subj = [c for c in tok.children if c.dep_ in ("nsubj", "nsubj:pass")]
                obj = [c for c in tok.children if c.dep_ in ("obj", "obl", "xcomp", "ccomp")]
                if subj and obj:
                    s0 = subj[0]
                    # se o sujeito for pronome relativo (que/qual), sobe ao antecedente
                    if s0.text.lower() in ("que", "qual", "quais", "quem") or s0.dep_ == "nsubj" and s0.pos_ == "PRON":
                        if tok.head is not None and tok.head != tok and tok.head.pos_ in ("NOUN", "PROPN"):
                            s0 = tok.head
                    causa = self._subarvore_texto(s0)
                    efeito = self._subarvore_texto(obj[0])
                    if causa and efeito and causa != efeito:
                        pares.append(
                            ParCausal(causa, efeito, tok.lemma_.lower(), "R3_verbo_causativo")
                        )
        return pares

    def _clausula_matriz(self, raiz, excluir=None):
        """Texto da cláusula matriz, removendo a subárvore da causa (excluir)."""
        excl = set()
        if excluir is not None:
            excl = {t.i for t in excluir.subtree}
        toks = [t for t in sorted(raiz.subtree, key=lambda t: t.i) if t.i not in excl]
        return " ".join(t.text for t in toks).strip(" ,.;:")

    # -- API --------------------------------------------------------------

    def extrair_sentenca(self, texto, fonte=""):
        doc = self.nlp(texto)
        pares = []
        pares += self._regra_marcador_causal(doc)
        pares += self._regra_locucao_causal(doc)
        pares += self._regra_verbo_causativo(doc)
        # dedup por (causa, efeito)
        vistos, unicos = set(), []
        for p in pares:
            chave = (p.causa.lower(), p.efeito.lower())
            if chave not in vistos:
                vistos.add(chave)
                p.fonte = fonte
                unicos.append(p)
        return unicos

    def extrair_documento(self, texto, fonte=""):
            pares = []
            vistos = set()
            for sent in re.split(r"(?<=[.!?])\s+", texto):
                if sent.strip():
                    for p in self.extrair_sentenca(sent.strip(), fonte):
                        chave = (p.causa.lower().strip(), p.efeito.lower().strip())
                        if chave not in vistos:
                            vistos.add(chave)
                            pares.append(p)
            return pares


# ---------------------------------------------------------------------------
# helpers de superfície (locuções multi-palavra)
# ---------------------------------------------------------------------------

def _multi(conj):
    return {m for m in conj if " " in m}

def _marcadores_uni(conj):
    return {m for m in conj if " " not in m}

def _token_apos(doc, char_idx):
    for tok in doc:
        if tok.idx >= char_idx and not tok.is_space:
            return tok
    return None

def _verbo_governante(token):
    cur = token
    for _ in range(8):
        if cur.head == cur:
            return cur if cur.pos_ in ("VERB", "AUX") else None
        cur = cur.head
        if cur.pos_ in ("VERB", "AUX"):
            return cur
    return None


if __name__ == "__main__":
    import sys
    from avaliacao import avaliar_estrategia1
    avaliar_estrategia1(diretorio="DatasetCSTNews")
