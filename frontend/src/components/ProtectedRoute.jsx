import { Navigate } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { useAuth } from "@/context/AuthContext";

export default function ProtectedRoute({ children }) {
  const { user } = useAuth();
  if (user === null) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-black text-zinc-500" data-testid="auth-loading">
        <Loader2 className="h-7 w-7 animate-spin" />
      </div>
    );
  }
  if (user === false) return <Navigate to="/login" replace />;
  return children;
}
