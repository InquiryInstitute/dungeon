# Edge Function: dm-invoke

Calls **Gemini** to run the Tomb of Horrors DM. The client sends the conversation history and optional module context; the function returns the model’s reply.

## Secrets (required for AI DM)

The Edge Function reads from **Supabase** Edge Function secrets (or your local `.env` via the script). Prefer the **API key** path; use Vertex only if you already have a service account with Vertex AI User.

**Preferred – API key (no IAM)**  
- `GCP_API_KEY` — API key from [Google AI Studio](https://aistudio.google.com/apikey) (Generative Language API). No project IAM or service account needed.

Set in Dashboard → Edge Functions → Secrets, or put `GCP_API_KEY` in `.env` / `.env.local` and run:

```bash
./scripts/set-supabase-vertex-secrets.sh
```

**Alternative – Vertex AI**  
- `VERTEX_PROJECT_ID`, `VERTEX_LOCATION`, `VERTEX_SERVICE_ACCOUNT_JSON` — service account must have **Vertex AI User** role. Use the same script if those are in `.env`.

## Deploy

```bash
supabase functions deploy dm-invoke
```

## Request (from dm.html)

- **Method:** `POST`
- **Headers:** `Content-Type: application/json`, `Authorization: Bearer <SUPABASE_ANON_KEY>`
- **Body:**
  ```json
  {
    "messages": [
      { "role": "dm", "content": "I run the Tomb of Horrors…" },
      { "role": "user", "content": "We search the entrance." }
    ],
    "moduleContext": "KEY TO THE TOMB\n1. FALSE ENTRANCE…"
  }
  ```
- **Response:** `{ "content": "The corridor is of plain stone…" }`
