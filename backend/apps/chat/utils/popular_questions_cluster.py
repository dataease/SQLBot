"""
热门问题：按数据源聚合，并在同一数据源内做语义相近合并（非纯字面 group_by）。

1. 意图桶：库表/数据概览类中文问法合并为同一主题（见 META_OVERVIEW_PATTERN）。
2. 向量聚类：对其余问句用本地中文 embedding 做余弦相似度合并（可选，失败则回退）。
3. 回退：归一化 + difflib 合并相近字面。
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any, Dict, List, Tuple

import numpy as np

# 表/数据量/有哪些数据 等「元信息」类问题归为一类（用户示例）
META_OVERVIEW_PATTERN = re.compile(
    r"(几张表|哪些表|多少张表|有多少表|表.*数据量|数据量.*表|分别.*数据量|数据量.*多大|"
    r"哪些数据|有什么数据|有哪些数据|什么数据|库表|schema|多少条数据|统计.*表|表的.*数量)",
    re.IGNORECASE,
)


def normalize_question(s: str) -> str:
    if not s:
        return ""
    t = s.strip()
    t = re.sub(r"[\s\u3000]+", "", t)
    t = re.sub(r"[。．.！？!?；;，、]+$", "", t)
    return t


def _split_meta_overview(
    weighted: List[Tuple[str, int]],
) -> Tuple[List[Tuple[str, int]], List[Tuple[str, int]]]:
    meta: List[Tuple[str, int]] = []
    rest: List[Tuple[str, int]] = []
    for q, c in weighted:
        if META_OVERVIEW_PATTERN.search(q):
            meta.append((q, c))
        else:
            rest.append((q, c))
    out: List[Tuple[str, int]] = []
    if meta:
        rep = max(meta, key=lambda x: x[1])[0]
        total = sum(c for _, c in meta)
        out.append((rep, total))
    return out, rest


def _merge_difflib(weighted: List[Tuple[str, int]], threshold: float = 0.78) -> List[Tuple[str, int]]:
    if not weighted:
        return []
    items = sorted(weighted, key=lambda x: -x[1])
    clusters: List[Dict[str, Any]] = []
    for q, c in items:
        nq = normalize_question(q)
        best_i = -1
        best_r = 0.0
        for i, cl in enumerate(clusters):
            r = SequenceMatcher(None, nq, cl["norm"]).ratio()
            if r >= threshold and r > best_r:
                best_r = r
                best_i = i
        if best_i >= 0:
            clusters[best_i]["count"] += c
            if c > clusters[best_i].get("max_w", 0):
                clusters[best_i]["rep"] = q
                clusters[best_i]["max_w"] = c
        else:
            clusters.append({"rep": q, "count": c, "norm": nq, "max_w": c})
    return [(c["rep"], int(c["count"])) for c in clusters]


def _merge_embedding(weighted: List[Tuple[str, int]], threshold: float = 0.76) -> List[Tuple[str, int]]:
    if len(weighted) <= 1:
        return weighted
    try:
        from apps.ai_model.embedding import EmbeddingModelCache

        texts = [w[0] for w in weighted]
        model = EmbeddingModelCache.get_model()
        embs = model.embed_documents(texts)
        arr = np.array(embs, dtype=np.float32)
        norms = np.linalg.norm(arr, axis=1, keepdims=True) + 1e-9
        arr = arr / norms
        n = len(weighted)
        parent = list(range(n))

        def find(a: int) -> int:
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a

        def union(a: int, b: int) -> None:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[rb] = ra

        sim = arr @ arr.T
        for i in range(n):
            for j in range(i + 1, n):
                if float(sim[i, j]) >= threshold:
                    union(i, j)
        groups: Dict[int, List[int]] = {}
        for i in range(n):
            r = find(i)
            groups.setdefault(r, []).append(i)
        out: List[Tuple[str, int]] = []
        for idxs in groups.values():
            total = sum(weighted[i][1] for i in idxs)
            rep_q = max((weighted[i] for i in idxs), key=lambda x: x[1])[0]
            out.append((rep_q, int(total)))
        return out
    except Exception:
        return _merge_difflib(weighted, threshold=0.78)


def cluster_questions_for_datasource(weighted: List[Tuple[str, int]]) -> List[Tuple[str, int]]:
    """同一数据源下多组 (原文, 次数) -> 合并后 (代表问句, 总次数)。"""
    if not weighted:
        return []
    meta_merged, rest = _split_meta_overview(weighted)
    if not rest:
        return meta_merged
    embedded_or_fb = _merge_embedding(rest)
    return meta_merged + embedded_or_fb
