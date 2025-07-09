// src/components/SignUpModal.tsx
import React, { useState } from 'react';
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL; 

interface SignUpModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSignUpSuccess: () => void;
  onSwitchToLogin: () => void;
}

const SignUpModal: React.FC<SignUpModalProps> = ({ isOpen, onClose, onSignUpSuccess, onSwitchToLogin }) => {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/signup`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ user_name: username, user_email: email, password }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Sign Up failed');
      }

      onSignUpSuccess(); // Notify parent of success
      onClose(); // Close modal after successful signup
    } catch (err: any) {
      setError(err.message || 'An unknown error occurred');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 flex justify-center items-center z-50">
      <div className="bg-white p-8 rounded-lg shadow-xl w-full max-w-md">
        <h2 className="text-2xl font-bold mb-6 text-center text-gray-800">Create New Account</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-gray-700 text-sm font-bold mb-2" htmlFor="username">
              Username
            </label>
            <input
              type="text"
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
              required
              disabled={loading}
            />
          </div>
          <div>
            <label className="block text-gray-700 text-sm font-bold mb-2" htmlFor="signup-email">
              Email
            </label>
            <input
              type="email"
              id="signup-email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
              required
              disabled={loading}
            />
          </div>
          <div>
            <label className="block text-gray-700 text-sm font-bold mb-2" htmlFor="signup-password">
              Password
            </label>
            <input
              type="password"
              id="signup-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 mb-3 leading-tight focus:outline-none focus:shadow-outline"
              required
              disabled={loading}
            />
          </div>
          {error && <p className="text-red-500 text-xs italic text-center">{error}</p>}
          <button
            type="submit"
            className={`w-full bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline transition duration-200 ${
              loading ? 'opacity-50 cursor-not-allowed' : ''
            }`}
            disabled={loading}
          >
            {loading ? 'Signing Up...' : 'Sign Up'}
          </button>
        </form>
        <p className="mt-4 text-center text-gray-600 text-sm">
          Already have an account?{' '}
          <button onClick={onSwitchToLogin} className="text-green-600 hover:underline font-bold">
            Login
          </button>
        </p>
        <button onClick={onClose} className="mt-4 w-full text-gray-500 hover:text-gray-700">
          Close
        </button>
      </div>
    </div>
  );
};

export default SignUpModal;