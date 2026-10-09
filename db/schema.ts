import { pgTable, serial, text, timestamp, uuid, index } from "drizzle-orm/pg-core";

export const sessions = pgTable(
  "sessions",
  {
    id: uuid().primaryKey().defaultRandom(),
    clientId: text("client_id").notNull(),
    title: text().notNull().default("New chat"),
    model: text().notNull(),
    createdAt: timestamp("created_at").notNull().defaultNow(),
    updatedAt: timestamp("updated_at").notNull().defaultNow(),
  },
  (t) => [index("sessions_client_idx").on(t.clientId, t.updatedAt)],
);

export const messages = pgTable(
  "messages",
  {
    id: serial().primaryKey(),
    sessionId: uuid("session_id")
      .notNull()
      .references(() => sessions.id, { onDelete: "cascade" }),
    role: text().notNull(),
    content: text().notNull(),
    createdAt: timestamp("created_at").notNull().defaultNow(),
  },
  (t) => [index("messages_session_idx").on(t.sessionId, t.id)],
);
