
from pymongo import MongoClient
from pymongo.collection import Collection
from bson.objectid import ObjectId
import uuid
from typing import List, Dict, Optional
from app.core.schema import ChatMessage, ChatSessionSummary, VideoDescription, VideoDBEntry
from datetime import datetime
from app.core.settings import settings

class ChatMongoDBRepository:

    """Repository class to handle all interactions with the MongoDB database"""

    def __init__(self, client: MongoClient):
        if(settings.DB_NAME is None):
            raise
        self.db=client[settings.DB_NAME]
        self.chat_sessions_collection: Collection=self.db["chat_sessions"]
        self.notebooks_collection: Collection=self.db["notebooks"]
        self.chat_sessions_collection.create_index("session_id", unique=True)
        print(f"MongoDBRepository connected to database: {self.db.name}")

    async def create_new_chat_session(self, user_id:str, notebook_id:str, video_id:str, first_user_prompt:str="")->str:
        session_id=str(uuid.uuid4())
        session_data={
            "session_id": session_id,
            "user_id": user_id,
            "video_id": video_id,
            "notebook_id": notebook_id,
            "history": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "first_prompt": first_user_prompt
        }
        self.chat_sessions_collection.insert_one(session_data)

        self.notebooks_collection.update_one(
            {"_id":ObjectId(notebook_id)},
            {"$addToSet": {"session_id_list":session_id},
             "$set":{"latest_session_id": session_id,
                     "updated_at":datetime.utcnow()}
             }
        )
        print(F"New chat session created and notebook {notebook_id} updated with session ID: {session_id}")

        return session_id

    async def get_chat_history(self, session_id:str)->List[ChatMessage]:
        session_doc=self.chat_sessions_collection.find_one({
            "session_id":session_id
        })
        if session_doc and session_doc.get("history"):
            return [ChatMessage(**msg) for msg in session_doc["history"]]
        return []

    async def update_chat_history(self, session_id:str, user_message: ChatMessage, ai_message: ChatMessage):
        self.chat_sessions_collection.update_one(
            {"session_id":session_id},
            {
                "$push":{"history":{"$each":[user_message.model_dump(),ai_message.model_dump()]}},
                "$set":{"updated_at": datetime.utcnow()}
            }
        )

    async def get_session_summary(self, session_id:str)->Optional[ChatSessionSummary]:
        session_doc=self.chat_sessions_collection.find_one(
            {"session_id":session_id},
            {"session_id":1, "first_prompt":1, "created_at":1, "notebook_id": 1}
        )
        if session_doc:
            return ChatSessionSummary(**session_doc)
        return None



