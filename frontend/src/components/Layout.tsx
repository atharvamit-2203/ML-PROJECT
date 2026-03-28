import { useState } from "react";
import { Outlet, Link, useLocation, useNavigate } from "react-router";
import { LineChart, Calculator, TrendingUp, Menu, LogOut, User as UserIcon, Gamepad2 } from "lucide-react";

import { auth } from "../firebase";
import { signOut, User } from "firebase/auth";

export default function Layout({ user }: { user: User | null }) {
  const location = useLocation();
  const navigate = useNavigate();
  const [showDropdown, setShowDropdown] = useState(false);

  const handleSignOut = async () => {
    try {
      await signOut(auth);
      navigate('/login');
    } catch (error) {
      console.error("Error signing out:", error);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-white font-sans selection:bg-emerald-500/30">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-white/10 bg-[#0a0a0a]/80 backdrop-blur-md">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/20 text-emerald-400">
                <TrendingUp className="h-5 w-5" />
              </div>
              <span className="text-lg font-semibold tracking-tight">QuantTrade</span>
            </div>

            <nav className="hidden md:flex items-center gap-6">
              <Link
                to="/"
                className={`flex items-center gap-2 text-sm font-medium transition-colors ${location.pathname === "/" ? "text-white" : "text-zinc-400 hover:text-white"
                  }`}
              >
                <LineChart className="h-4 w-4" />
                Markets
              </Link>
              <Link
                to="/predictor"
                className={`flex items-center gap-2 text-sm font-medium transition-colors ${location.pathname === "/predictor" ? "text-white" : "text-zinc-400 hover:text-white"
                  }`}
              >
                <Calculator className="h-4 w-4" />
                AI Predictor
              </Link>
              <Link
                to="/simulator"
                className={`flex items-center gap-2 text-sm font-medium transition-colors ${location.pathname === "/simulator" ? "text-white" : "text-zinc-400 hover:text-white"
                  }`}
              >
                <Gamepad2 className="h-4 w-4" />
                Simulator
              </Link>

            </nav>

            <div className="flex items-center gap-4">
              <div className="relative">
                <button
                  onClick={() => setShowDropdown(!showDropdown)}
                  className="hidden md:flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition-colors bg-emerald-500/20 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/30"
                >
                  {user?.photoURL ? (
                    <img src={user.photoURL} alt="Profile" className="w-5 h-5 rounded-full" referrerPolicy="no-referrer" />
                  ) : (
                    <UserIcon className="w-4 h-4" />
                  )}
                  <span className="max-w-[100px] truncate">{user?.displayName || user?.email || 'Connected'}</span>
                </button>

                {showDropdown && (
                  <div className="absolute right-0 mt-2 w-48 rounded-xl border border-white/10 bg-[#121212] py-1 shadow-2xl backdrop-blur-xl">
                    <div className="px-4 py-2 border-b border-white/5 mb-1">
                      <p className="text-sm font-medium text-white truncate">{user?.displayName}</p>
                      <p className="text-xs text-zinc-400 truncate">{user?.email}</p>
                    </div>
                    <button
                      onClick={handleSignOut}
                      className="w-full flex items-center gap-2 px-4 py-2 text-sm text-rose-400 hover:bg-white/5 transition-colors"
                    >
                      <LogOut className="h-4 w-4" />
                      Sign Out
                    </button>
                  </div>
                )}
              </div>
              <button className="md:hidden p-2 text-zinc-400 hover:text-white">
                <Menu className="h-5 w-5" />
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>
    </div>
  );
}
