// Supabase Edge Function: invoke Gemini as the Tomb of Horrors DM.
// Uses GCP_API_KEY (Generative Language API), same as ask-faculty.

const GEMINI_MODEL = "gemini-2.5-flash";

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization",
};

function jsonResponse(body: object, status: number) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...CORS_HEADERS, "Content-Type": "application/json" },
  });
}

function roleToGemini(role: string): "user" | "model" {
  return role === "dm" || role === "model" ? "model" : "user";
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response(null, { headers: CORS_HEADERS });
  }

  if (req.method !== "POST") {
    return jsonResponse({ error: "Method not allowed" }, 405);
  }

  try {
    let body: { messages?: { role: string; content: string }[]; moduleContext?: string };
    try {
      body = (await req.json()) as typeof body;
    } catch {
      return jsonResponse({ error: "Invalid JSON body" }, 400);
    }

    const apiKey = Deno.env.get("GCP_API_KEY")?.trim();
    if (!apiKey) {
      return jsonResponse({ error: "GCP_API_KEY not set in Edge Function secrets" }, 500);
    }

    const messages = body.messages ?? [];
    const moduleContext = body.moduleContext ?? "";

    const systemInstruction = `You are the Dungeon Master. You narrate the world and what happens in it. Speak in first person as the DM. Describe only what the characters would see, hear, and know; never reveal traps, secret doors, or game mechanics. Keep responses concise and atmospheric (a few short paragraphs at most). Stay in character.

Tell the story purely in-world. Do not mention the module, the adventure, the scenario, "this area", rulebooks, or any meta or out-of-character framing. Never say things like "in this module", "the adventure says", "area 3", or "as described in the key". Just describe the world and events as they happen.

The reference text below was extracted from a scan and may have OCR errors. Use it only to know what is in the world and what happens; interpret and rephrase in your own words so your narration is clear and natural. Do not quote it.

<reference>
${moduleContext.slice(0, 28000)}
</reference>`;

    const contents = messages.map((m) => ({
      role: roleToGemini(m.role),
      parts: [{ text: m.content }],
    }));

    const url = `https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL}:generateContent?key=${encodeURIComponent(apiKey)}`;
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        contents,
        systemInstruction: {
          role: "user",
          parts: [{ text: systemInstruction }],
        },
        generationConfig: {
          maxOutputTokens: 4096,
          temperature: 0.7,
        },
      }),
    });

    if (!res.ok) {
      const errText = await res.text();
      console.error("Gemini API error:", res.status, errText);
      return jsonResponse({ error: "Gemini API error", detail: errText.slice(0, 500) }, 502);
    }

    const data = (await res.json()) as {
      candidates?: { content?: { parts?: { text?: string }[] } }[];
    };
    const parts = data.candidates?.[0]?.content?.parts ?? [];
    const text = parts.map((p) => p.text ?? "").join("").trim() || "(No response.)";

    return jsonResponse({ content: text }, 200);
  } catch (e) {
    console.error("dm-invoke error:", e);
    return jsonResponse(
      { error: "Internal server error", detail: e instanceof Error ? e.message : String(e) },
      500
    );
  }
});
