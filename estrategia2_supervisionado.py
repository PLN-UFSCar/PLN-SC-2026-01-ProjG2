# -*- coding: utf-8 -*-
"""
Estratégia 2 — Classificação supervisionada de pares de sentenças.

Enquadra a identificação de causalidade como classificação binária de pares
(A, B): existe relação causal entre os segmentos? Positivos vêm das relações
causais do RST (cause/result); negativos, de outras relações (elaboration,
contrast, list, sequence...).

Codificação (duas opções, selecionadas automaticamente conforme disponibilidade):
  1) BERTimbau / Sentence-Transformer  (neuralmind/bert-base-portuguese-cased
     via sentence-transformers, ou multilingual-e5-base) -> embeddings densos.
  2) Fallback TF-IDF (n-gramas de caractere+palavra) quando não há acesso ao
     modelo pré-treinado. Mantém o pipeline reprodutível offline.

Classificador: Regressão Logística sobre a concatenação
     [emb(A) ; emb(B) ; |emb(A)-emb(B)| ; emb(A)*emb(B)]
Avaliação: validação cruzada estratificada (StratifiedKFold), dado o volume
modesto do corpus.

Uso:
    python estrategia2_supervisionado.py
"""

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.metrics import precision_score, recall_score, f1_score, accuracy_score
from sklearn.pipeline import make_pipeline
from sklearn.feature_extraction.text import TfidfVectorizer


# ---------------------------------------------------------------------------
# Codificadores
# ---------------------------------------------------------------------------

class CodificadorBERTimbau:
    """Embeddings densos via sentence-transformers (BERTimbau ou e5)."""

    NOMES = [
        "neuralmind/bert-base-portuguese-cased",
        "intfloat/multilingual-e5-base",
    ]

    def __init__(self):
        from sentence_transformers import SentenceTransformer
        ultimo_erro = None
        for nome in self.NOMES:
            try:
                self.model = SentenceTransformer(nome)
                self.nome = nome
                return
            except Exception as e:  # pragma: no cover
                ultimo_erro = e
        raise RuntimeError(f"Nenhum modelo ST disponível: {ultimo_erro}")

    def encode(self, textos):
        return np.asarray(self.model.encode(textos, show_progress_bar=False))


class CodificadorTFIDF:
    """Fallback offline: TF-IDF palavra + caractere, reduzido por SVD."""

    def __init__(self, dim=300):
        from sklearn.decomposition import TruncatedSVD
        self.vec = TfidfVectorizer(
            analyzer="word", ngram_range=(1, 2), min_df=2, max_features=20000
        )
        self.svd = TruncatedSVD(n_components=dim, random_state=42)
        self._ajustado = False

    def fit(self, textos):
        X = self.vec.fit_transform(textos)
        n = min(self.svd.n_components, X.shape[1] - 1)
        self.svd.n_components = max(2, n)
        self.svd.fit(X)
        self._ajustado = True
        return self

    def encode(self, textos):
        if not self._ajustado:
            raise RuntimeError("Chame fit() antes de encode() no fallback TF-IDF.")
        return self.svd.transform(self.vec.transform(textos))


def obter_codificador():
    """Tenta BERTimbau; se indisponível (sem download), usa TF-IDF."""
    try:
        cod = CodificadorBERTimbau()
        print(f"[codificador] usando embeddings densos: {cod.nome}")
        return cod, "bertimbau"
    except Exception as e:
        print(f"[codificador] BERTimbau indisponível ({type(e).__name__}); "
              f"usando fallback TF-IDF+SVD.")
        return CodificadorTFIDF(), "tfidf"


# ---------------------------------------------------------------------------
# Construção de features de par
# ---------------------------------------------------------------------------

def features_pares(cod, tipo, pares_A, pares_B):
    """Concatena emb(A), emb(B), |A-B|, A*B."""
    if tipo == "tfidf":
        cod.fit(list(pares_A) + list(pares_B))
    A = cod.encode(list(pares_A))
    B = cod.encode(list(pares_B))
    return np.hstack([A, B, np.abs(A - B), A * B])


# ---------------------------------------------------------------------------
# Treino + avaliação por validação cruzada
# ---------------------------------------------------------------------------

def treinar_avaliar(pares_A, pares_B, y, n_splits=5, seed=42):
    y = np.asarray(y)
    cod, tipo = obter_codificador()
    X = features_pares(cod, tipo, pares_A, pares_B)

    clf = LogisticRegression(max_iter=2000, class_weight="balanced", C=1.0)
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    y_pred = cross_val_predict(clf, X, y, cv=skf)

    metricas = {
        "codificador": tipo,
        "n_exemplos": int(len(y)),
        "n_positivos": int(y.sum()),
        "precisao": float(precision_score(y, y_pred, zero_division=0)),
        "recall": float(recall_score(y, y_pred, zero_division=0)),
        "f1": float(f1_score(y, y_pred, zero_division=0)),
        "acuracia": float(accuracy_score(y, y_pred)),
    }
    return metricas


if __name__ == "__main__":
    from avaliacao import avaliar_estrategia2
    avaliar_estrategia2(diretorio="DatasetCSTNews")
