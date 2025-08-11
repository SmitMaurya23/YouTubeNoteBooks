from typing import List, Dict, Any, Optional
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage
from langchain_google_vertexai import ChatVertexAI

from app.services.rag_service import BasicRAGService
from app.schemas.schema import ChatMessage

MAX_VERBATIM_HISTORY_LENGTH=6

class ChatRAGService:
    """
    Component 2: RAG service that manages conversation history in-memory.
    It can also summarize old history to save token space.
    """
    def __init__(self, llm:ChatVertexAI, rag_service: BasicRAGService):
        self.llm=llm
        self.rag_service=rag_service
        self.summarization_prompt=ChatPromptTemplate.from_messages(
            [("system",
             "You are a helpful assistant whose sole purpose is to concisely summarize."
             "the ptrovided conversation history. FOcus on the main topics and key information "
             "discussed, ignoring conversational filler. The summary should be brief and repressent the essential context continuing the conversation."),
             MessagesPlaceholder(variable_name="chat_history"),
             ("user","Please summarize the above conversation history.")
            ]
        )

        self.summarization_chain=(
            RunnablePassthrough.assign(chat_history=lambda x: x["chat_history"])
            | self.summarization_prompt
            | self.llm
            | StrOutputParser()
        )

        self.chat_prompt=ChatPromptTemplate.from_messages(
            [
                ("system",
                 "You are a helpful assistant for YouTube video content. "
                 "Use the following retrieved video transcript excerpts AND "
                 "the conversation history to answer the user's question. "
                 "If you don't know the answer based on the provided context, "
                 "politely state that you cannot find the answer in the given information. "
                 "You can make up answers but explicitly mention that this is outside of video information. Be concise but informative."
                ),
                MessagesPlaceholder(variable_name="chat_history"),
                ("user", "Context: {context}\nQuestion: {question}"),
            ]
        )

        self.chat_rag_chain=(
            RunnablePassthrough.assign(
                context=lambda x:self.rag_service._get_retriever_chain(
                    x["question"],x["video_id"]
                ),
                chat_history=lambda x: x["chat_history_for_llm"]
            )
            | self.chat_prompt
            | self.llm
            | StrOutputParser()
        )

    async def _summarize_chat_history(self, history_to_summarize:List[ChatMessage])->str:
        if not history_to_summarize:
            return ""
        lc_messages=[HumanMessage(content=msg.content) if msg.role=="user" else AIMessage(content=msg.content) for msg in history_to_summarize]

        try:
            summary=await self.summarization_chain.ainvoke({"chat_history":lc_messages})
            return summary
        except Exception as e:
            print(f"Error during history summarization: {e}")
            return "Error: could not summarize previous conversation."

    async def get_response(self, query_text: str, chat_history: List[ChatMessage], video_id: str)->str:
        """
        Generates a chatbot response with conversation history.
        """
        num_messages=len(chat_history)
        lc_chat_history_for_llm=[]

        if num_messages > MAX_VERBATIM_HISTORY_LENGTH*2:
            messages_to_summarize=chat_history[:-MAX_VERBATIM_HISTORY_LENGTH*2]
            recent_messages=chat_history[:-MAX_VERBATIM_HISTORY_LENGTH*2]

            summary=await self._summarize_chat_history(messages_to_summarize)
            if summary:
                lc_chat_history_for_llm.append(AIMessage(content=f"Previous conversation summary: {summary}"))
            lc_chat_history_for_llm.extend([HumanMessage(content=msg.content) if msg.role=="user" else AIMessage(content=msg.content) for msg in recent_messages])

        else:
            lc_chat_history_for_llm.extend([HumanMessage(content=msg.content) if msg.role == 'user' else AIMessage(content=msg.content) for msg in chat_history])

        try:
            response=await self.chat_rag_chain.ainvoke({
                "question":query_text,
                "chat_history_for_llm": lc_chat_history_for_llm,
                "video_id":video_id
            })
            return response
        except Exception as e:
            print(f"Error in ChatRAGService: {e}")
            return f"Error generating response:{e}"




