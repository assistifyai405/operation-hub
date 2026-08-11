import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider } from "@/context/AuthContext";
import { LocaleProvider } from "@/context/LocaleContext";
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
import { PrivacyPage, TermsPage, BetaNoticePage } from "@/pages/LegalPages";
import HomePage from "@/pages/marketing/HomePage";
import ProductIndexPage from "@/pages/marketing/ProductIndexPage";
import CopilotPage from "@/pages/marketing/CopilotPage";
import CrmPage from "@/pages/marketing/CrmPage";
import MarketingProjectsPage from "@/pages/marketing/ProjectsPage";
import MarketingAutomationsPage from "@/pages/marketing/AutomationsPage";
import MarketingDocumentsPage from "@/pages/marketing/DocumentsPage";
import PricingPage from "@/pages/marketing/PricingPage";
import FaqPage from "@/pages/marketing/FaqPage";
import SecurityPage from "@/pages/marketing/SecurityPage";
import SolutionsPage from "@/pages/marketing/SolutionsPage";
import ProductDetailPage from "@/pages/marketing/ProductDetailPage";

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <AuthProvider>
          <LocaleProvider>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route path="/reset-password" element={<ResetPassword />} />
            <Route path="/verify-email" element={<VerifyEmail />} />
            <Route path="/invite/:token" element={<InviteAccept />} />
            <Route path="/privacy" element={<PrivacyPage />} />
            <Route path="/terms" element={<TermsPage />} />
            <Route path="/beta-notice" element={<BetaNoticePage />} />
            <Route path="/product" element={<ProductIndexPage />} />
            <Route path="/product/copilot" element={<CopilotPage />} />
            <Route path="/product/crm" element={<CrmPage />} />
            <Route path="/product/projects" element={<MarketingProjectsPage />} />
            <Route path="/product/automations" element={<MarketingAutomationsPage />} />
            <Route path="/product/documents" element={<MarketingDocumentsPage />} />
            <Route path="/product/proposals" element={<Navigate to="/product/documents" replace />} />
            <Route path="/product/contracts" element={<Navigate to="/product/documents" replace />} />
            <Route path="/product/invoices" element={<Navigate to="/product/documents" replace />} />
            <Route path="/product/agents" element={<ProductDetailPage slug="agents" />} />
            <Route path="/product/knowledge" element={<ProductDetailPage slug="knowledge" />} />
            <Route path="/product/opportunities" element={<ProductDetailPage slug="opportunities" />} />
            <Route path="/pricing" element={<PricingPage />} />
            <Route path="/faq" element={<FaqPage />} />
            <Route path="/security" element={<SecurityPage />} />
            <Route path="/solutions" element={<SolutionsPage />} />
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
          </LocaleProvider>
        </AuthProvider>
      </BrowserRouter>
      <Toaster position="bottom-right" theme="dark" />
    </div>
  );
}

export default App;
