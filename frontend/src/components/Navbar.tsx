// src/components/Navbar.tsx
import React, { useState, useEffect } from 'react';
import axios, { AxiosError } from 'axios'; // Import AxiosError
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL; 

interface NavbarProps {
  userName: string | null;
  notebookId: string | null;
  onLogout: () => void;
  onLoginClick: () => void;
  onBack: () => void; // This prop needs to be passed from App.tsx
}

const Navbar: React.FC<NavbarProps> = ({ userName, notebookId, onLogout, onLoginClick, onBack }) => {
  const [notebookTitle, setNotebookTitle] = useState<string | null>(null);
  const [loadingTitle, setLoadingTitle] = useState<boolean>(false); // New state for loading
  const [titleError, setTitleError] = useState<string | null>(null); // New state for error

  useEffect(() => {
    const fetchNotebookTitle = async () => {
      if (!notebookId) { // Only fetch if notebookId is not null
        setNotebookTitle(null); // Clear title if no notebook is selected
        setLoadingTitle(false);
        setTitleError(null);
        return;
      }

      setLoadingTitle(true);
      setTitleError(null); // Clear previous errors
      try {
        const notebookResponse = await axios.get<{ notebook: { notebook_title: string | null } }>(
          `${API_BASE_URL}/notebook/${notebookId}`
        );
        setNotebookTitle(notebookResponse.data.notebook.notebook_title);
      } catch (err) {
        const errorMessage = (err as AxiosError<{ detail: string }>).response?.data?.detail || 'Failed to load notebook title.';
        setTitleError(errorMessage);
        setNotebookTitle(null); // Ensure title is null on error
        console.error('Error fetching notebook title:', err);
      } finally {
        setLoadingTitle(false);
      }
    };

    fetchNotebookTitle();
  }, [notebookId]);

  const displayTitle = () => {
    if (notebookId) {
      if (loadingTitle) {
        return "Loading...";
      }
      if (titleError) {
        return "Error loading title";
      }
      return `${notebookTitle || 'Untitled Notebook'}`;
    }
    return "";
  };

  return (
    <nav className="bg-gradient-to-r from-blue-600 to-purple-700 p-4 shadow-lg">
      <div className="container mx-auto flex justify-between items-center">
        <div className="text-white text-2xl font-extrabold tracking-wide">
          <span className="text-yellow-300 text-xl">YouTubeNoteBook: </span>{displayTitle()}
        </div>
        <div className="flex items-center space-x-4">
          {/* Show Back to Home button only if a notebook is active */}
          {notebookId && (
            <button
              onClick={onBack}
              className="bg-gray-200 hover:bg-gray-300 text-gray-800 font-semibold py-2 px-4 rounded-lg transition duration-200 flex items-center"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z" clipRule="evenodd" />
              </svg>
              Back to Home
            </button>
          )}

          {userName ? (
            <>
              <span className="text-white text-s font-medium">Hello, {userName}!</span>
              <button
                onClick={onLogout}
                className="bg-red-500 hover:bg-red-600 text-white font-semibold py-2 px-4 rounded-full transition duration-300 ease-in-out transform hover:scale-105"
              >
                Logout
              </button>
            </>
          ) : (
            <button
              onClick={onLoginClick}
              className="bg-green-500 hover:bg-green-600 text-white font-semibold py-2 px-4 rounded-full transition duration-300 ease-in-out transform hover:scale-105"
            >
              Login / Sign Up
            </button>
          )}
        </div>
      </div>
    </nav>
  );
};

export default Navbar;