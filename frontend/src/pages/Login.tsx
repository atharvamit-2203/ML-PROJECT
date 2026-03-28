import React, { useState } from 'react';
import { useNavigate } from 'react-router';
import { auth, googleProvider, linkedInProvider } from '../firebase';
import { signInWithPopup, signInWithRedirect, getRedirectResult } from 'firebase/auth';
import { Shield, TrendingUp, Mail, AlertCircle } from 'lucide-react';

export default function Login() {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<string | null>(null);

  const handleGoogleSignIn = async () => {
    try {
      setIsLoading('google');
      setError(null);
      await signInWithPopup(auth, googleProvider);
      navigate('/');
    } catch (err: any) {
      console.error("Google sign-in error:", err);
      setError(err.message || "Failed to sign in with Google.");
    } finally {
      setIsLoading(null);
    }
  };

  const handleLinkedInSignIn = async () => {
    try {
      setIsLoading('linkedin');
      setError(null);
      // Note: This requires LinkedIn OAuth setup in Firebase Console
      await signInWithPopup(auth, linkedInProvider);
      navigate('/');
    } catch (err: any) {
      console.error("LinkedIn sign-in error:", err);
      setError("LinkedIn login requires additional configuration in the Firebase Console. Please use Google for now.");
    } finally {
      setIsLoading(null);
    }
  };

  const handleBrokerSignIn = () => {
    setIsLoading('broker');
    setError(null);
    // Simulate broker OAuth redirect
    setTimeout(() => {
      setError("Broker OAuth integration requires specific API keys from your broker (Zerodha, Upstox, etc.). Please use Google for now.");
      setIsLoading(null);
    }, 1500);
  };

  return (
    <div className="min-h-screen bg-[#0a0a0a] flex items-center justify-center p-4 selection:bg-emerald-500/30">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-500/20 text-emerald-400 mb-4">
            <TrendingUp className="h-6 w-6" />
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Welcome to QuantTrade</h1>
          <p className="text-zinc-400 text-sm mt-2">Connect your account to access AI predictions</p>
        </div>

        {/* Login Card */}
        <div className="rounded-2xl border border-white/10 bg-[#121212] p-8 shadow-2xl backdrop-blur-xl">
          <div className="space-y-4">
            {error && (
              <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 flex items-start gap-3">
                <AlertCircle className="h-5 w-5 text-rose-400 shrink-0 mt-0.5" />
                <p className="text-sm text-rose-400">{error}</p>
              </div>
            )}

            <button
              onClick={handleGoogleSignIn}
              disabled={isLoading !== null}
              className="w-full flex items-center justify-center gap-3 rounded-xl bg-white px-4 py-3 text-sm font-semibold text-black hover:bg-zinc-200 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading === 'google' ? (
                <div className="h-5 w-5 border-2 border-black/20 border-t-black rounded-full animate-spin" />
              ) : (
                <svg className="h-5 w-5" viewBox="0 0 24 24">
                  <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
                  <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                  <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
                  <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
                </svg>
              )}
              Continue with Google
            </button>

            <button
              onClick={handleLinkedInSignIn}
              disabled={isLoading !== null}
              className="w-full flex items-center justify-center gap-3 rounded-xl bg-[#0A66C2] px-4 py-3 text-sm font-semibold text-white hover:bg-[#004182] transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading === 'linkedin' ? (
                <div className="h-5 w-5 border-2 border-white/20 border-t-white rounded-full animate-spin" />
              ) : (
                <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
                </svg>
              )}
              Continue with LinkedIn
            </button>

            <div className="relative py-4">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-white/10"></div>
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="bg-[#121212] px-2 text-zinc-500">Or connect broker</span>
              </div>
            </div>

            <button
              onClick={handleBrokerSignIn}
              disabled={isLoading !== null}
              className="w-full flex items-center justify-center gap-3 rounded-xl bg-zinc-800 px-4 py-3 text-sm font-semibold text-white hover:bg-zinc-700 transition-all border border-white/5 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading === 'broker' ? (
                <div className="h-5 w-5 border-2 border-white/20 border-t-white rounded-full animate-spin" />
              ) : (
                <Shield className="h-5 w-5 text-emerald-400" />
              )}
              Connect Stock Broker
            </button>
          </div>

          <p className="mt-8 text-center text-xs text-zinc-500">
            By connecting, you agree to our Terms of Service and Privacy Policy.
            We never execute trades without your explicit permission.
          </p>
        </div>
      </div>
    </div>
  );
}
