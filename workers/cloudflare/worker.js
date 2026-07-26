/**
 * Cloudflare Worker — AI gateway + webhook receiver.
 *
 * Deploy:
 *   wrangler deploy workers/cloudflare/worker.js --name ai-startup-gateway
 *
 * Config (wrangler.toml or env):
 *   TELEGRAM_BOT_TOKEN, TELEGRAM_WEBHOOK_SECRET, BACKEND_URL
 */

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    if (url.pathname === "/webhook/telegram" && request.method === "POST") {
      return handleTelegram(request, env);
    }
    if (url.pathname === "/ai" && request.method === "POST") {
      return handleAI(request, env);
    }
    if (url.pathname === "/health") {
      return new Response("OK", { status: 200 });
    }
    return new Response("Not found", { status: 404 });
  },
};

async function handleTelegram(request, env) {
  const secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token");
  if (secret !== env.TELEGRAM_WEBHOOK_SECRET) {
    return new Response("Unauthorized", { status: 401 });
  }
  const update = await request.json();
  // Forward to backend
  const resp = await fetch(`${env.BACKEND_URL}/internal/telegram`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(update),
  });
  return new Response("OK", { status: 200 });
}

async function handleAI(request, env) {
  const body = await request.json();
  const prompt = body.prompt || "";

  // Use Workers AI for fast inference
  const response = await env.AI.run("@cf/meta/llama-3.1-8b-instruct", {
    messages: [
      { role: "system", content: "You are a helpful AI assistant." },
      { role: "user", content: prompt },
    ],
  });
  return Response.json({ result: response });
}
