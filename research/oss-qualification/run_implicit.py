from __future__ import annotations

import os

import numpy as np
from implicit.als import AlternatingLeastSquares
from scipy.sparse import csr_matrix

from common import write_results


def main():
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    matrix = csr_matrix(
        np.array(
            [
                [5, 4, 0, 0, 0, 0],
                [4, 5, 1, 0, 0, 0],
                [0, 1, 5, 4, 0, 0],
                [0, 0, 4, 5, 1, 0],
                [0, 0, 0, 1, 5, 4],
                [0, 0, 0, 0, 4, 5],
            ],
            dtype=np.float32,
        )
    )
    model = AlternatingLeastSquares(factors=4, regularization=0.1, iterations=12, random_state=42)
    model.fit(matrix, show_progress=False)
    item_ids, scores = model.recommend(0, matrix[0], N=3, filter_already_liked_items=True)
    ids = [int(x) for x in item_ids]
    ok = len(ids) == 3 and 0 not in ids and 1 not in ids and all(np.isfinite(scores))
    write_results(
        "implicit",
        [
            {
                "id": "implicit-als",
                "class": "behavioral-recommendation-extension",
                "status": "PASS" if ok else "FAIL",
                "recommended_item_ids": ids,
                "scores": [float(x) for x in scores],
                "kernel_dependency": False,
            }
        ],
    )


if __name__ == "__main__":
    main()
