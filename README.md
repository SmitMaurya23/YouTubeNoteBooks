
# YouTube Notebooks: AI-Powered Video Understanding & Note-Taking

[Visit YouTube Notebooks](https://youtubenotebooks-9pzl.onrender.com/)

## ✨ Project Overview

YouTube Notebooks is an innovative web application that transforms the way you interact with YouTube videos.
Instead of passively watching, you can now **summarize**, **chat**, **navigate**, and **take notes** — all powered by state-of-the-art AI.

This platform enables:

- AI-generated video summaries
- Interactive, context-aware Q&A
- Dynamic timestamp navigation
- Persistent notebooks and chat sessions
- User account management with CRUD support for notebooks

By combining **FastAPI**, **React**, **LangChain**, **Google Gemini Models**, and **MongoDB Atlas Vector Search**, YouTube Notebooks creates an intelligent layer on top of YouTube content, enabling a smarter, more productive viewing experience.

---

## 🚀 Core Functionalities

### User Management
- Create an account and log in securely.
- Manage multiple notebooks tied to your account.
- Add, update, or delete notebooks (video data remains cached for efficiency).

### Notebook Creation & Video Processing
- Submit a YouTube video URL to create a notebook.
- The system:
  - Fetches the transcript.
  - Checks if the video already exists in the database (prevents re-processing).
  - If new, splits transcript into chunks, embeds them with Google Vertex AI, and stores them in MongoDB with vector search.
  - Stores timestamps (`start`, `end`, `duration`) for precise navigation.

### AI-Powered Video Interaction
- **Summarization:** Generate concise, AI-based summaries of videos via Gemini 2.5 Flash.
- **Interactive Chatbot:** Ask questions about the video; AI retrieves the most relevant transcript chunks and uses prior chat history to respond.
- **Persistent Chat Sessions:** Each chat is tied to a notebook and stored. Older chats are summarized after every 6 turns to preserve context without exceeding LLM context limits.
- **Dynamic Timestamps:** When asking about a topic, matching transcript chunks return clickable timestamps — instantly jumping to the correct portion of the video.

### Notebooks Dashboard
- Search notebooks by title.
- Retrieve previously created notebooks instantly.
- View video, chat, and notes in a single unified interface.

---

## 🏗️ Architecture

The system follows a **layered monolithic architecture** with clear separation of concerns:

```
Frontend (React + Vite + Tailwind)  <--->  Backend (FastAPI + LangChain)  <--->  MongoDB Atlas
```

**Layers (Backend):**
- **Routers**: Handle HTTP endpoints (`chat_router.py`, `notebook_router.py`, `user_router.py`, `video_router.py`).
- **Service Layer**: Implements business logic (`chat_rag_service.py`, `timestamp_service.py`, `genai_service.py`, etc.).
- **Repository Layer**: Manages data persistence (`chat_mongodb_repository.py`, `video_mongodb_repository.py`, etc.).
- **Core Layer**: Shared utilities, schemas, configs (`dependencies.py`, `embeddings.py`, `settings.py`, etc.).

**Hosting:**
- **Frontend**: Hosted as a static site on Render.
- **Backend**: Deployed as a web service on Render.
- **Database**: MongoDB Atlas (cloud-based, vector search enabled).

---

## 🛠️ Tech Stack

### Frontend
- **React + Vite** — Fast, modern web interface.
- **TypeScript** — Safer, more maintainable code.
- **Tailwind CSS** — Rapid, responsive styling.

### Backend
- **FastAPI** — High-performance Python web framework.
- **Uvicorn** — ASGI server for FastAPI.
- **LangChain** — Orchestration of LLM, embeddings, and memory.

### Database & Vector Search
- **MongoDB Atlas** — Stores users, videos, embeddings, chat sessions, and notebooks.
- **Vector Search** — Enables semantic retrieval for chatbot and timestamps.

### AI Models & Services
- **Google Gemini (2.5 Flash)** — Summarization, chatbot responses.
- **Google Vertex AI Text Embedding (`gemini-embedding-001`)** — Converts transcript and queries into embeddings.
- **Chunk-based RAG** — Retrieval-Augmented Generation pipeline for contextual answers.

---

## ⚙️ Setup & Local Installation

### Prerequisites
- **Python 3.9+**
- **Node.js + npm** (or **uv** for Python environment management)
- **MongoDB Atlas Account** (free M0 cluster sufficient)
- **Google Cloud Project** with:
  - Vertex AI API enabled
  - Service account JSON key downloaded
  - `GOOGLE_APPLICATION_CREDENTIALS` environment variable set to that key’s path

---

### 1. Clone the Repository
```bash
git clone https://github.com/SmitMaurya23/YouTubeNoteBooks.git
cd YouTubeNoteBooks
```

---

### 2. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file with your MongoDB URI and other cloud  secrets.

Run the FastAPI server:
```bash
uv run main.py
```

---

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

---

### 4. Access the Application
Visit:
```
http://localhost:5173
```

---

## 📂 MongoDB Collections

- **Users** — user profile and notebook references
- **Videos** — transcript, URL, metadata
- **Notebooks** — tie user, video, and chat sessions
- **Chat Sessions** — persistent conversational history
- **Video Embeddings** — transcript chunk vectors for semantic search

---

## 📌 Future Enhancements
- OAuth-based authentication (Google/GitHub)
- Collaborative notebooks (shared with other users)
- Multi-video topic-based summarization
- Advanced note-taking and export features (PDF/Markdown)
