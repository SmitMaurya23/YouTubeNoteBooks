# app/services/persistent_chat_rag_service.py
from typing import List, Optional, Tuple
from langchain_core.messages import HumanMessage, AIMessage

from app.services.chat_rag_service import ChatRAGService
from app.repositories.chat_mongodb_repository import ChatMongoDBRepository
from app.core.schema import ChatMessage

class PersistentChatRAGService:
    """
    Component 3: A service that manages the full chat session lifecycle,
    including loading and saving history from a persistent store (MongoDB).
    """
    def __init__(self, chat_rag_service: ChatRAGService, chat_mongo_repo: ChatMongoDBRepository):
        self.chat_rag_service = chat_rag_service
        self.chat_mongo_repo = chat_mongo_repo

    async def get_response_with_storage(
        self, query_text: str, session_id: str, user_id: str, video_id: str
    ) -> Tuple[str, str]:
        """
        Generates a chatbot response by loading history from storage, generating a response,
        and then saving the updated history back to storage.
        """
        # 1. Retrieve history from storage
        chat_history = await self.chat_mongo_repo.get_chat_history(session_id)

        # 2. Generate the response using the chat RAG service
        ai_response_text = await self.chat_rag_service.get_response(
            query_text=query_text,
            chat_history=chat_history,
            video_id=video_id
        )

        # 3. Update history in storage
        await self.chat_mongo_repo.update_chat_history(
            session_id=session_id,
            user_message=ChatMessage(role="user", content=query_text),
            ai_message=ChatMessage(role="assistant", content=ai_response_text)
        )

        return ai_response_text, session_id

