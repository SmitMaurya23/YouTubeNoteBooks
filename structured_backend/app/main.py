import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth_router,chat_router, notebook_router, video_router

app=FastAPI(
    title="YouTube Notebook API"
    description="API for processing YouTube videos, generating content, and managing chat sessions."
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://youtubenotebooks-9pzl.onrender.com", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(auth_router.router)
app.include_router(chat_router.router)
app.include_router(notebook_router.router)
app.include_router(video_router.router)

@app.get("/")
async def read_root():
    return {"message":"Welcome to the youtube notebook api!"}

if __name__=="__main__":
    import uvicorn
    port=int(os.getenv("PORT",8000))
    host=os.getenv("HOST","0.0.0.0")
    uvicorn.run("main:app",host=host,port=port,reload=True)