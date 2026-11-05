"""
Snippet: Pure Python Vector Dot Product and Cosine Similarity Search
Difficulty: Intermediate

Interview Context:
Top-tier companies frequently ask you to implement fundamental linear algebra operations from scratch (without NumPy or PyTorch) to test your deep understanding of mathematical primitives, floating-point safety, and algorithmic complexity before introducing hardware acceleration.
"""

import math
from typing import List, Tuple

def dot_product(v1: List[float], v2: List[float]) -> float:
    """
    Computes the dot product of two vectors: A · B = sum(A_i * B_i).
    
    Why: The dot product measures the alignment of two vectors. 
    If they point in the same direction, it's large; if orthogonal, it's zero.
    """
    if len(v1) != len(v2):
        raise ValueError(f"Dimension mismatch: len(v1)={len(v1)} != len(v2)={len(v2)}")
    
    # Using generator expression with sum() is idiomatic Python, 
    # though a traditional loop can sometimes avoid generator overhead.
    return sum(a * b for a, b in zip(v1, v2))

def magnitude(v: List[float]) -> float:
    """
    Computes the L2 norm (magnitude) of a vector: ||A|| = sqrt(sum(A_i^2)).
    """
    # math.fsum is used instead of builtin sum() for better floating-point 
    # precision (it accumulates partial sums to minimize rounding errors).
    return math.sqrt(math.fsum(x * x for x in v))

def cosine_similarity(v1: List[float], v2: List[float], eps: float = 1e-12) -> float:
    """
    Computes the cosine similarity between two vectors.
    Formula: sim(v1, v2) = (v1 · v2) / (||v1|| * ||v2||)
    
    Numerical Safety & Edge Cases:
    1. Zero Vectors: If a vector has a magnitude of 0 (all elements are 0), 
       division by zero will crash the program. We add a small epsilon (eps) 
       to the denominator as a guardrail.
    """
    dot = dot_product(v1, v2)
    mag1 = magnitude(v1)
    mag2 = magnitude(v2)
    
    # Guard against division by zero for zero-vectors
    denominator = mag1 * mag2
    if denominator < eps:
        return 0.0
    
    return dot / denominator

def rank_search_results(
    query: List[float], 
    database: List[Tuple[str, List[float]]], 
    top_k: int = 3
) -> List[Tuple[str, float]]:
    """
    Ranks items in a database against a query vector using pure Python 
    cosine similarity search.
    
    Performance Trade-off:
    This brute-force approach has a time complexity of O(M * D) where M is the 
    number of documents and D is the dimensionality. Without vectorized SIMD 
    instructions or indexing (like HNSW), this does not scale to millions of items 
    and is meant strictly for small-scale systems or pedagogical understanding.
    """
    scores = []
    
    for doc_id, vector in database:
        sim = cosine_similarity(query, vector)
        scores.append((doc_id, sim))
        
    # Sort by similarity score in descending order (highest similarity first)
    scores.sort(key=lambda item: item[1], reverse=True)
    
    # Return the top_k results
    return scores[:top_k]

# --- Example Usage & Verification ---
if __name__ == "__main__":
    # Mock Database: (Document ID, Embedding Vector of dimension 3)
    db = [
        ("doc_python", [1.0, 1.0, 0.0]),
        ("doc_ml", [0.9, 0.8, 0.1]),
        ("doc_cooking", [0.0, 0.1, 1.0]),
        ("doc_empty", [0.0, 0.0, 0.0]) # Edge case test: zero vector
    ]
    
    # Query vector looking for programming/AI concepts
    query_vector = [1.0, 0.9, 0.0]
    
    results = rank_search_results(query_vector, db, top_k=2)
    
    print("Top Search Results:")
    for rank, (doc_id, score) in enumerate(results, 1):
        print(f"{rank}. {doc_id} (Score: {score:.4f})")
        
    # Sanity Checks
    assert results[0][0] == "doc_python", "Expected doc_python to be the closest match."
    
    # Test zero-vector division guard
    zero_sim = cosine_similarity([1.0, 2.0], [0.0, 0.0])
    assert zero_sim == 0.0, "Zero-vector division guard failed."
    
    print("\nImplementation successful: Pure Python similarity metrics verified.")
