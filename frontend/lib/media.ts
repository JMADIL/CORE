import type { ThoughtNode } from "../types/chat";

export interface GeneratedImage { url: string; }
export interface GeneratedMedia { url: string; kind: "image" | "audio"; generationId?: string; }

/** Ignore expiring authorization, while preserving file/transform parameters. */
export function imageIdentity(value: string): string {
  try {
    const url = new URL(value);
    url.hash = "";
    for (const key of [...url.searchParams.keys()]) {
      if (/^(signature|expires|expiration|token|policy|keyname|key-pair-id|x-amz-.+|x-goog-.+)$/i.test(key)) url.searchParams.delete(key);
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
export function uniqueImagePreviews(options: { sources: string[]; imageContext: boolean; authoritative?: boolean }) {
  return (tree: MediaNode) => {
    const seen = new Set(options.sources.map(imageIdentity));
    function visit(node: MediaNode) {
      if (!node.children) return;
      node.children = node.children.flatMap(child => {
        const source = child.tagName === "img" ? child.properties?.src : child.properties?.href;
        if (child.tagName === "img" && typeof source === "string") {
          const id = imageIdentity(source);
          if (options.authoritative || seen.has(id)) return [];
          seen.add(id);
        } else if (child.tagName === "a" && typeof source === "string" && imageLink(source, options.imageContext)) {
          const id = imageIdentity(source);
          if (!options.authoritative && !seen.has(id)) {
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

/** Extract completed provider files by generation ID, with URL identity as fallback. */
export function generatedMedia(thoughts: ThoughtNode[]): GeneratedMedia[] {
  const media = new Map<string, GeneratedMedia>();
  const urls = new Map<string, string>();
  let context: GeneratedMedia["kind"] | undefined;
  function visit(value: unknown, inherited: GeneratedMedia["kind"] | undefined, depth = 0) {
    if (!value || typeof value !== "object" || depth > 8) return;
    if (Array.isArray(value)) { value.forEach(row => visit(row, inherited, depth + 1)); return; }
    const row = value as Record<string, unknown>;
    if (["failed", "pending", "generating"].includes(String(row.status))) return;
    if (row.type === "text" && typeof row.text === "string") {
      try { visit(JSON.parse(row.text), inherited, depth + 1); } catch { /* Ordinary MCP text. */ }
      return;
    }
    const mime = row.content_mime_type ?? row.mime_type ?? row.mimeType ?? row.content_type;
    const type = row.media_type ?? row.modality ?? row.kind ?? row.type;
    const kind = typeof mime === "string"
      ? mime.startsWith("image/") ? "image" : mime.startsWith("audio/") ? "audio" : undefined
      : type === "audio" || type === "image" ? type : inherited;
    for (const field of ["master_url", "content_url", "image_url", "audio_url", "download_url", "url"]) {
      const url = row[field];
      if (typeof url !== "string") continue;
      try {
        const parsed = new URL(url);
        if (parsed.protocol !== "https:" || parsed.username || parsed.password || parsed.hostname === "elevenlabs.io" || parsed.hostname.endsWith(".elevenlabs.io")) continue;
        const inferred = kind ?? (field === "image_url" ? "image" : field === "audio_url" ? "audio" : imageLink(url) ? "image" : /\.(mp3|wav|ogg|m4a|aac|flac)$/i.test(parsed.pathname) ? "audio" : undefined);
        const file = field !== "url" || imageLink(url, inferred === "image") || (inferred === "audio" && (/\.(mp3|wav|ogg|m4a|aac|flac)$/i.test(parsed.pathname) || parsed.hostname.endsWith(".elevenlabsusercontent.com")));
        if (!inferred || !file) continue;
        const generationId = typeof row.generation_id === "string" ? row.generation_id : typeof row.id === "string" ? row.id : undefined;
        const identity = imageIdentity(url);
        const key = generationId ? `${inferred}:generation:${generationId}` : urls.get(identity) ?? `${inferred}:file:${identity}`;
        const previousKey = urls.get(identity);
        if (previousKey && previousKey !== key) media.delete(previousKey);
        urls.set(identity, key);
        media.set(key, {url, kind: inferred, ...(generationId ? {generationId} : {})});
        break;
      } catch { /* Ignore malformed file URLs. */ }
    }
    for (const key of ["generations", "results", "media", "outputs", "content", "data", "result", "files", "artifacts", "assets"]) visit(row[key], kind, depth + 1);
  }
  for (const thought of thoughts) {
    if (!thought.name.startsWith("elevenlabs_")) continue;
    if (/creative_(generate|edit)_image$/.test(thought.name)) context = "image";
    else if (/creative_generate_speech$/.test(thought.name)) context = "audio";
    else if (/creative_generate_video$/.test(thought.name)) context = undefined;
    if (thought.type !== "tool_result" || !thought.output) continue;
    try { visit(JSON.parse(thought.output), context); } catch { /* Non-JSON tool text. */ }
  }
  return [...media.values()].slice(0, 8);
}

export function generatedImages(thoughts: ThoughtNode[]): GeneratedImage[] {
  return generatedMedia(thoughts).filter(media => media.kind === "image").map(({url}) => ({url}));
}
