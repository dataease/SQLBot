# Author: Junjun
# Date: 2025/9/23
import math

import numpy as np


def cosine_similarity(vec_a, vec_b):
    if len(vec_a) != len(vec_b):
        raise ValueError("The vector dimension must be the same")

    a = np.asarray(vec_a, dtype=np.float64)
    b = np.asarray(vec_b, dtype=np.float64)

    dot_product = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return float(dot_product / (norm_a * norm_b))


def batch_cosine_similarity(query_vec, table_vecs):
    """批量计算一个 query 向量与多个 table 向量的余弦相似度。

    Args:
        query_vec: query embedding (list or array)
        table_vecs: 二维数组，每行是一个 table embedding

    Returns:
        一维 numpy array，每个元素是对应 table 与 query 的余弦相似度
    """
    q = np.asarray(query_vec, dtype=np.float64)
    mat = np.asarray(table_vecs, dtype=np.float64)

    q_norm = np.linalg.norm(q)
    if q_norm == 0:
        return np.zeros(len(table_vecs))

    # 按行计算范数，避免除零
    norms = np.linalg.norm(mat, axis=1)
    norms[norms == 0] = 1.0  # 零向量相似度为 0，除以 1 保持结果为 0

    return mat @ q / (norms * q_norm)
