# Deploy

## GitHub Pages (site + DM chat)

Already set up: push to `main` runs the workflow and deploys to **dungeon.castalia.institute**.

```bash
git push origin main
```

Then open https://dungeon.castalia.institute/dm.html .

---

## Supabase Edge Function (Gemini DM)

To have the DM use Vertex AI (Gemini) instead of the fallback:

1. **Create/link a Supabase project**
   - [Supabase Dashboard](https://supabase.com/dashboard) → New project (or use existing).
   - Note the **Project URL** (e.g. `https://abcdefgh.supabase.co`) and **anon key** (Settings → API).

2. **Link the repo and deploy the function**
   ```bash
   cd /path/to/dungeon
   supabase link --project-ref YOUR_PROJECT_REF
   supabase functions deploy dm-invoke
   ```
   `YOUR_PROJECT_REF` is the short id in your project URL (e.g. `abcdefgh`).

3. **Set Edge Function secrets** (Dashboard → Project Settings → Edge Functions → Secrets)
   - `VERTEX_PROJECT_ID` — Google Cloud project ID
   - `VERTEX_LOCATION` — e.g. `us-central1`
   - `VERTEX_SERVICE_ACCOUNT_JSON` — full JSON key for a service account with Vertex AI User role

4. **Point the DM at Supabase**  
   In `dm.html` (or via a config file you load before the app), set:
   ```js
   window.DM_CONFIG = {
     supabaseUrl: 'https://YOUR_PROJECT_REF.supabase.co',
     supabaseAnonKey: 'YOUR_ANON_KEY'
   };
   ```
   Then redeploy the site (e.g. push to `main`) or serve locally.

After that, the chat will call the Edge Function and Gemini will run the DM.
