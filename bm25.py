




import bm25s

corpus = [
    "The quick brown fox jumps over the lazy dog",
    "Artificial intelligence and machine learning are evolving rapidly",
    "Python is an excellent programming language for data science and search",
    "Search engines use BM25 to rank documents by relevance"
]

corpus_tokens = bm25s.tokenize(corpus)

retriever = bm25s.BM25()

retriever.index(corpus_tokens)

query = "Python search programming"
query_tokens = bm25s.tokenize(query)

results, scores = retriever.retrieve(query_tokens, k=2)

for i in range(len(results[0])):
    print(f"Score: {scores[0][i]:.4f} | Document: {results[0][i]}")
