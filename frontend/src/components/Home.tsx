// src/components/Home.tsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import LinkSubmission from './LinkSubmission'; // Import LinkSubmission for new notebook creation

interface Notebook {
  _id: string;
  user_id: string;
  video_id: string;
  notebook_title: string;
  // Add other fields you might want to display, e.g., created_at
}

interface HomeProps {
  userId: string;
  onCreateNewNotebook: () => void;
  onSelectNotebook: (notebookId: string, videoId: string) => void;
  isCreatingNewNotebook: boolean;
  onCancelNewNotebook: () => void;
  onSubmitVideoForNewNotebook: (url: string, notebookTitle: string) => void;
  submissionLoading: boolean;
  submissionError: string | null;
}

const Home: React.FC<HomeProps> = ({
  userId,
  onCreateNewNotebook,
  onSelectNotebook,
  isCreatingNewNotebook,
  onCancelNewNotebook,
  onSubmitVideoForNewNotebook,
  submissionLoading,
  submissionError,
}) => {
  const [notebooks, setNotebooks] = useState<Notebook[]>([]);
  const [loadingNotebooks, setLoadingNotebooks] = useState<boolean>(true);
  const [errorNotebooks, setErrorNotebooks] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [newNotebookTitle, setNewNotebookTitle] = useState<string>(''); // For new notebook title input

  useEffect(() => {
    const fetchNotebooks = async () => {
      setLoadingNotebooks(true);
      setErrorNotebooks(null);
      try {
        const response = await axios.get<{ notebooks: Notebook[] }>(`http://localhost:8000/notebooks/${userId}`);
        setNotebooks(response.data.notebooks);
      } catch (err: any) {
        setErrorNotebooks(err.response?.data?.detail || 'Failed to fetch notebooks');
      } finally {
        setLoadingNotebooks(false);
      }
    };

    if (userId) {
      fetchNotebooks();
    }
  }, [userId, isCreatingNewNotebook]); // Re-fetch when creating new notebook state changes

  const filteredNotebooks = notebooks.filter(notebook =>
    notebook.notebook_title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleNewLinkSubmission = (url: string) => {
    if (!newNotebookTitle.trim()) {
      alert('Please enter a title for your new notebook.');
      return;
    }
    onSubmitVideoForNewNotebook(url, newNotebookTitle);
  };

  return (
    <div className="container mx-auto p-4">
      <h2 className="text-3xl font-bold text-center text-gray-900 mb-8">Your Notebooks</h2>

      {!isCreatingNewNotebook && (
        <div className="mb-6 flex justify-between items-center">
          <input
            type="text"
            placeholder="Search notebooks by title..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="flex-grow border border-gray-300 p-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 transition duration-200 mr-4"
          />
          <button
            onClick={onCreateNewNotebook}
            className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-6 rounded-lg shadow-md transition duration-200 flex items-center"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 5a1 1 0 011 1v3h3a1 1 0 110 2h-3v3a1 1 0 11-2 0v-3H6a1 1 0 110-2h3V6a1 1 0 011-1z" clipRule="evenodd" />
            </svg>
            Create New Notebook
          </button>
        </div>
      )}

      {isCreatingNewNotebook ? (
        <div className="bg-white p-8 rounded-lg shadow-lg w-full max-w-md mx-auto mt-8">
            <h3 className="text-xl font-bold mb-4 text-gray-800">New YouTube Notebook</h3>
            <div className="mb-4">
                <label className="block text-gray-700 text-sm font-bold mb-2" htmlFor="newNotebookTitle">
                    Notebook Title
                </label>
                <input
                    type="text"
                    id="newNotebookTitle"
                    value={newNotebookTitle}
                    onChange={(e) => setNewNotebookTitle(e.target.value)}
                    placeholder="Enter a title for your new notebook"
                    className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
                    disabled={submissionLoading}
                />
            </div>
          <LinkSubmission
            onSubmit={handleNewLinkSubmission}
            isLoading={submissionLoading}
            error={submissionError}
          />
          <button
            onClick={onCancelNewNotebook}
            className="mt-4 w-full p-2 rounded-md text-gray-700 bg-gray-200 hover:bg-gray-300 transition-colors duration-200"
            disabled={submissionLoading}
          >
            Cancel
          </button>
        </div>
      ) : (
        <>
          {loadingNotebooks && <p className="text-center text-gray-600">Loading notebooks...</p>}
          {errorNotebooks && <p className="text-red-500 text-center">{errorNotebooks}</p>}
          {!loadingNotebooks && !errorNotebooks && filteredNotebooks.length === 0 && (
            <p className="text-center text-gray-600">No notebooks found. Click "Create New Notebook" to get started!</p>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredNotebooks.map((notebook) => (
              <div
                key={notebook._id}
                onClick={() => onSelectNotebook(notebook._id, notebook.video_id)}
                className="bg-white rounded-lg shadow-lg overflow-hidden cursor-pointer hover:shadow-xl transition-shadow duration-300 transform hover:-translate-y-1"
              >
                <div className="relative w-full" style={{ paddingTop: '56.25%' }}> {/* 16:9 aspect ratio */}
                  <img
                    src={`https://img.youtube.com/vi/${notebook.video_id}/hqdefault.jpg`}
                    alt={notebook.notebook_title}
                    className="absolute top-0 left-0 w-full h-full object-cover"
                    onError={(e) => { e.currentTarget.src = '/placeholder-video.png'; }} // Fallback image
                  />
                </div>
                <div className="p-4">
                  <h3 className="text-xl font-semibold text-gray-800 truncate">{notebook.notebook_title}</h3>
                  <p className="text-gray-600 text-sm mt-1">Video ID: {notebook.video_id}</p>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
};

export default Home;