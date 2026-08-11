import { useEffect } from "react";

/**
 * Lightweight SEO head updates for CRA (no react-helmet dependency).
 */
export default function SeoHead({
  title,
  description,
  canonicalPath,
  ogTitle,
  ogDescription,
  noIndex = false,
}) {
  useEffect(() => {
    const fullTitle = title ? `${title} · Assistify` : "Assistify";
    document.title = fullTitle;

    const setMeta = (selector, attr, value) => {
      if (!value) return;
      let el = document.querySelector(selector);
      if (!el) {
        el = document.createElement("meta");
        if (selector.startsWith('meta[name="')) {
          el.setAttribute("name", selector.match(/name="([^"]+)"/)[1]);
        } else if (selector.startsWith('meta[property="')) {
          el.setAttribute("property", selector.match(/property="([^"]+)"/)[1]);
        }
        document.head.appendChild(el);
      }
      el.setAttribute(attr, value);
    };

    setMeta('meta[name="description"]', "content", description || "");
    setMeta('meta[property="og:title"]', "content", ogTitle || fullTitle);
    setMeta('meta[property="og:description"]', "content", ogDescription || description || "");
    setMeta('meta[property="og:type"]', "content", "website");
    setMeta('meta[name="twitter:card"]', "content", "summary_large_image");

    let robots = document.querySelector('meta[name="robots"]');
    if (noIndex) {
      if (!robots) {
        robots = document.createElement("meta");
        robots.setAttribute("name", "robots");
        document.head.appendChild(robots);
      }
      robots.setAttribute("content", "noindex,nofollow");
    } else if (robots) {
      robots.setAttribute("content", "index,follow");
    }

    if (canonicalPath) {
      let link = document.querySelector('link[rel="canonical"]');
      if (!link) {
        link = document.createElement("link");
        link.setAttribute("rel", "canonical");
        document.head.appendChild(link);
      }
      const origin = typeof window !== "undefined" ? window.location.origin : "";
      link.setAttribute("href", `${origin}${canonicalPath}`);
    }
  }, [title, description, canonicalPath, ogTitle, ogDescription, noIndex]);

  return null;
}
