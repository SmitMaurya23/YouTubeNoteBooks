from app.services.vector_service import VectorService
from app.services.transcript_processing_service import TranscriptProcessingService
from app.repositories.vector_repository import VectorRepository
from app.core.dependencies import get_vector_store, get_youtube_service
from langchain_core.documents import Document

def run_test(url,query):
    transcript_processing_service=TranscriptProcessingService()
    vector_repository=VectorRepository(vector_store=get_vector_store())
    #vector_service=VectorService(vector_repository,transcript_processing_service)
    youtube_service=get_youtube_service()

    video_id=youtube_service.extract_video_id(url)
    #transcript_list=youtube_service.fetch_transcript(video_id)
    #vector_service.embed_and_store_transcript(video_id,transcript_list)
    #print("Embedding done successfully!!")
    query_results = vector_repository.similarity_search_query(query,2,{"video_id": video_id})
    print("Similarity search results:")
    for doc in query_results:
        print(f"- Content: {doc.page_content[:100]}...")
        print(f"  Metadata: {doc.metadata}")
        if 'start' in doc.metadata and 'end' in doc.metadata:
            print(f"  Time Range: {doc.metadata['start']} - {doc.metadata['end']} seconds")

    print("completed!!!")

if __name__=="__main__":
    run_test("https://youtu.be/ehTIhQpj9ys?si=Fcsaza8VFT37majY","computer science degree?")