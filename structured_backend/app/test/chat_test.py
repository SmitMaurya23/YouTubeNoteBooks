from app.services.rag_service import BasicRAGService
from app.services.chat_rag_service import ChatRAGService
from app.services.persistant_chat_rag_service import PersistentChatRAGService
from app.services.genai_service import GenAIService
from app.services.vector_service import VectorService
from app.repositories.vector_repository import VectorRepository
from app.repositories.mongodb_repository import MongoDBRepository
from app.core.dependencies import get_vector_store, get_gemini_model, get_mongo_client

import asyncio

async def run_test():
    llm=get_gemini_model()
    vector_store=get_vector_store()
    client=get_mongo_client()
    mongodb_repo=MongoDBRepository(client)
    rag_service=BasicRAGService(llm,vector_store)
    chat_rag_service=ChatRAGService(llm,rag_service)
    persistant_chat_rag_service=PersistentChatRAGService(chat_rag_service,mongodb_repo)

    ans=await rag_service.get_response("What is told about India?", "eWiBLgxOcW0")
    print(ans)


if __name__=="__main__":
   asyncio.run(run_test())