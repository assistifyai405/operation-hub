import { useEffect } from "react";

/** Inject JSON-LD structured data. Caller must pass truthful data only. */
export default function JsonLd({ data }) {
  useEffect(() => {
    if (!data) return undefined;
    const id = "assistify-jsonld";
    let el = document.getElementById(id);
    if (!el) {
      el = document.createElement("script");
      el.type = "application/ld+json";
      el.id = id;
      document.head.appendChild(el);
    }
    el.textContent = JSON.stringify(data);
    return () => {
      const node = document.getElementById(id);
      if (node) node.remove();
    };
  }, [data]);
  return null;
}
