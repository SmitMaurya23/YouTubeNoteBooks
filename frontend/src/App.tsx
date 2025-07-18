// App.tsx (No changes needed in App.tsx for this UI overhaul)
import { useState, useEffect } from 'react';
import axios, { AxiosError } from 'axios';
import Navbar from './components/Navbar';
import YouTubeNoteBook from './components/YouTubeNotebook';
import LoginModal from './components/LoginModal';
import SignUpModal from './components/SignupModal';
import Home from './components/Home';
import './App.css';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL; 

interface VideoSubmissionResponse {
  message: string;
  video_id: string;
}

function App() {
  const [userId, setUserId] = useState<string | null>(null);
  const [userName, setUserName] = useState<string | null>(null);
  const [showLoginModal, setShowLoginModal] = useState(false);
  const [showSignUpModal, setShowSignUpModal] = useState(false);

  // States for LinkSubmission when creating a new notebook
  const [submissionLoading, setSubmissionLoading] = useState<boolean>(false);
  const [submissionError, setSubmissionError] = useState<string | null>(null);
  const [currentVideoId, setCurrentVideoId] = useState<string | null>(null); // To hold videoId for new notebook creation
  const [currentNotebookId, setCurrentNotebookId] = useState<string | null>(null); // To hold notebookId for active notebook
  const [isCreatingNewNotebook, setIsCreatingNewNotebook] = useState<boolean>(false); // To indicate if user is creating a new one


  useEffect(() => {
    // Check for existing user session on component mount
    const storedUserId = localStorage.getItem('user_id');
    const storedUserName = localStorage.getItem('user_name');
    if (storedUserId && storedUserName) {
      setUserId(storedUserId);
      setUserName(storedUserName);
    } else {
      // If no user is logged in, show login modal by default
      setShowLoginModal(true);
    }
  }, []);

  const handleLoginSuccess = (id: string, name: string) => {
    setUserId(id);
    setUserName(name);
    setShowLoginModal(false);
  };

  const handleSignUpSuccess = () => {
    alert('Account created successfully! Please log in.');
    setShowSignUpModal(false);
    setShowLoginModal(true); // After sign up, prompt for login
  };

  const handleLogout = () => {
    setUserId(null);
    setUserName(null);
    localStorage.removeItem('user_id');
    localStorage.removeItem('user_name');
    setCurrentVideoId(null);
    setCurrentNotebookId(null);
    setShowLoginModal(true); // Show login modal after logout
  };

  // This is for submitting a video link when creating a *new* notebook
  const handleSubmitVideoForNewNotebook = async (url: string, notebookTitle: string) => {
    setSubmissionLoading(true);
    setSubmissionError(null);
    setCurrentVideoId(null);

    try {
      // Step 1: Submit video to get video_id
      const videoResponse = await axios.post<VideoSubmissionResponse>(`${API_BASE_URL}/submit-video`, { url });
      const newVideoId = videoResponse.data.video_id;
      setCurrentVideoId(newVideoId);

      // Step 2: Create a new notebook entry with this video_id
      if (userId) {
        const notebookCreateResponse = await axios.post<{ message: string; notebook_id: string }>(
          `${API_BASE_URL}/notebooks`,
          { user_id: userId, video_id: newVideoId, notebook_title: notebookTitle }
        );
        setCurrentNotebookId(notebookCreateResponse.data.notebook_id);
        setIsCreatingNewNotebook(false); // Done creating new notebook
      } else {
        throw new Error("User not logged in to create a notebook.");
      }

    } catch (err) {
      const errorMessage = (err as AxiosError<{ detail: string }>).response?.data?.detail || 'Error submitting video or creating notebook';
      setSubmissionError(errorMessage);
      console.error("Video submission/notebook creation error:", err);
    } finally {
      setSubmissionLoading(false);
    }
  };

  const handleSelectExistingNotebook = (notebookId: string, videoId: string) => {
    setCurrentNotebookId(notebookId);
    setCurrentVideoId(videoId);
    setIsCreatingNewNotebook(false);
  };

  const handleBackToHome = () => {
    setCurrentNotebookId(null);
    setCurrentVideoId(null);
    setIsCreatingNewNotebook(false);
    setSubmissionError(null); // Clear any errors
  };

  const handleCreateNewNotebookClick = () => {
    setIsCreatingNewNotebook(true);
    setCurrentNotebookId(null); // Ensure no old notebook is active
    setCurrentVideoId(null);
  };

  return (
    <div className="min-h-screen bg-gray-100 font-sans antialiased">
      <Navbar userName={userName} notebookId={currentNotebookId} onLogout={handleLogout} onLoginClick={() => setShowLoginModal(true) }  onBack={handleBackToHome} />

      <main className="py-1">
        {!userId ? (
          <>
            {showLoginModal && (
              <LoginModal
                isOpen={showLoginModal}
                onClose={() => setShowLoginModal(false)}
                onLoginSuccess={handleLoginSuccess}
                onSwitchToSignUp={() => { setShowLoginModal(false); setShowSignUpModal(true); }}
              />
            )}
            {showSignUpModal && (
              <SignUpModal
                isOpen={showSignUpModal}
                onClose={() => setShowSignUpModal(false)}
                onSignUpSuccess={handleSignUpSuccess}
                onSwitchToLogin={() => { setShowSignUpModal(false); setShowLoginModal(true); }}
              />
            )}
            {/* Optionally show a message if not logged in and modals are closed */}
            {!showLoginModal && !showSignUpModal && (
                <p className="text-center text-gray-600 mt-10">Please log in to continue.</p>
            )}
          </>
        ) : (
          // User is logged in
          currentNotebookId && currentVideoId ? (
            <YouTubeNoteBook videoId={currentVideoId} notebookId={currentNotebookId}  userId={userId}  />
          ) : (
            <Home
              userId={userId}
              onCreateNewNotebook={handleCreateNewNotebookClick}
              onSelectNotebook={handleSelectExistingNotebook}
              isCreatingNewNotebook={isCreatingNewNotebook}
              onCancelNewNotebook={() => setIsCreatingNewNotebook(false)}
              onSubmitVideoForNewNotebook={handleSubmitVideoForNewNotebook}
              submissionLoading={submissionLoading}
              submissionError={submissionError}
            />
          )
        )}
      </main>
    </div>
  );
}

export default App;