import "@/App.css";
import { Suspense, lazy } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider } from "@/context/AuthContext";
import { LocaleProvider } from "@/context/LocaleContext";
import { ThemeProvider } from "@/context/ThemeContext";
import { HelpProvider } from "@/help/HelpContext";
import ProtectedRoute from "@/components/ProtectedRoute";
import Layout from "@/components/Layout";

/* Auth + shell stay eager for fast first interaction after login */
import Login from "@/pages/Login";
import Register from "@/pages/Register";
import ForgotPassword from "@/pages/ForgotPassword";
import ResetPassword from "@/pages/ResetPassword";
import VerifyEmail from "@/pages/VerifyEmail";
import InviteAccept from "@/pages/InviteAccept";
import Onboarding from "@/pages/Onboarding";
import { PrivacyPage, TermsPage, BetaNoticePage } from "@/pages/LegalPages";

/* Marketing bundle — lazy so authenticated app code is not required on public pages */
const HomePage = lazy(() => import("@/pages/marketing/HomePage"));
const ProductIndexPage = lazy(() => import("@/pages/marketing/ProductIndexPage"));
const CopilotPage = lazy(() => import("@/pages/marketing/CopilotPage"));
const CrmPage = lazy(() => import("@/pages/marketing/CrmPage"));
const MarketingProjectsPage = lazy(() => import("@/pages/marketing/ProjectsPage"));
const MarketingAutomationsPage = lazy(() => import("@/pages/marketing/AutomationsPage"));
const MarketingDocumentsPage = lazy(() => import("@/pages/marketing/DocumentsPage"));
const PricingPage = lazy(() => import("@/pages/marketing/PricingPage"));
const FaqPage = lazy(() => import("@/pages/marketing/FaqPage"));
const SecurityPage = lazy(() => import("@/pages/marketing/SecurityPage"));
const SolutionsPage = lazy(() => import("@/pages/marketing/SolutionsPage"));
const ProductDetailPage = lazy(() => import("@/pages/marketing/ProductDetailPage"));

/* Authenticated app pages — lazy for route-level code splitting */
const Dashboard = lazy(() => import("@/pages/Dashboard"));
const Clients = lazy(() => import("@/pages/Clients"));
const Projects = lazy(() => import("@/pages/Projects"));
const ProjectWorkspace = lazy(() => import("@/pages/ProjectWorkspace"));
const Tasks = lazy(() => import("@/pages/Tasks"));
const AIChat = lazy(() => import("@/pages/AIChat"));
const AICopilot = lazy(() => import("@/pages/AICopilot"));
const AIAgents = lazy(() => import("@/pages/AIAgents"));
const Proposals = lazy(() => import("@/pages/Proposals"));
const Contracts = lazy(() => import("@/pages/Contracts"));
const Invoices = lazy(() => import("@/pages/Invoices"));
const Documents = lazy(() => import("@/pages/Documents"));
const Analytics = lazy(() => import("@/pages/Analytics"));
const Settings = lazy(() => import("@/pages/Settings"));
const AIWorkspace = lazy(() => import("@/pages/AIWorkspace"));
const Opportunities = lazy(() => import("@/pages/Opportunities"));
const CRM = lazy(() => import("@/pages/CRM"));
const ContactDetail = lazy(() => import("@/pages/ContactDetail"));
const Pipeline = lazy(() => import("@/pages/Pipeline"));
const KnowledgeBrain = lazy(() => import("@/pages/KnowledgeBrain"));
const Automations = lazy(() => import("@/pages/Automations"));
const EmailCenter = lazy(() => import("@/pages/EmailCenter"));
const Integrations = lazy(() => import("@/pages/Integrations"));
const Inbox = lazy(() => import("@/pages/Inbox"));

function RouteFallback() {
  return (
    <div className="flex min-h-[40vh] items-center justify-center text-sm text-zinc-500" role="status">
      Loading…
    </div>
  );
}

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <AuthProvider>
          <LocaleProvider>
            <ThemeProvider>
            <HelpProvider>
              <Suspense fallback={<RouteFallback />}>
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
              </Suspense>
            </HelpProvider>
            </ThemeProvider>
          </LocaleProvider>
        </AuthProvider>
      </BrowserRouter>
      <Toaster position="bottom-right" theme="system" />
    </div>
  );
}

export default App;
