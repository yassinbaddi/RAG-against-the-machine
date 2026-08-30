import bm25s



def search_bm25(retriever, query, chunks, k=4):
    query_tokens = bm25s.tokenize(query)

    results, scores = retriever.retrieve(
        query_tokens,
        k=k,
    )

    return [chunks[i] for i in results[0]]