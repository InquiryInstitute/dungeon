// Supabase Edge Function: invoke Vertex AI (Gemini) as the Tomb of Horrors DM.
// Requires secrets: VERTEX_PROJECT_ID, VERTEX_LOCATION, VERTEX_SERVICE_ACCOUNT_JSON

import { create } from "https://deno.land/x/djwt@v3.0.2/mod.ts";

const VERTEX_SCOPE = "https://www.googleapis.com/auth/cloud-platform";

function getEnv(name: string): string {
  const v = Deno.env.get(name);
  if (!v) throw new Error(`Missing env: ${name}`);
  return v;
}

async function getGoogleAccessToken(): Promise<string> {
  const raw = getEnv("VERTEX_SERVICE_ACCOUNT_JSON");
  let key: Record<string, string>;
  try {
    key = JSON.parse(raw) as Record<string, string>;
  } catch {
    throw new Error("VERTEX_SERVICE_ACCOUNT_JSON is invalid JSON");
  }
  const clientEmail = key.client_email;
  const privateKeyPem = key.private_key;
  if (!clientEmail || !privateKeyPem) {
    throw new Error("Service account JSON must include client_email and private_key");
  }

  const now = Math.floor(Date.now() / 1000);
  const payload = {
    iss: clientEmail,
    sub: clientEmail,
    aud: "https://oauth2.googleapis.com/token",
    iat: now,
    exp: now + 3600,
    scope: VERTEX_SCOPE,
  };

  const pemContents = privateKeyPem
    .replace(/-----BEGIN PRIVATE KEY-----/, "")
    .replace(/-----END PRIVATE KEY-----/, "")
    .replace(/\s/g, "");
  const binaryKey = Uint8Array.from(atob(pemContents), (c) => c.charCodeAt(0));

  let cryptoKey: CryptoKey;
  try {
    cryptoKey = await crypto.subtle.importKey(
      "pkcs8",
      binaryKey,
      { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" },
      false,
      ["sign"]
    );
  } catch (e) {
    throw new Error("Failed to import private key: " + (e?.message ?? String(e)));
  }

  const jwt = await create(
    { alg: "RS256", typ: "JWT" },
    payload,
    cryptoKey
  );

  const tokenRes = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "urn:ietf:params:oauth:grant-type:jwt-bearer",
      assertion: jwt,
    }),
  });
  if (!tokenRes.ok) {
    const t = await tokenRes.text();
    throw new Error(`Google token error: ${tokenRes.status} ${t}`);
  }
  const tokenData = (await tokenRes.json()) as { access_token?: string };
  if (!tokenData.access_token) throw new Error("No access_token in response");
  return tokenData.access_token;
}

function vertexRole(role: string): "user" | "model" {
  return role === "dm" || role === "model" ? "model" : "user";
}

Deno.serve(async (req) => {
  const corsHeaders = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
  };

  if (req.method === "OPTIONS") {
    return new Response(null, { headers: corsHeaders });
  }

  if (req.method !== "POST") {
    return new Response(JSON.stringify({ error: "Method not allowed" }), {
      status: 405,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  let body: { messages?: { role: string; content: string }[]; moduleContext?: string };
  try {
    body = (await req.json()) as typeof body;
  } catch {
    return new Response(
      JSON.stringify({ error: "Invalid JSON body" }),
      { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }

  const messages = body.messages ?? [];
  const moduleContext = body.moduleContext ?? "";

  const systemInstruction = `You are the Dungeon Master for the classic module "Tomb of Horrors" (S1)—the labyrinthine crypt of the demi-lich Acererak. You speak in first person as the DM. You describe only what the players would see, hear, and know; you never reveal traps, secret doors, or mechanics. Keep responses concise and atmospheric (a few short paragraphs at most). Stay in character.

Use the following module text only to inform your descriptions and rulings. Do not quote it verbatim; narrate as the DM.

<module>
${moduleContext.slice(0, 28000)}
</module>`;

  const contents = messages.map((m) => ({
    role: vertexRole(m.role),
    parts: [{ text: m.content }],
  }));

  const projectId = getEnv("VERTEX_PROJECT_ID");
  const location = getEnv("VERTEX_LOCATION");
  const modelId = "gemini-1.5-flash";
  const url = `https://${location}-aiplatform.googleapis.com/v1/projects/${projectId}/locations/${location}/publishers/google/models/${modelId}:generateContent`;

  let accessToken: string;
  try {
    accessToken = await getGoogleAccessToken();
  } catch (e) {
    console.error(e);
    return new Response(
      JSON.stringify({ error: "Vertex auth failed", detail: String(e) }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }

  const vertexBody = {
    contents,
    systemInstruction: {
      role: "user",
      parts: [{ text: systemInstruction }],
    },
    generationConfig: {
      maxOutputTokens: 1024,
      temperature: 0.7,
    },
  };

  const vertexRes = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify(vertexBody),
  });

  if (!vertexRes.ok) {
    const errText = await vertexRes.text();
    console.error("Vertex API error:", vertexRes.status, errText);
    return new Response(
      JSON.stringify({ error: "Vertex API error", detail: errText.slice(0, 500) }),
      { status: 502, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }

  const vertexData = (await vertexRes.json()) as {
    candidates?: { content?: { parts?: { text?: string }[] } }[];
  };
  const parts = vertexData.candidates?.[0]?.content?.parts ?? [];
  const text = parts.map((p) => p.text ?? "").join("").trim() || "(No response.)";

  return new Response(JSON.stringify({ content: text }), {
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
});
