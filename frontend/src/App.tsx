import { useState } from 'react';
import axios, { AxiosError } from 'axios';
import './App.css';

// Define interfaces for API responses
interface VideoSubmissionResponse {
  message: string;
  video_id: string;
}

interface TranscriptEntry {
  text: string;
  start: number;
  duration: number;
}

interface TranscriptResponse {
  video_id: string;
  transcript: TranscriptEntry[];
}

interface DescriptionResponse {
  video_id: string;
  title: string;
  keywords: string[];
  category_tags: string[];
  detailed_description: string;
  summary: string;
}

function App() {
  const [url, setUrl] = useState<string>('');
  const [videoId, setVideoId] = useState<string>('');
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [description, setDescription] = useState<DescriptionResponse | null>(null);
  const [error, setError] = useState<string>('');
  const [isLoadingTranscript, setIsLoadingTranscript] = useState<boolean>(false);
  const [isLoadingDescription, setIsLoadingDescription] = useState<boolean>(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setTranscript([]);
    setDescription(null);
    try {
      const response = await axios.post<VideoSubmissionResponse>('http://localhost:8000/submit-video', { url });
      setVideoId(response.data.video_id);
    } catch (err) {
      const errorMessage = (err as AxiosError<{ detail: string }>).response?.data?.detail || 'Error submitting video';
      setError(errorMessage);
    }
  };

  const fetchTranscript = async () => {
    setError('');
    setIsLoadingTranscript(true);
    try {
      const response = await axios.get<TranscriptResponse>(`http://localhost:8000/transcript/${videoId}`);
      setTranscript(response.data.transcript);
    } catch (err) {
      const errorMessage = (err as AxiosError<{ detail: string }>).response?.data?.detail || 'Error fetching transcript';
      setError(errorMessage);
    } finally {
      setIsLoadingTranscript(false);
    }
  };

  const fetchDescription = async () => {
    setError('');
    setIsLoadingDescription(true);
    try {
      const response = await axios.get<DescriptionResponse>(`http://localhost:8000/description/${videoId}`);
      setDescription(response.data);
    } catch (err) {
      const errorMessage = (err as AxiosError<{ detail: string }>).response?.data?.detail || 'Error fetching description';
      setError(errorMessage);
    } finally {
      setIsLoadingDescription(false);
    }
  };

  return (
    <div className="container mx-auto p-4 max-w-2xl">
      <h1 className="text-3xl font-bold mb-6 text-center">YouTube Notebook</h1>
      
      <form onSubmit={handleSubmit} className="mb-6">
        <input
          type="text"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="Enter YouTube URL"
          className="border p-3 rounded w-full mb-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          type="submit"
          className="bg-blue-500 text-white p-3 rounded w-full hover:bg-blue-600 transition-colors"
        >
          Submit Video
        </button>
      </form>

      {videoId && (
        <div className="mb-6">
          <p className="mb-3 text-gray-700">Video ID: <span className="font-semibold">{videoId}</span></p>
          <div className="flex space-x-4">
            <button
              onClick={fetchTranscript}
              disabled={isLoadingTranscript}
              className={`flex-1 p-3 rounded text-white transition-colors ${
                isLoadingTranscript ? 'bg-green-300 cursor-not-allowed' : 'bg-green-500 hover:bg-green-600'
              }`}
            >
              {isLoadingTranscript ? 'Loading...' : 'Get Transcript'}
            </button>
            <button
              onClick={fetchDescription}
              disabled={isLoadingDescription}
              className={`flex-1 p-3 rounded text-white transition-colors ${
                isLoadingDescription ? 'bg-purple-300 cursor-not-allowed' : 'bg-purple-500 hover:bg-purple-600'
              }`}
            >
              {isLoadingDescription ? 'Loading...' : 'Get Description'}
            </button>
          </div>
        </div>
      )}

      {error && (
        <p className="text-red-500 mb-6 p-3 bg-red-100 rounded">{error}</p>
      )}

      {transcript.length > 0 && (
        <div className="mb-6">
          <h2 className="text-xl font-semibold mb-3">Transcript</h2>
          <ul className="list-disc pl-5 bg-gray-50 p-4 rounded max-h-96 overflow-y-auto">
            {transcript.map((entry, index) => (
              <li key={index} className="mb-2">
                <span className="text-gray-600">[{entry.start.toFixed(1)}s]:</span> {entry.text}
              </li>
            ))}
          </ul>
        </div>
      )}

      {description && (
        <div className="space-y-6">
          <div>
            <h2 className="text-xl font-semibold mb-3">Video Title</h2>
            <p className="bg-gray-50 p-4 rounded font-medium">{description.title || 'No title available'}</p>
          </div>

            <div>
            <h2 className="text-xl font-semibold mb-3">Category Tags</h2>
            <p className="bg-gray-50 p-4 rounded italic">
              {description.category_tags && description.category_tags.length > 0
              ? description.category_tags.join(', ')
              : 'No category tags available'}
            </p>
            </div>

          <div>
            <h2 className="text-xl font-semibold mb-3">Keywords</h2>
            <p className="bg-gray-50 p-4 rounded italic">
              {description.keywords && description.keywords.length > 0
              ? description.keywords.join(', ')
              : 'No keywords available'}
            </p>
            </div>

          <div>
            <h2 className="text-xl font-semibold mb-3">Detailed Description</h2>
            <ul className="list-disc pl-5 bg-gray-50 p-4 rounded">
              {description.detailed_description.split('||').map((point, index) => (
                <li key={index} className="mb-2">{point || 'No details available'}</li>
              ))}
            </ul>
          </div>
          <div>
            <h2 className="text-xl font-semibold mb-3">Summary</h2>
            <div className="bg-gray-50 p-4 rounded">
              {description.summary.split('||').map((paragraph, index) => (
                <p key={index} className="mb-2">{paragraph || 'No summary available'}</p>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;