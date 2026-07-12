import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export function Markdown({ children }) {
  return (
    <div className="assistant-md text-sm leading-relaxed text-zinc-200">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: (p) => <h1 className="mb-2 mt-3 text-base font-bold text-zinc-50" {...p} />,
          h2: (p) => <h2 className="mb-1.5 mt-3 text-sm font-bold text-zinc-100" {...p} />,
          h3: (p) => <h3 className="mb-1 mt-2 text-sm font-semibold text-zinc-100" {...p} />,
          p: (p) => <p className="mb-2 last:mb-0" {...p} />,
          ul: (p) => <ul className="mb-2 ml-1 space-y-1" {...p} />,
          ol: (p) => <ol className="mb-2 ml-4 list-decimal space-y-1" {...p} />,
          li: ({ children, ...rest }) => (
            <li className="flex gap-2" {...rest}><span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-violet-400" /><span className="min-w-0">{children}</span></li>
          ),
          strong: (p) => <strong className="font-semibold text-zinc-50" {...p} />,
          a: (p) => <a className="text-violet-300 underline underline-offset-2 hover:text-violet-200" target="_blank" rel="noreferrer" {...p} />,
          code: ({ inline, children, ...rest }) =>
            inline
              ? <code className="rounded bg-zinc-800 px-1 py-0.5 text-[12px] text-violet-200" {...rest}>{children}</code>
              : <code className="block overflow-x-auto rounded-lg border border-white/10 bg-zinc-900 p-3 text-[12px] text-zinc-200" {...rest}>{children}</code>,
          pre: (p) => <pre className="mb-2" {...p} />,
          blockquote: (p) => <blockquote className="border-l-2 border-violet-500/50 pl-3 text-zinc-400" {...p} />,
          table: (p) => <div className="mb-2 overflow-x-auto"><table className="w-full border-collapse text-xs" {...p} /></div>,
          th: (p) => <th className="border border-white/10 bg-zinc-900 px-2 py-1 text-left font-semibold text-zinc-200" {...p} />,
          td: (p) => <td className="border border-white/10 px-2 py-1 text-zinc-300" {...p} />,
        }}
      >
        {children || ""}
      </ReactMarkdown>
    </div>
  );
}
