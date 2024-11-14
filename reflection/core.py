# from rag.mongo_client import MongoClient
import json
import uuid
import chromadb
from chromadb.config import Settings
import os
from dotenv import load_dotenv
from chromadb.utils import embedding_functions
load_dotenv()

OPEN_AI_ROLE_MAPPING = {
    "human": "user",
    "ai": "assistant"
}

sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="keepitreal/vietnamese-sbert")

class Reflection():
    def __init__(self,
        llm,
        db_path: str, 
        dbChatHistoryCollection: str, # chewy_chewy_chat_history
        semanticCacheCollection: str,
    ):
        self.client = chromadb.PersistentClient(path=db_path) 
        self.his_collection = self.client.get_or_create_collection(name=dbChatHistoryCollection,embedding_function=sentence_transformer_ef )
        self.semantic_cache_collection = self.client.get_or_create_collection(name=semanticCacheCollection, embedding_function=sentence_transformer_ef)
        self.llm = llm
        self.dbChatHistoryCollection = dbChatHistoryCollection

    def chat(self, session_id: str, enhanced_message: str, original_message: str = '', cache_response: bool = False, query_embedding: list = []):
        system_prompt_content = """Bạn là một chatbot của cửa hàng tiệm bánh và đồ uống. Vai trò của bạn là hỗ trợ khách hàng trong việc tìm hiểu về các sản phẩm và dịch vụ của cửa hàng, cũng như tạo một trải nghiệm mua sắm dễ chịu và thân thiện. Bạn có thể trả lời các câu hỏi về loại hoa, dịch vụ giao hàng. Bạn cũng có thể trò chuyện với khách hàng về các chủ đề không liên quan đến sản phẩm như thời tiết, sở thích cá nhân, và những câu chuyện thú vị để tạo sự gắn kết. 
Hãy luôn giữ thái độ lịch sự và chuyên nghiệp. Nếu khách hàng hỏi về sản phẩm cụ thể, hãy cung cấp thông tin chi tiết và gợi ý các lựa chọn phù hợp. Nếu khách hàng trò chuyện về các chủ đề không liên quan đến sản phẩm, hãy tham gia vào cuộc trò chuyện một cách vui vẻ và thân thiện.
một số điểm chính bạn cần lưu ý:
1. Đáp ứng nhanh chóng và chính xác, sử dụng xưng hô là "Mình và bạn".
2. Giữ cho cuộc trò chuyện vui vẻ và thân thiện.
3. Cung cấp thông tin hữu ích về tiệm bánh và dịch vụ của cửa hàng.
4. Giữ cho cuộc trò chuyện mang tính chất hỗ trợ và giúp đỡ.
Hãy làm cho khách hàng cảm thấy được chào đón và quan tâm!"""
        system_prompt = [
            {
                "role": "system", 
                "content": system_prompt_content
            },
        ]
        human_prompt = [
            {
                "role": "user", 
                "content": enhanced_message
            },
        ]

        # self.client.delete_collection(self.dbChatHistoryCollection)
        session_messages = self.his_collection.get(where_document={"$contains":session_id})  # Hypothetical method to iterate over all documents
        print("session_messages: ", session_messages)

        formatted_session_messages = self.__construct_session_messages__(session_messages)
        messages = system_prompt + formatted_session_messages + human_prompt
        print(f"final messages: {messages}")
        
        response = self.llm.chat(messages)
        self.__record_human_prompt__(session_id, enhanced_message, original_message)
        self.__record_ai_response__(session_id, response)
        if cache_response:
            self.__cache_ai_response__(enhanced_message, original_message, response, query_embedding)

        return response.choices[0].message.content

    def __construct_session_messages__(self, session_messages: list):
        result = []
        if not session_messages['ids']:
            return result

        for session_message in session_messages['documents']:
            session_message = json.loads(session_message)
            print(f"session_message: {session_message}")
            print(f"session_message: {session_message['History']}")
            result.append({
                "role": OPEN_AI_ROLE_MAPPING[session_message['History']['type']],
                "content": session_message['History']['data']['content']
            })
        return result

    def __record_human_prompt__(self, session_id: str, enhanced_message: str, original_message: str):
        self.his_collection.add(
            ids=[str(uuid.uuid4())],
            documents=[json.dumps({
                "SessionId": session_id,
                "History": {
                    "type": "human",
                    "data":  {
                        "type": "human",
                        "content": original_message,
                        "enhanced_content": enhanced_message,
                        "additional_kwargs": {},
                        "response_metadata": {},
                        "name": None,
                        "id": None,
                        }
                    }
                })],
        )
    
    def __record_ai_response__(self, session_id: str, response: dict):
        self.his_collection.add(
            ids=[str(uuid.uuid4())],
            documents=[json.dumps({
                    "SessionId": session_id,
                    "History": {
                        "type": "ai",
                        "data":  {
                            "type": "ai",
                            "content": response.choices[0].message.content,
                            "enhanced_content": None,
                            "additional_kwargs": {},
                            "name": None,
                            "id": response.id,
                            "usage_metadata": {
                                "input_tokens": response.usage.prompt_tokens,
                                "output_tokens": response.usage.completion_tokens,
                                "total_tokens": response.usage.total_tokens
                            },
                            "response_metadata": {
                                "usage": response.usage.to_json(),
                                "model_name": response.model,
                                "finish_reason": response.choices[0].finish_reason,
                                "logprobs": response.choices[0].logprobs
                            },
                        }
                    }
                })],
        )

    def __cache_ai_response__(self, enhanced_message: str, original_message: str, response: dict, query_embedding: list):
        embedding = query_embedding
        self.semantic_cache_collection.add(
            ids=[str(uuid.uuid4())],
            embeddings = [embedding],
            documents=[json.dumps({
                    "text": [
                        {
                            "type": "human",
                            "content": original_message,
                            "enhanced_content": enhanced_message,
                            "additional_kwargs": {},
                            "response_metadata": {},
                            "name": None,
                            "id": None,
                        }
                    ],
                    "llm_string": {
                        "model_name": response.model,
                        "name": "ChatOpenAI"
                    },
                    "return_val": [
                        {
                            "type": "ai",
                            "content": response.choices[0].message.content,
                            "enhanced_content": None,
                            "additional_kwargs": {},
                            "name": None,
                            "id": response.id,
                            "usage_metadata": {
                                "input_tokens": response.usage.prompt_tokens,
                                "output_tokens": response.usage.completion_tokens,
                                "total_tokens": response.usage.total_tokens
                            },
                            "response_metadata": {
                                "usage": response.usage.to_json(),
                                "model_name": response.model,
                                "finish_reason": response.choices[0].finish_reason,
                                "logprobs": response.choices[0].logprobs
                            },
                        }
                    ]
                })]
        )