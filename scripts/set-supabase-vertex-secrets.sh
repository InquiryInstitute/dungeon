#!/usr/bin/env bash
# Set Gemini secrets for dm-invoke Edge Function in Supabase.
# Prefer GCP_API_KEY (Generative Language API, no IAM). Else: Vertex (VERTEX_*).
# Sources .env / .env.local from dungeon or ../Inquiry.Institute.
set -e

cd "$(dirname "$0")/.."

II="../Inquiry.Institute"
for f in .env .env.local "$II/.env.local" "$II/.env" "$II/gcp/faculty-runner/.env"; do
  if [[ -f $f ]]; then
    set -a
    source "$f"
    set +a
  fi
done

# Prefer VERTEX_* names; fall back to GCP_* (Inquiry.Institute convention).
export VERTEX_PROJECT_ID="${VERTEX_PROJECT_ID:-${GCP_PROJECT_ID:-${GOOGLE_CLOUD_PROJECT:-inquiry-institute}}}"
export VERTEX_LOCATION="${VERTEX_LOCATION:-${GCP_LOCATION:-us-central1}}"
if [[ -z "${VERTEX_SERVICE_ACCOUNT_JSON:-}" && -n "${GOOGLE_APPLICATION_CREDENTIALS:-}" ]]; then
  cred_file="${GOOGLE_APPLICATION_CREDENTIALS}"
  if [[ -f "$cred_file" ]]; then
    VERTEX_SERVICE_ACCOUNT_JSON=$(cat "$cred_file")
  elif [[ -f "$II/$cred_file" ]]; then
    VERTEX_SERVICE_ACCOUNT_JSON=$(cat "$II/$cred_file")
  fi
  export VERTEX_SERVICE_ACCOUNT_JSON
fi
if [[ -z "${VERTEX_SERVICE_ACCOUNT_JSON:-}" ]]; then
  for try in "$II/gcp/google-chat-service-account.json" "$II/gcp/vertex-service-account.json" "$II/gcp/faculty-runner/service-account.json"; do
    if [[ -f "$try" ]]; then
      VERTEX_SERVICE_ACCOUNT_JSON=$(cat "$try")
      export VERTEX_SERVICE_ACCOUNT_JSON
      break
    fi
  done
fi

# Option A: Generative Language API (no Vertex IAM)
if [[ -n "${GCP_API_KEY:-}" ]]; then
  echo "Setting GCP_API_KEY (Generative Language API)..."
  supabase secrets set GCP_API_KEY="$GCP_API_KEY"
  echo "Done. DM will use API key; no Vertex IAM required."
  exit 0
fi

# Option B: Vertex AI
missing=()
[[ -z "${VERTEX_PROJECT_ID:-}" ]] && missing+=(VERTEX_PROJECT_ID)
[[ -z "${VERTEX_LOCATION:-}" ]] && missing+=(VERTEX_LOCATION)
[[ -z "${VERTEX_SERVICE_ACCOUNT_JSON:-}" ]] && missing+=(VERTEX_SERVICE_ACCOUNT_JSON)
if [[ ${#missing[@]} -gt 0 ]]; then
  echo "Missing: ${missing[*]} (or set GCP_API_KEY for API-key path)"
  echo "Set in .env / .env.local or Supabase Dashboard → Edge Functions → Secrets"
  echo "  API key: supabase secrets set GCP_API_KEY=your-key"
  echo "  Vertex:  supabase secrets set VERTEX_PROJECT_ID=... VERTEX_LOCATION=us-central1 VERTEX_SERVICE_ACCOUNT_JSON='...'"
  exit 1
fi

echo "Setting Vertex secrets..."
supabase secrets set VERTEX_PROJECT_ID="$VERTEX_PROJECT_ID"
supabase secrets set VERTEX_LOCATION="$VERTEX_LOCATION"
supabase secrets set VERTEX_SERVICE_ACCOUNT_JSON="$VERTEX_SERVICE_ACCOUNT_JSON"
echo "Done. Invoke the DM again to use Vertex."
