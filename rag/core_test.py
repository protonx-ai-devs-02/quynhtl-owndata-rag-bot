import os
import chromadb
from dotenv import load_dotenv
from chromadb.utils import embedding_functions
load_dotenv()

# Default number of top matches to retrieve from vector search
DEFAULT_SEARCH_LIMIT = int(os.getenv('DEFAULT_SEARCH_LIMIT'))
sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="keepitreal/vietnamese-sbert")


class RAG():
    def __init__(self, collection_name: str, db_path: str):
        # Initialize ChromaDB client and collection
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(name=collection_name, embedding_function=sentence_transformer_ef)


    def weighted_reciprocal_rank(self, doc_lists):
        """
        Perform weighted Reciprocal Rank Fusion on multiple rank lists.
        You can find more details about RRF here:
        https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf

        Args:
            doc_lists: A list of rank lists, where each rank list contains unique items.

        Returns:
            list: The final aggregated list of items sorted by their weighted RRF
                  scores in descending order.
        """
        c = 60  # Parameter from the paper
        weights = [1] * len(doc_lists)  # Weights for each list

        if len(doc_lists) != len(weights):
            raise ValueError("Number of rank lists must equal the number of weights.")

        # Collect all unique documents
        all_documents = {doc["description"] for doc_list in doc_lists for doc in doc_list}
        rrf_score_dic = {doc: 0.0 for doc in all_documents}

        # Calculate RRF scores
        for doc_list, weight in zip(doc_lists, weights):
            for rank, doc in enumerate(doc_list, start=1):
                rrf_score = weight * (1 / (rank + c))
                rrf_score_dic[doc["description"]] += rrf_score

        # Sort documents by RRF scores in descending order
        sorted_documents = sorted(
            rrf_score_dic.keys(), key=lambda x: rrf_score_dic[x], reverse=True
        )

        # Map sorted content back to original documents
        page_content_to_doc_map = {
            doc["description"]: doc for doc_list in doc_lists for doc in doc_list
        }
        return [page_content_to_doc_map[content] for content in sorted_documents]

    def hybrid_search(self, query: str, query_embedding: list, limit=DEFAULT_SEARCH_LIMIT):
        if query_embedding is None:
            return "Invalid query or embedding generation failed."

        # Perform vector search in ChromaDB
        vector_results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=limit
        )
        
        vector_results = [
            {
                "_id": vector_results['ids'][0][i],
                "title": vector_results['metadatas'][0][i].get('title'),
                "description": vector_results['metadatas'][0][i].get('description'),
                "price": vector_results['metadatas'][0][i].get('price'),
                "image_url": vector_results['metadatas'][0][i].get('image_url'),
                "category": vector_results['metadatas'][0][i].get('category'),
                "distance": vector_results['distances'][0][i]
            }
            for i in range(len(vector_results['ids'][0]))
        ]

        # Perform keyword search in ChromaDB
        keyword_results = self.collection.query(
            query_texts=[query],
            n_results=limit
        )

        keyword_results = [
            {
                "_id": keyword_results['ids'][0][i],
                "title": keyword_results['metadatas'][0][i].get('title'),
                "description": keyword_results['metadatas'][0][i].get('description'),
                "price": keyword_results['metadatas'][0][i].get('price'),
                "image_url": keyword_results['metadatas'][0][i].get('image_url'),
                "category": keyword_results['metadatas'][0][i].get('category'),
                "distance": keyword_results['distances'][0][i]
            }
            for i in range(len(keyword_results['ids'][0]))
        ]

        # Merge results and apply rank fusion
        doc_lists = [vector_results, keyword_results]
        fused_documents = self.weighted_reciprocal_rank(doc_lists)
        return fused_documents

    def enhance_prompt(self, query: str, query_embedding: list):
        get_knowledge = self.hybrid_search(query, query_embedding)
        print('hybrid_search_result:', get_knowledge)
        enhanced_prompt = ""
        for result in get_knowledge:
            enhanced_prompt += f"Title: {result.get('title', 'N/A')}, Content: {result.get('description', 'N/A')}, Price: {result.get('price', 'N/A')}, Image URLs: {result.get('image_url', 'N/A')}\n"
        return enhanced_prompt
