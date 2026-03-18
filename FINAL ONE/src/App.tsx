import { BrowserRouter, Routes, Route, Navigate } from "react-router";
import { useEffect, useState } from "react";
import { onAuthStateChanged, User } from "firebase/auth";
import { auth } from "./firebase";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Predictor from "./pages/Predictor";
import Login from "./pages/Login";

// Protected Route Wrapper
function ProtectedRoute({ children, user, loading }: { children: React.ReactNode, user: User | null, loading: boolean }) {
  if (loading) {
    return (
      <div className="min-h-screen bg-[#0a0a0a] flex items-center justify-center">
        <div className="h-8 w-8 border-4 border-emerald-500/20 border-t-emerald-500 rounded-full animate-spin" />
      </div>
    );
  }
  
  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
      setUser(currentUser);
      setLoading(false);
    });
    return () => unsubscribe();
  }, []);

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={
          <ProtectedRoute user={user} loading={loading}>
            <Layout user={user} />
          </ProtectedRoute>
        }>
          <Route index element={<Dashboard />} />
          <Route path="predictor" element={<Predictor />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
