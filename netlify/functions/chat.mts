import type { Config } from "@netlify/functions";
import Anthropic from "@anthropic-ai/sdk";
import OpenAI from "openai";
import { GoogleGenAI } from "@google/genai";
import { and, asc, eq } from "drizzle-orm";
import { db } from "../../db/index.js";
import { messages, sessions } from "../../db/schema.js";
import { MODELS } from "../../lib/models.js";

const SYSTEM_PROMPT =
  "You are aunty.ai, an expert software engineering assistant optimized for long-horizon multi-step coding tasks. " +
  "Give precise, practical answers. When you reference project code, cite file paths. Use Markdown with fenced code blocks.";

const UUID_RE = /^[0-9a-f-]{36}$/i;
const MAX_CONTEXT_CHARS = 400_000;
const MAX_HISTORY = 40;
const MAX_IMAGES = 4;

type Turn = { role: "user" | "assistant"; content: string };
type Image = { mediaType: string; data: string };

function parseImages(input: unknown): Image[] {
  if (!Array.isArray(input)) return [];
  const out: Image[] = [];
  for (const url of input.slice(0, MAX_IMAGES)) {
    const m = typeof url === "string" && url.match(/^data:(image\/(?:png|jpeg|gif|webp));base64,(.+)$/);
    if (m) out.push({ mediaType: m[1], data: m[2] });
  }
  return out;
}

async function* streamAnthropic(model: string, system: string, turns: Turn[], images: Image[]) {
  const client = new Anthropic();
  const msgs: Anthropic.MessageParam[] = turns.map((t) => ({ role: t.role, content: t.content }));
  if (images.length) {
    const last = msgs[msgs.length - 1];
    last.content = [
      ...images.map((img) => ({
        type: "image" as const,
        source: { type: "base64" as const, media_type: img.mediaType as "image/png", data: img.data },
      })),
      { type: "text" as const, text: last.content as string },
    ];
  }
  const stream = await client.messages.create({ model, system, max_tokens: 16000, messages: msgs, stream: true });
  for await (const event of stream) {
    if (event.type === "content_block_delta" && event.delta.type === "text_delta") yield event.delta.text;
  }
}

async function* streamOpenAI(model: string, system: string, turns: Turn[], images: Image[]) {
  const client = new OpenAI();
  const msgs: OpenAI.Chat.ChatCompletionMessageParam[] = [
    { role: "system", content: system },
    ...turns.map((t) => ({ role: t.role, content: t.content }) as OpenAI.Chat.ChatCompletionMessageParam),
  ];
  if (images.length) {
    const last = msgs[msgs.length - 1] as OpenAI.Chat.ChatCompletionUserMessageParam;
    last.content = [
      { type: "text", text: last.content as string },
      ...images.map((img) => ({
        type: "image_url" as const,
        image_url: { url: `data:${img.mediaType};base64,${img.data}` },
      })),
    ];
  }
  const stream = await client.chat.completions.create({ model, messages: msgs, stream: true });
  for await (const chunk of stream) {
    const text = chunk.choices[0]?.delta?.content;
    if (text) yield text;
  }
}

async function* streamGemini(model: string, system: string, turns: Turn[], images: Image[]) {
  const ai = new GoogleGenAI({});
  const contents = turns.map((t) => ({
    role: t.role === "assistant" ? "model" : "user",
    parts: [{ text: t.content }] as Array<Record<string, unknown>>,
  }));
  if (images.length) {
    contents[contents.length - 1].parts.unshift(
      ...images.map((img) => ({ inlineData: { mimeType: img.mediaType, data: img.data } })),
    );
  }
  const stream = await ai.models.generateContentStream({ model, contents, config: { systemInstruction: system } });
  for await (const chunk of stream) {
    if (chunk.text) yield chunk.text;
  }
}

export default async (req: Request) => {
  if (req.method !== "POST") return new Response("Method not allowed", { status: 405 });

  const clientId = req.headers.get("x-client-id") ?? "";
  const body = await req.json().catch(() => null);
  if (!UUID_RE.test(clientId) || !body || !UUID_RE.test(body.sessionId ?? "")) {
    return Response.json({ error: "Invalid request" }, { status: 400 });
  }

  const text = String(body.message ?? "").trim();
  const images = parseImages(body.images);
  if (!text && !images.length) return Response.json({ error: "Message is empty" }, { status: 400 });

  const [session] = await db
    .select()
    .from(sessions)
    .where(and(eq(sessions.id, body.sessionId), eq(sessions.clientId, clientId)));
  if (!session) return Response.json({ error: "Session not found" }, { status: 404 });

  const modelId = MODELS[body.model] ? body.model : session.model;
  const provider = MODELS[modelId].provider;

  const history = await db
    .select({ role: messages.role, content: messages.content })
    .from(messages)
    .where(eq(messages.sessionId, session.id))
    .orderBy(asc(messages.id));

  const userContent = text || "(see attached image)";
  const storedContent = images.length ? `${userContent}\n\n_[${images.length} image(s) attached]_` : userContent;

  await db.insert(messages).values({ sessionId: session.id, role: "user", content: storedContent });
  const isFirst = history.length === 0;
  await db
    .update(sessions)
    .set({
      model: modelId,
      updatedAt: new Date(),
      ...(isFirst && session.title === "New chat" ? { title: userContent.replace(/\s+/g, " ").slice(0, 60) } : {}),
    })
    .where(eq(sessions.id, session.id));

  let system = SYSTEM_PROMPT;
  const workspace = typeof body.context === "string" ? body.context.slice(0, MAX_CONTEXT_CHARS) : "";
  if (workspace) system += `\n\nWorkspace Context:\n${workspace}`;

  // Providers require alternating turns starting with the user, so merge consecutive same-role turns
  const turns: Turn[] = [];
  for (const m of [...history.slice(-MAX_HISTORY), { role: "user", content: userContent }]) {
    const role = m.role === "assistant" ? "assistant" : "user";
    const prev = turns[turns.length - 1];
    if (prev?.role === role) prev.content += `\n\n${m.content}`;
    else if (turns.length || role === "user") turns.push({ role, content: m.content });
  }

  const generator =
    provider === "anthropic"
      ? streamAnthropic(modelId, system, turns, images)
      : provider === "openai"
        ? streamOpenAI(modelId, system, turns, images)
        : streamGemini(modelId, system, turns, images);

  const encoder = new TextEncoder();
  return new Response(
    new ReadableStream({
      async start(controller) {
        let reply = "";
        try {
          for await (const chunk of generator) {
            reply += chunk;
            controller.enqueue(encoder.encode(chunk));
          }
        } catch (err) {
          console.error("Model request failed", err);
          const note = `\n\n**Error:** the model request failed (${err instanceof Error ? err.message : "unknown error"}).`;
          reply += note;
          controller.enqueue(encoder.encode(note));
        }
        if (reply.trim()) {
          await db.insert(messages).values({ sessionId: session.id, role: "assistant", content: reply });
          await db.update(sessions).set({ updatedAt: new Date() }).where(eq(sessions.id, session.id));
        }
        controller.close();
      },
    }),
    { headers: { "Content-Type": "text/plain; charset=utf-8", "Cache-Control": "no-cache" } },
  );
};

export const config: Config = {
  path: "/api/chat",
};
