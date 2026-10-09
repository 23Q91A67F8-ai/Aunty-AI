import type { Config } from "@netlify/functions";
import { MODELS, DEFAULT_MODEL } from "../../lib/models.js";

export default async () => {
  return Response.json({
    default: DEFAULT_MODEL,
    models: Object.entries(MODELS).map(([id, m]) => ({ id, ...m })),
  });
};

export const config: Config = {
  path: "/api/models",
};
