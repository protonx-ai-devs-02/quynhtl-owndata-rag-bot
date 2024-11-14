from flask import Flask, request, jsonify
from flask_cors import CORS
from openai_client import OpenAIClient
from rag.core_test import RAG
from semantic_router import SemanticRouter, Route
from semantic_router.samples import productSample, chitchatSample
from reflection.core import Reflection
from embedding_model.core import EmbeddingModel
import os
from dotenv import load_dotenv
load_dotenv()

# Load environment variables
api_key=os.getenv('OPENAI_API_KEY')
db_chat_history_collection=os.getenv('DB_CHAT_HISTORY_COLLECTION')
collection_name=os.getenv('COLLECTION_NAME')
semanticCacheCollection=os.getenv('semanticCacheCollection')
db_path='databaseQQ/VECTOR_STORE'

# Initialize Flask
app = Flask(__name__)
CORS(app)

# Initialize embedding model and OpenAI client
embedding_model = EmbeddingModel()
openai_api_key=os.getenv("OPENAI_API_KEY")
llm = OpenAIClient(openai_api_key)

from chromadb.utils import embedding_functions
import chromadb
client = chromadb.PersistentClient(path=db_path)
sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="keepitreal/vietnamese-sbert")
chroma_collection = client.get_or_create_collection(name=collection_name, embedding_function=sentence_transformer_ef)

rag = RAG(
    collection_name=collection_name,
    db_path=db_path
)

# Setup Semantic Router
PRODUCT_ROUTE_NAME = 'products'
CHITCHAT_ROUTE_NAME = 'chitchat'
productRoute = Route(name=PRODUCT_ROUTE_NAME, samples=productSample)
chitchatRoute = Route(name=CHITCHAT_ROUTE_NAME, samples=chitchatSample)
semanticRouter = SemanticRouter(routes=[productRoute, chitchatRoute])

# Setup Reflection
reflection = Reflection(
    llm=llm,
    db_path=db_path,
    dbChatHistoryCollection=db_chat_history_collection,
    semanticCacheCollection=semanticCacheCollection
)

@app.route('/api/v1/chewy_chewy', methods=['POST'])
def chat():
    data = request.get_json()
    session_id = data.get('session_id', '')
    query = data.get('query', '')

    # Determine route for query
    guided_route = semanticRouter.guide(query)[1]
    print(f"semantic route: {guided_route}")

    if guided_route == PRODUCT_ROUTE_NAME:
        # Get query embedding
        query_embedding = embedding_model.get_embedding(query)

        # Query product information via RAG if no cache hit
        source_information = rag.enhance_prompt(query, query_embedding).replace('<br>', '\n')
        combined_information = f"Câu hỏi : {query}, \ntrả lời khách hàng sử dụng thông tin sản phẩm sau:\n###Sản Phẩm###\n{source_information}."
        response = reflection.chat(
            session_id=session_id,
            enhanced_message=combined_information,
            original_message=query,
            cache_response=True,
            query_embedding=query_embedding
        )
    else:
        # If chitchat, directly call LLM without RAG
        response = reflection.chat(
            session_id=session_id,
            enhanced_message=query,
            original_message=query,
            cache_response=False
        )

    return jsonify({
        "role": "assistant",
        "content": response,
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port='5001', debug=True)
