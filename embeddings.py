import numpy as np
import time
from typing import List

# @todo @perf This can take 5-10 seconds
print('Importing sentence_transformers...')
start_time = time.time()
from sentence_transformers import SentenceTransformer
end_time = time.time()
print(f'Imported sentence_transformers. Took {end_time - start_time:03} seconds.')


_model = SentenceTransformer('all-MiniLM-L6-v2')


def embed(sentences: List[str]) -> np.ndarray:
    es = _model.encode(sentences)
    for i, e in enumerate(es):
        norm = np.linalg.norm(e)
        es[i] = e / norm
    return es


def cos_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return np.dot(a, b)
