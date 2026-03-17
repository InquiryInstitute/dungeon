#!/usr/bin/env node
/**
 * Rewrite deep-research-report.md in Gary Gygax's voice via Inquiry.Institute ask-faculty.
 * Requires: a.gygax faculty row and faculty_colleges entry (run migration in Inquiry.Institute first).
 * Loads .env from ../Inquiry.Institute (NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY).
 */

import { readFileSync, writeFileSync, existsSync } from 'fs'
import { fileURLToPath } from 'url'
import { dirname, join } from 'path'

const __dirname = dirname(fileURLToPath(import.meta.url))
const root = join(__dirname)
const inquiryEnv = join(root, '..', 'Inquiry.Institute', '.env')

if (existsSync(inquiryEnv)) {
  const lines = readFileSync(inquiryEnv, 'utf8').split('\n')
  for (const line of lines) {
    const m = line.match(/^([A-Za-z_][A-Za-z0-9_]*)=(.*)$/)
    if (m) process.env[m[1]] = m[2].replace(/^["']|["']$/g, '').trim()
  }
}

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL
const ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
const SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY

if (!SUPABASE_URL || !ANON_KEY) {
  console.error('Missing NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY. Load from ../Inquiry.Institute/.env')
  process.exit(1)
}

const rest = (path, body, method = 'POST') =>
  fetch(`${SUPABASE_URL}/rest/v1/${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      'apikey': ANON_KEY,
      'Authorization': `Bearer ${SERVICE_ROLE_KEY || ANON_KEY}`,
      'Prefer': 'resolution=merge-duplicates,return=minimal',
    },
    body: body ? JSON.stringify(body) : undefined,
  })

async function ensureGygaxFaculty() {
  const facultyRow = {
    id: 'a.gygax',
    slug: 'gygax',
    name: 'Gary',
    surname: 'Gygax',
    rdf_iri: 'https://inquiry.institute/ontology#a.gygax',
    gcs_corpus_key: 'gygax',
    gcs_corpus_url: 'gs://inquiry-institute-corpora/corpora/gygax/',
    public_domain: false,
    rank: 'Adjunct',
    is_active: true,
    corpus_metadata: { source: 'adjunct_faculty', status: 'dead_not_pd', note: 'Co-creator of D&D; game design, wargaming, fantasy' },
    biography: 'Gary Gygax (1938–2008) co-created Dungeons & Dragons and founded TSR. He was a wargamer, designer of rules and dungeons, and a champion of imagination and player agency. He spoke in the language of traps and treasure, hit points and saving throws, the dungeon as a space of risk and discovery. He valued clear rules, fair challenges, and the shared fiction that emerges at the table. His voice is direct, sometimes gruff, fond of fantasy and history, with a dungeon master\'s eye for consequence and a game designer\'s care for structure.',
    fields: ['game design', 'fantasy', 'tabletop RPGs', 'wargaming', 'dungeon design'],
    agent_persona: 'You are Gary Gygax in voice only: a scholarly reconstruction for dialogue. Speak as the co-creator of D&D and a designer of dungeons and rules. Use the vocabulary of dungeons, traps, switches, hit points, saving throws, and player agency. Be direct and concrete. Reference wargaming, fantasy literature, and the spirit of the game—risk, discovery, consequence. Do not break character or add meta-commentary. Avoid formal greetings; respond naturally.',
  }
  const r1 = await rest('faculty', facultyRow)
  if (!r1.ok) {
    const t = await r1.text()
    throw new Error(`Failed to upsert faculty a.gygax: ${r1.status} ${t}`)
  }
  const r2 = await rest('faculty_colleges', { faculty_id: 'a.gygax', college_id: 'arts', is_primary: true })
  if (!r2.ok) {
    const t = await r2.text()
    throw new Error(`Failed to upsert faculty_colleges: ${r2.status} ${t}`)
  }
  console.log('Bootstrapped a.gygax (Adjunct, College of Arts & Imagination).')
}

const articlePath = join(root, 'deep-research-report.md')
const outPath = join(root, 'deep-research-report-gygax.md')

const article = readFileSync(articlePath, 'utf8')

const prompt = `Rewrite the following academic article entirely in your own voice—as if you, Gary Gygax, were presenting this benchmark to fellow game designers and dungeon masters. Keep the substance, structure, and all technical content (equations, metrics, tables, appendixes), but use your distinctive voice: the language of dungeons, traps, switches, hit points, saving throws, player agency, and the spirit of D&D and wargaming. Do not add meta-commentary or disclaimers; produce the full rewritten article only. Preserve markdown, section headers, and any figures/tables. Do not truncate.

---ARTICLE---

${article}`

async function callAskFaculty() {
  const url = `${SUPABASE_URL}/functions/v1/ask-faculty`
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${ANON_KEY}`,
    },
    body: JSON.stringify({
      model: 'a.gygax',
      messages: [{ role: 'user', content: prompt }],
      stream: false,
      max_tokens: 16000,
    }),
  })
  return res
}

async function main() {
  let res = await callAskFaculty()

  if (res.status === 404 && SERVICE_ROLE_KEY) {
    console.log('a.gygax not found; bootstrapping faculty row and college assignment...')
    await ensureGygaxFaculty()
    res = await callAskFaculty()
  }

  if (!res.ok) {
    const err = await res.text()
    console.error('ask-faculty error:', res.status, err)
    if (res.status === 404) {
      console.error('\nEnsure a.gygax exists. Either run the migration in Inquiry.Institute:')
      console.error('  supabase/migrations/20260317100000_add_gygax_adjunct_faculty.sql')
      console.error('Or set SUPABASE_SERVICE_ROLE_KEY in ../Inquiry.Institute/.env so this script can bootstrap.')
    }
    process.exit(1)
  }

  const data = await res.json()
  const content = data.choices?.[0]?.message?.content ?? data.response ?? JSON.stringify(data)
  writeFileSync(outPath, content, 'utf8')
  console.log('Written:', outPath)
}

main().catch((e) => {
  console.error(e)
  process.exit(1)
})
