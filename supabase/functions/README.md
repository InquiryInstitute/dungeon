# Edge Function: dm-invoke

Calls **Vertex AI (Gemini)** to run the Tomb of Horrors DM. The client sends the conversation history and optional module context; the function returns the model’s reply.

## Secrets (Supabase Dashboard → Project Settings → Edge Functions)

Set these so the function can authenticate to Google Cloud:

| Secret | Description |
|--------|-------------|
| `VERTEX_PROJECT_ID` | Google Cloud project ID (e.g. `my-project`) |
| `VERTEX_LOCATION` | Vertex AI region (e.g. `us-central1`) |
| `VERTEX_SERVICE_ACCOUNT_JSON` | Full contents of the service account key JSON (create in GCP Console → IAM → Service Accounts → Keys). Must include `client_email` and `private_key`. |

The service account needs the **Vertex AI User** role (or similar) so it can call `generateContent`.

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
