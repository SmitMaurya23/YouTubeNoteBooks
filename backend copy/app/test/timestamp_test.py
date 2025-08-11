import asyncio
from app.services.timestamp_service import TimestampService
from app.repositories.vector_repository import VectorRepository
from app.core.dependencies import get_llm_timestamp
from app.core.dependencies import get_vector_store


async def run_test():
    video_id="ehTIhQpj9ys"
    vector_store=get_vector_store()
    vector_repository=VectorRepository(vector_store)
    llm=get_llm_timestamp()
    timestamp_service=TimestampService(llm,vector_repository)
    query="Computer Degree."

    result=await timestamp_service.get_timestamps_for_query(query,video_id)

    for i,timestampentry in enumerate(result):
        print(f"document {i}:\ntimestamp: {timestampentry.timestamp}\ntext: {timestampentry.text}\n\n")



if __name__=="__main__":
    asyncio.run(run_test())