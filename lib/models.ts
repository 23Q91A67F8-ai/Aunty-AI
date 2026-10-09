export type Provider = "anthropic" | "openai" | "gemini";

export const MODELS: Record<string, { provider: Provider; name: string }> = {
  "claude-sonnet-5-5": { provider: "anthropic", name: "Claude Sonnet 5.5" },
  "claude-opus-5-5": { provider: "anthropic", name: "Claude Opus 5.5" },
  "claude-haiku-5-5": { provider: "anthropic", name: "Claude Haiku 5.5 (fast)" },
  "gpt-5.5": { provider: "openai", name: "GPT-5.5" },
  "gpt-5.4-mini": { provider: "openai", name: "GPT-5.4 mini (fast)" },
  "gemini-3.5-flash": { provider: "gemini", name: "Gemini 3.5 Flash" },
};

export const DEFAULT_MODEL = "claude-sonnet-5-5";
