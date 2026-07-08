function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function wrapComplexityExpressions(text: string): string {
  return text
    .replace(/\balpha\b/gi, "α")
    .replace(/O\((?:[^()]|\([^()]*\))*\)/g, (match) => `<code class="complexity-expr">${match}</code>`);
}

function formatInline(text: string): string {
  let out = wrapComplexityExpressions(text);
  out = out.replace(
    /\*\*(.+?)\*\*/g,
    (_, content: string) => {
      const trimmed = content.trim();
      if (/^(optimal approach|time\s*\/?\s*space complexity)/i.test(trimmed)) {
        return `<h4 class="rich-heading">${trimmed}</h4>`;
      }
      return `<strong class="rich-bold">${content}</strong>`;
    }
  );
  // Inline numbered steps: "1. Foo 2. Bar" or line breaks between steps
  out = out.replace(/(\d+)\.\s+/g, (match, num: string, offset: number) => {
    if (offset === 0) {
      return `<span class="rich-list-num">${num}.</span> `;
    }
    return `<br class="rich-step-break" /><span class="rich-list-num">${num}.</span> `;
  });
  return out.replace(/\n/g, "<br/>");
}

function formatParagraph(para: string): string {
  const lines = para.split(/\n/).filter((line) => line.trim().length > 0);
  const listLines = lines.filter((line) => /^\d+\.\s+/.test(line.trim()));

  if (listLines.length >= 2 && listLines.length === lines.length) {
    const items = lines
      .map((line) => {
        const match = line.trim().match(/^(\d+)\.\s+(.*)$/);
        if (!match) return "";
        return `<li class="rich-li">${formatInline(match[2])}</li>`;
      })
      .join("");
    return `<ol class="rich-ol">${items}</ol>`;
  }

  return `<p class="rich-para">${formatInline(para)}</p>`;
}

/** Render agent/evaluation markdown-ish text with readable complexity notation. */
export function formatRichText(text: string): string {
  if (!text.trim()) return "";

  return escapeHtml(text)
    .split(/\n\n+/)
    .map((para) => formatParagraph(para))
    .join("");
}
