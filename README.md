# YouTube Notebooks: AI-Powered Video Understanding

## ✨ Project Overview

YouTube Notebooks is an innovative web application designed to revolutionize how you interact with YouTube video content. Beyond simple video playback, this platform allows users to extract deep insights, ask questions, and navigate through video content with the power of cutting-edge AI.

Leveraging FastAPI for the robust backend, React with Vite for a dynamic frontend, and integrating advanced Google AI models (Gemini 2.0 Flash, Text Embedding) with MongoDB Atlas Vector Search, YouTube Notebooks transforms passive watching into active, intelligent learning and note-taking.

## 🚀 Features

* **Intelligent Video Summarization:** Get concise, AI-generated summaries of YouTube videos.
* **Contextual Chatbot Q&A:** Ask questions about any part of the video content and receive intelligent, AI-powered answers that are contextually aware of the video's transcript.
* **Persistent Chat History:** Maintain and retrieve full chat sessions tied to specific videos and notebooks, allowing you to pick up where you left off.
* **Dynamic Timestamp Generation:** Instantly generate precise timestamps for specific topics or questions within a video, making navigation and reference a breeze.
* **Personalized Notebooks:** Organize your video-related insights, chats, and notes into structured notebooks for easy access and management.
* **Intuitive User Interface:** A clean, responsive frontend built with React and Tailwind CSS for a seamless user experience.

## 🛠️ Tech Stack

This project is built with a powerful and modern technology stack:

**Frontend:**
* **React:** A declarative, component-based JavaScript library for building user interfaces.
* **Vite:** A next-generation frontend tooling that provides an extremely fast development experience.
* **TypeScript:** Adds static typing to JavaScript, enhancing code quality and developer productivity.
* **Tailwind CSS:** A utility-first CSS framework for rapidly building custom designs.

**Backend:**
* **FastAPI:** A modern, fast (high-performance) web framework for building APIs with Python 3.7+.
* **Uvicorn:** An ASGI server for running FastAPI applications.
* **Python:** The core language for backend logic and AI integrations.

**Database & Data Management:**
* **MongoDB:** A NoSQL database used for storing video metadata, transcripts, user notebooks, and comprehensive chat histories.
* **MongoDB Atlas Vector Search:** Utilized for efficient similarity search over vector embeddings of video transcripts, enabling the chatbot to retrieve highly relevant content chunks for contextual understanding.

**Artificial Intelligence & Machine Learning:**
* **Google Gemini 1.5 Flash:** A powerful, multimodal large language model from Google AI, used for generating video descriptions, answering chatbot queries, and extracting timestamp information. Its speed and efficiency are key for real-time interactions.
* **Google Text Embedding Models (e.g., `text-embedding-004`):** Employed to convert video transcripts and user queries into high-dimensional numerical vectors, crucial for enabling semantic search capabilities with MongoDB Atlas Vector Search.
* **LangChain:** A framework for developing applications powered by language models, used to orchestrate the interactions between LLMs, vector stores, and memory (chat history).

**Cloud & Infrastructure:**
* **Google Cloud Vertex AI:** Provides the underlying infrastructure and APIs for accessing Google's Gemini models and embedding services.
* **Render:** A cloud platform used for simplified deployment and hosting of both the frontend static site and the FastAPI backend web service.

## 💡 How It Works (High-Level Architecture)

1.  **Video Submission:** A user submits a YouTube video URL via the React frontend.
2.  **Transcript Processing:** The FastAPI backend extracts the video ID, fetches the video's transcript from YouTube, and performs initial processing.
3.  **Embedding & Storage:** The transcript is chunked into smaller, semantically meaningful segments. Each segment is then converted into a numerical vector (embedding) using Google's Text Embedding models. These embeddings, along with their corresponding text, are stored in a MongoDB collection with a Vector Search index.
4.  **Notebook & Session Management:** The backend creates or updates a "notebook" entry for the video and manages chat session IDs within MongoDB.
5.  **Chatbot Interaction:**
    * When a user asks a question, the query is also converted into an embedding.
    * A vector search is performed against the stored transcript embeddings in MongoDB Atlas to retrieve the most semantically relevant video segments.
    * The user's query, the retrieved relevant transcript chunks, and the ongoing chat history (managed by LangChain's memory and stored in MongoDB) are sent to the Google Gemini 1.5 Flash model.
    * Gemini generates a contextual and accurate response based on all provided information.
    * The conversation (user query + AI response) is saved to MongoDB, maintaining the chat session history.
6.  **Timestamp Generation:** For timestamp requests, the relevant sections of the transcript are identified through a similar embedding and LLM process, and precise timestamps are extracted and returned.
7.  **Data Flow:** The React frontend consumes data from and sends requests to the FastAPI backend, which orchestrates all interactions with MongoDB, Google AI services, and LangChain.

## ⚙️ Setup and Local Installation

To run this project locally, follow these steps:

### Prerequisites

* **Python 3.9+**
* **uv & npm** 
* **MongoDB Atlas Account:** A free tier (M0 cluster) is sufficient for development.
* **Google Cloud Project:**
    * Enable the **Vertex AI API**.
    * Ensure billing is enabled (required for Vertex AI, even for free tier usage).
    * Create a Service Account key and download its JSON file. Set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable to the path of this file, or handle authentication in your Python code (Render will use service accounts or env variables).

### 1. Clone the Repository

```bash
git clone [https://github.com/your-username/your-repo-name.git](https://github.com/your-username/your-repo-name.git)
cd your-repo-name