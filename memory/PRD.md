# Assistify OS — PRD

## Original Problem Statement
Build a premium AI business operating system called Assistify OS — an all-in-one dark-theme SaaS platform for entrepreneurs to manage clients, projects, AI agents, proposals, documents, tasks and operations. Pages: Login, Dashboard, Clients, Projects, Tasks, AI Chat, AI Agents, Proposals, Documents, Analytics, Settings. Design inspired by Linear, Notion, Stripe, Vercel — dark theme, electric violet accent, rounded cards, smooth animations, fully responsive.

## User Choices
- Real AI integration for AI Chat & AI Agents (Emergent LLM key, OpenAI gpt-5.4, streaming)
- Clean & geometric typography → Outfit font
- Electric violet accent (Linear-style)
- Static login → routes to dashboard (no real auth)

## Architecture
- Frontend: React 19 + React Router 7, Tailwind, shadcn/ui, Recharts, lucide-react. Fixed sidebar layout + glass header.
- Backend: FastAPI + MongoDB. Endpoints: GET /api/agents, POST /api/chat/stream (SSE streaming via emergentintegrations), GET /api/chat/history/{session_id}. Chat messages persisted in MongoDB.
- LLM: emergentintegrations LlmChat, model openai/gpt-5.4, EMERGENT_LLM_KEY.

## User Personas
- Solo founders / agency owners managing multiple clients and projects who want AI leverage.

## Implemented (2026-06)
- AI Proposal Writer ("Proposal" tab in every Project Workspace): auto-uses full project context (client, project, AI Planner, notes, documents, tasks, timeline) to generate 15 editable client-facing sections via a provider-agnostic AI service layer (ai_service.py) with prompts in config (proposal_config.py). Header (editable name, status, version, last generated) + Generate/Save/Regenerate/Version History/Export PDF/Export DOCX. New ai_proposals MongoDB collection (title, projectId, clientId, status, content, version, history, timestamps) with restore + side-by-side compare. Real server-side PDF (reportlab) & DOCX (python-docx) exports. Statuses Draft/Generated/Sent/Accepted/Rejected/Archived. Logs proposal_generated/saved/exported. Cascade-deletes with project. Verified iteration_8 (backend 16/16, frontend 100%, existing features untouched).
- AI Project Planner ("AI Planner" tab in every Project Workspace): analyzes full project context (client, description, notes, tasks, documents, timeline, status) via gpt-5.4 and generates 9 structured sections (Executive Summary, Business Goal, Technical Requirements, Recommended Plan, Milestones, Suggested Tasks, Estimated Timeline, Risks, Next Actions). Generate/Regenerate, edit-before-save, version history with timestamps saved to MongoDB (plans collection), side-by-side version compare, and Export to PDF (print window). Plans cascade-delete with project; saving logs a plan_generated activity. Verified iteration_6/7 (backend 6/6, frontend 100% after activity-refresh fix).
- Project Workspace at /projects/:id with 7 tabs (Overview, AI Chat, Tasks, Documents, Proposals, Notes, Activity Timeline). Per-project AI chat with persisted, isolated history (session_id=project-<id>). Auto-logged activity timeline (project/task created, task completed, proposal generated, document uploaded). New collections: documents, proposals, activities; projects gained description+notes; project delete cascades docs/proposals/activities. Verified iteration_5 (31/31 backend + all frontend, incl. chat isolation).
- Dashboard wired to live CRUD data: real counts (Total Clients, Active Projects, Open Tasks, Completed Tasks), latest 5 clients, next 5 open tasks (sorted by due), live Projects-by-Status pie, loading + empty states, clickable stat cards. Revenue & AI-activity charts remain placeholder. Verified iteration_4 (100%).
- CRUD persistence (MongoDB) for Clients, Projects, Tasks with modals, validation, empty states, delete confirms. Projects link to Clients; Tasks link to Projects. Deleting a parent unlinks children. Backend enriches list responses with client_name/project_name and client project counts. Endpoints: /api/{clients,projects,tasks} GET/POST/PUT/DELETE. Verified 24/24 backend + all frontend flows (iteration_3).
- Command Palette (Ctrl/Cmd+K) with navigation + AI quick actions (prompt prefilled into AI Chat). Verified iteration_2.
- All 11 pages with premium dark UI, electric violet theme, Outfit font, animations.
- Dashboard: revenue/stat cards, revenue area chart, projects pie, recent clients, upcoming tasks, AI agent activity bar chart, quick actions, notifications dropdown.
- Clients (table), Projects (kanban), Tasks (interactive checklist + filters), Proposals (list), Documents (grid), Analytics (4 charts), Settings (tabbed).
- AI Agents page (4 personas from backend) + AI Chat with streaming SSE and agent switcher.
- Placeholder data in frontend/src/data/mock.js.
- Verified: backend 100%, frontend 100% (testing agent iteration_1).

## Known Status
- AI Chat/Agents return live responses ONLY once the Emergent LLM key has balance. Currently $0 → returns budget error (user opted to fund later). UI flow works end-to-end.

## Backlog
- P1: Persist assistant error markers / show error toast on AI failure.
- P1: Add data-testid to kanban columns/cards.
- P2: CRUD persistence for clients/projects/tasks (currently mock).
- P2: Real auth + multi-user.
- P2: Health endpoint to verify LLM key validity.

## Next Tasks
- Fund LLM key and validate live AI chat.
- Wire real data persistence for core entities if requested.
