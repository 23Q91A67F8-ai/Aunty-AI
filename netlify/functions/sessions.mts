import type { Config, Context } from "@netlify/functions";
import { and, asc, desc, eq } from "drizzle-orm";
import { db } from "../../db/index.js";
import { messages, sessions } from "../../db/schema.js";
import { DEFAULT_MODEL, MODELS } from "../../lib/models.js";

const UUID_RE = /^[0-9a-f-]{36}$/i;

export default async (req: Request, context: Context) => {
  const clientId = req.headers.get("x-client-id") ?? "";
  if (!UUID_RE.test(clientId)) {
    return Response.json({ error: "Missing client id" }, { status: 400 });
  }

  const id = context.params.id;
  if (id && !UUID_RE.test(id)) {
    return Response.json({ error: "Invalid session id" }, { status: 400 });
  }
  const owned = id ? and(eq(sessions.id, id), eq(sessions.clientId, clientId)) : undefined;

  if (!id) {
    if (req.method === "GET") {
      const rows = await db
        .select()
        .from(sessions)
        .where(eq(sessions.clientId, clientId))
        .orderBy(desc(sessions.updatedAt))
        .limit(200);
      return Response.json(rows);
    }

    if (req.method === "POST") {
      const body = await req.json().catch(() => ({}));
      const model = MODELS[body.model] ? body.model : DEFAULT_MODEL;
      const [row] = await db
        .insert(sessions)
        .values({ clientId, model, title: String(body.title || "New chat").slice(0, 120) })
        .returning();
      return Response.json(row, { status: 201 });
    }

    return new Response("Method not allowed", { status: 405 });
  }

  const [session] = await db.select().from(sessions).where(owned);
  if (!session) {
    return Response.json({ error: "Session not found" }, { status: 404 });
  }

  if (req.method === "GET") {
    const rows = await db
      .select({ id: messages.id, role: messages.role, content: messages.content, createdAt: messages.createdAt })
      .from(messages)
      .where(eq(messages.sessionId, id))
      .orderBy(asc(messages.id));
    return Response.json({ session, messages: rows });
  }

  if (req.method === "PATCH") {
    const body = await req.json().catch(() => ({}));
    const updates: Partial<typeof sessions.$inferInsert> = {};
    if (typeof body.title === "string" && body.title.trim()) updates.title = body.title.trim().slice(0, 120);
    if (MODELS[body.model]) updates.model = body.model;
    if (Object.keys(updates).length === 0) return Response.json(session);
    const [row] = await db.update(sessions).set(updates).where(owned).returning();
    return Response.json(row);
  }

  if (req.method === "DELETE") {
    await db.delete(sessions).where(owned);
    return new Response(null, { status: 204 });
  }

  return new Response("Method not allowed", { status: 405 });
};

export const config: Config = {
  path: ["/api/sessions", "/api/sessions/:id"],
};
