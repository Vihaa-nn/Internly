const LOWERCASE_WORDS = new Set([
  "and",
  "or",
  "of",
  "the",
  "a",
  "an",
  "in",
  "for",
  "at",
  "to",
  "on",
]);

function formatWord(word: string, isFirst: boolean): string {
  if (!word) return word;
  if (/^[A-Z]{2,}$/.test(word)) return word;
  if (/^[A-Z0-9]+$/.test(word) && word.length <= 5) return word;

  const lower = word.toLowerCase();
  if (!isFirst && LOWERCASE_WORDS.has(lower)) return lower;
  return lower.charAt(0).toUpperCase() + lower.slice(1);
}

/** Title-case company names, job titles, and similar user-entered labels. */
export function formatDisplayLabel(text: string): string {
  const trimmed = text.trim();
  if (!trimmed) return "";

  return trimmed
    .split(/\s+/)
    .map((word, index) => {
      if (word.includes("-")) {
        return word
          .split("-")
          .map((part, partIndex) => formatWord(part, index === 0 && partIndex === 0))
          .join("-");
      }
      return formatWord(word, index === 0);
    })
    .join(" ");
}
