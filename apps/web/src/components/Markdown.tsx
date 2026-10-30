import { Fragment, type ReactNode } from "react";

/** Минимальный безопасный рендер markdown для текста заданий: абзацы, списки, `код`, **жирный** (без HTML). */
function inline(text: string): ReactNode[] {
  const parts = text.split(/(`[^`]+`|\*\*[^*]+\*\*)/g);
  return parts.map((p, i) => {
    if (p.startsWith("`") && p.endsWith("`") && p.length > 2) return <code key={i}>{p.slice(1, -1)}</code>;
    if (p.startsWith("**") && p.endsWith("**") && p.length > 4) return <strong key={i}>{p.slice(2, -2)}</strong>;
    return <Fragment key={i}>{p}</Fragment>;
  });
}

export function Markdown({ text }: { text: string }) {
  const blocks: ReactNode[] = [];
  const lines = text.split("\n");
  let i = 0;
  let key = 0;
  while (i < lines.length) {
    const line = lines[i] ?? "";
    if (!line.trim()) {
      i++;
    } else if (/^\d+\.\s/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\d+\.\s/.test(lines[i] ?? "")) items.push((lines[i++] ?? "").replace(/^\d+\.\s/, ""));
      blocks.push(
        <ol key={key++} className="ml-5 list-decimal space-y-2">
          {items.map((t, n) => (
            <li key={n}>{inline(t)}</li>
          ))}
        </ol>,
      );
    } else if (/^[-*]\s/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^[-*]\s/.test(lines[i] ?? "")) items.push((lines[i++] ?? "").replace(/^[-*]\s/, ""));
      blocks.push(
        <ul key={key++} className="ml-5 list-disc space-y-2">
          {items.map((t, n) => (
            <li key={n}>{inline(t)}</li>
          ))}
        </ul>,
      );
    } else {
      const para: string[] = [];
      while (i < lines.length && (lines[i] ?? "").trim() && !/^(\d+\.|[-*])\s/.test(lines[i] ?? "")) para.push(lines[i++] ?? "");
      blocks.push(<p key={key++}>{inline(para.join(" "))}</p>);
    }
  }
  return <div className="prose-task space-y-3 leading-relaxed text-slate-200">{blocks}</div>;
}
