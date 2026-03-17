# Dungeon

**Exploring using D&D to train AI World Models.**

This project investigates how tabletop role-playing games (e.g., Dungeons & Dragons) can be used to train and evaluate AI world models—agents that maintain coherent, consistent representations of dynamic environments, narrative state, and character knowledge.

### Running the Tomb of Horrors (S1) DM

The DM is a **chat-only** page: the DM (Gemini via Vertex AI) speaks first with an intro, then you describe actions and get replies.

**Option A — With Gemini (Supabase Edge Function + Vertex AI)**

1. Create a Supabase project and deploy the Edge Function:
   ```bash
   cd supabase && supabase functions deploy dm-invoke
   ```
2. Set Edge Function secrets in Supabase Dashboard: `VERTEX_PROJECT_ID`, `VERTEX_LOCATION`, `VERTEX_SERVICE_ACCOUNT_JSON` (see `supabase/functions/README.md`).
3. In `dm.html`, set your project URL and anon key:
   ```js
   window.DM_CONFIG = { supabaseUrl: 'https://YOUR_REF.supabase.co', supabaseAnonKey: 'YOUR_ANON_KEY' };
   ```
4. Serve the site over HTTP and open `dm.html`. The chat will call the Edge Function, which uses Vertex AI (Gemini) to run the DM.

**Option B — Without backend**

If `DM_CONFIG` is not set, the DM falls back to simple area lookups: mention a number 1–33 (e.g. “we go to area 3”) to get that area’s text from the module.

---

*InquiryInstitute · [dungeon.castalia.institute](https://dungeon.castalia.institute)*
