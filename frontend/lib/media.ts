import type { ThoughtNode } from "../types/chat";

export interface GeneratedImage { url: string; }

/** Ignore expiring authorization, while preserving file/transform parameters. */
export function imageIdentity(value: string): string {
  try {
    const url = new URL(value);
    url.hash = "";
    for (const key of [...url.searchParams.keys()]) {
      if (/^(signature|expires|expiration|token|policy|key-pair-id|x-amz-.+|x-goog-.+)$/i.test(key)) url.searchParams.delete(key);
    }
    url.searchParams.sort();
    return url.href;
  } catch { return value; }
}

interface MediaNode {
  type: string;
  tagName?: string;
  properties?: Record<string, unknown>;
  children?: MediaNode[];
}

/** Give tool results and Markdown one preview per file, including plain links. */
export function uniqueImagePreviews(options: { sources: string[]; imageContext: boolean }) {
  return (tree: MediaNode) => {
    const seen = new Set(options.sources.map(imageIdentity));
    function visit(node: MediaNode) {
      if (!node.children) return;
      node.children = node.children.flatMap(child => {
        const source = child.tagName === "img" ? child.properties?.src : child.properties?.href;
        if (child.tagName === "img" && typeof source === "string") {
          const id = imageIdentity(source);
          if (seen.has(id)) return [];
          seen.add(id);
        } else if (child.tagName === "a" && typeof source === "string" && imageLink(source, options.imageContext)) {
          const id = imageIdentity(source);
          if (!seen.has(id)) {
            seen.add(id);
            return [{type: "element", tagName: "img", properties: {src: source, alt: "Generated image"}}];
          }
        }
        visit(child);
        return [child];
      });
    }
    visit(tree);
  };
}

export function imageLink(value: string, imageContext = false): boolean {
  try {
    const url = new URL(value);
    if (url.protocol !== "https:" || url.username || url.password) return false;
    const contentHost = url.hostname === "elevenlabsusercontent.com" || url.hostname.endsWith(".elevenlabsusercontent.com");
    return /\.(png|jpe?g|webp|gif|avif)(?:$)/i.test(url.pathname) || (imageContext && contentHost);
  } catch { return false; }
}

/** Read actual file results, never canvas links or URLs buried in prompts. */
export function generatedImages(thoughts: ThoughtNode[]): GeneratedImage[] {
  const images = new Map<string, string>();
  const imageRun = thoughts.some(t => t.type === "tool_call" && /elevenlabs_creative_(generate|edit)_image$/.test(t.name));
  function visit(value: unknown, imageContext: boolean, depth = 0) {
    if (!value || typeof value !== "object" || depth > 8) return;
    if (Array.isArray(value)) { value.forEach(row => visit(row, imageContext, depth + 1)); return; }
    const row = value as Record<string, unknown>;
    if (row.status === "failed" || row.status === "pending" || row.status === "generating") return;
    if (row.type === "text" && typeof row.text === "string") {
      try { visit(JSON.parse(row.text), imageContext, depth + 1); } catch { /* Non-JSON tool text. */ }
      return;
    }
    const mime = row.content_mime_type ?? row.mime_type ?? row.mimeType;
    const isImage = typeof mime === "string" ? mime.startsWith("image/") : imageContext || row.type === "image" || row.media_type === "image";
    for (const key of ["content_url", "image_url", "download_url", "url"]) {
      const url = row[key];
      if (typeof url !== "string") continue;
      const typedFile = key !== "url" && isImage;
      try {
        const parsed = new URL(url);
        const canvas = parsed.hostname === "elevenlabs.io" || parsed.hostname.endsWith(".elevenlabs.io");
        if (!canvas && parsed.protocol === "https:" && !parsed.username && !parsed.password && (typedFile || imageLink(url, isImage))) {
          images.set(imageIdentity(url), url);
          // The remaining URL fields may be download/thumbnail aliases for this file.
          break;
        }
      } catch { /* Ignore malformed provider URLs. */ }
    }
    for (const key of ["generations", "results", "media", "outputs", "content", "data", "result"]) visit(row[key], isImage, depth + 1);
  }
  for (const thought of thoughts) {
    if (thought.type !== "tool_result" || !thought.name.startsWith("elevenlabs_") || !thought.output) continue;
    try { visit(JSON.parse(thought.output), imageRun); } catch { /* Ordinary tool explanations contain no media. */ }
  }
  return [...images.values()].slice(0, 8).map(url => ({ url }));
}
