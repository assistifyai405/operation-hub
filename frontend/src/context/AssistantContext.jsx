import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { useLocation } from "react-router-dom";

const AssistantContext = createContext(null);
export const useAssistant = () => useContext(AssistantContext);

const ROUTE_LABELS = {
  "/dashboard": "your dashboard",
  "/clients": "your clients",
  "/projects": "your projects",
  "/tasks": "your tasks",
  "/proposals": "your proposals",
  "/contracts": "your contracts",
  "/invoices": "your invoices",
  "/documents": "your documents",
  "/analytics": "your analytics",
  "/ai-workspace": "your AI workspace",
  "/ai-chat": "the Copilot",
  "/ai-agents": "your AI agents",
  "/settings": "your settings",
};

export function AssistantProvider({ children }) {
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const [pageContext, setPageContext] = useState(null); // {scope, label, entityId, entityName}
  const [docTick, setDocTick] = useState(0);            // re-render trigger when a doc registers/clears
  const docRef = useRef(null);                          // {type, name, sections, getContent, applySection}
  const undoRef = useRef(null);                         // {label, restore: () => void}

  const registerDocument = useCallback((handle) => {
    docRef.current = handle;
    setDocTick((t) => t + 1);
  }, []);
  const clearDocument = useCallback(() => {
    docRef.current = null;
    undoRef.current = null;
    setDocTick((t) => t + 1);
  }, []);

  const effectiveContext = useMemo(() => {
    void docTick;
    const doc = docRef.current;
    if (doc) {
      return { scope: "document", documentType: doc.type, entityName: doc.name,
               entityId: pageContext?.entityId || null, hasDocument: true, label: `the ${doc.name}` };
    }
    if (pageContext) return { hasDocument: false, ...pageContext };
    return { scope: "generic", hasDocument: false, label: ROUTE_LABELS[location.pathname] || "your workspace" };
    // eslint-disable-next-line
  }, [pageContext, location.pathname, docTick]);

  const buildPayload = useCallback((targetSectionKey) => {
    void docTick;
    const doc = docRef.current;
    if (doc) {
      const content = (doc.getContent && doc.getContent()) || {};
      const sections = (doc.sections || []).map((s) => ({
        key: s.key, label: s.label, type: s.type || "text", value: content[s.key],
      }));
      const payload = {
        scope: "document", documentType: doc.type, entityName: doc.name,
        entityId: pageContext?.entityId || null, sections,
      };
      if (targetSectionKey) payload.section = sections.find((s) => s.key === targetSectionKey) || null;
      return payload;
    }
    if (pageContext) {
      const { label, ...rest } = pageContext;
      return { label, ...rest };
    }
    return { scope: "generic", label: ROUTE_LABELS[location.pathname] || "your workspace" };
  }, [pageContext, location.pathname, docTick]);

  const applyChange = useCallback((apply) => {
    const doc = docRef.current;
    if (!doc || !apply) return false;
    if (apply.mode === "section" && apply.target) {
      const prev = ((doc.getContent && doc.getContent()) || {})[apply.target];
      doc.applySection(apply.target, apply.value);
      undoRef.current = { label: `1 section`, restore: () => doc.applySection(apply.target, prev) };
      return true;
    }
    if (apply.mode === "document" && apply.values) {
      const content = (doc.getContent && doc.getContent()) || {};
      const prev = {};
      Object.keys(apply.values).forEach((k) => { prev[k] = content[k]; doc.applySection(k, apply.values[k]); });
      undoRef.current = { label: `${Object.keys(apply.values).length} sections`, restore: () => Object.keys(prev).forEach((k) => doc.applySection(k, prev[k])) };
      return true;
    }
    return false;
  }, []);

  const undoLast = useCallback(() => {
    if (undoRef.current) { undoRef.current.restore(); undoRef.current = null; return true; }
    return false;
  }, []);

  const value = {
    open, setOpen,
    pageContext, setPageContext,
    registerDocument, clearDocument,
    hasDocument: !!docRef.current,
    effectiveContext,
    buildPayload, applyChange, undoLast,
  };
  return <AssistantContext.Provider value={value}>{children}</AssistantContext.Provider>;
}

// Writers call this to register the currently-open document so the assistant can
// read its sections and apply changes. Auto-clears on unmount / tab switch.
export function useAssistantDocument({ type, name, sections, content, setField, active = true }) {
  const A = useContext(AssistantContext);
  const registerDocument = A?.registerDocument;
  const clearDocument = A?.clearDocument;
  const live = useRef({});
  live.current = { content, setField };
  const keySig = (sections || []).map((s) => s.key).join(",");
  const hasContent = !!content;
  useEffect(() => {
    if (!registerDocument || !active || !hasContent || !(sections && sections.length)) return undefined;
    registerDocument({
      type, name,
      sections: sections.map((s) => ({ key: s.key, label: s.label, type: s.type || "text" })),
      getContent: () => live.current.content,
      applySection: (k, v) => live.current.setField(k, v),
    });
    return () => clearDocument && clearDocument();
    // eslint-disable-next-line
  }, [registerDocument, clearDocument, active, type, name, keySig, hasContent]);
}
