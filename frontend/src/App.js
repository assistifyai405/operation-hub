import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider } from "@/context/AuthContext";
import ProtectedRoute from "@/components/ProtectedRoute";
import Layout from "@/components/Layout";
import Login from "@/pages/Login";
import Register from "@/pages/Register";
import ForgotPassword from "@/pages/ForgotPassword";
import ResetPassword from "@/pages/ResetPassword";
import VerifyEmail from "@/pages/VerifyEmail";
import Dashboard from "@/pages/Dashboard";
import Clients from "@/pages/Clients";
import Projects from "@/pages/Projects";
import ProjectWorkspace from "@/pages/ProjectWorkspace";
import Tasks from "@/pages/Tasks";
import AIChat from "@/pages/AIChat";
import AICopilot from "@/pages/AICopilot";
import AIAgents from "@/pages/AIAgents";
import Proposals from "@/pages/Proposals";
import Contracts from "@/pages/Contracts";
import Invoices from "@/pages/Invoices";
import Documents from "@/pages/Documents";
import Analytics from "@/pages/Analytics";
import Settings from "@/pages/Settings";
import AIWorkspace from "@/pages/AIWorkspace";
import Opportunities from "@/pages/Opportunities";
import CRM from "@/pages/CRM";
import ContactDetail from "@/pages/ContactDetail";
import Pipeline from "@/pages/Pipeline";
import KnowledgeBrain from "@/pages/KnowledgeBrain";
import Automations from "@/pages/Automations";
import Onboarding from "@/pages/Onboarding";
import InviteAccept from "@/pages/InviteAccept";
import EmailCenter from "@/pages/EmailCenter";
import Integrations from "@/pages/Integrations";
import Inbox from "@/pages/Inbox";

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route path="/reset-password" element={<ResetPassword />} />
            <Route path="/verify-email" element={<VerifyEmail />} />
            <Route path="/invite/:token" element={<InviteAccept />} />
            <Route path="/onboarding" element={<ProtectedRoute><Onboarding /></ProtectedRoute>} />
            <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/clients" element={<Clients />} />
              <Route path="/projects" element={<Projects />} />
              <Route path="/projects/:id" element={<ProjectWorkspace />} />
              <Route path="/tasks" element={<Tasks />} />
              <Route path="/ai-chat" element={<AICopilot />} />
              <Route path="/ai-chat-classic" element={<AIChat />} />
              <Route path="/ai-agents" element={<AIAgents />} />
              <Route path="/proposals" element={<Proposals />} />
              <Route path="/contracts" element={<Contracts />} />
              <Route path="/invoices" element={<Invoices />} />
              <Route path="/documents" element={<Documents />} />
              <Route path="/emails" element={<EmailCenter />} />
              <Route path="/inbox" element={<Inbox />} />
              <Route path="/integrations" element={<Integrations />} />
              <Route path="/analytics" element={<Analytics />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/ai-workspace" element={<AIWorkspace />} />
              <Route path="/opportunities" element={<Opportunities />} />
              <Route path="/crm" element={<CRM />} />
              <Route path="/crm/:id" element={<ContactDetail />} />
              <Route path="/pipeline" element={<Pipeline />} />
              <Route path="/knowledge-brain" element={<KnowledgeBrain />} />
              <Route path="/automations" element={<Automations />} />
              <Route path="/ai-history" element={<Navigate to="/ai-workspace" replace />} />
            </Route>
          </Routes>
        </AuthProvider>
      </BrowserRouter>
      <Toaster position="bottom-right" theme="dark" />
    </div>
  );
}

export default App;
