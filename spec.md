# SPEC.md — Automated Digital Infrastructure Newsletter (MVP)

## 0) Purpose

Build an MVP backend that generates a **weekly digital infrastructure newsletter** using a **LangGraph multi‑agent workflow** with:

- **Manager (Orchestrator)** → **Research Agents (vertical specialists)** → **Reviewer** (iterative fix plan loop) → **Editor** (minor voice/consistency pass) → **Assembly**.
- **Natural language requests** to kick off a newsletter: the user can type a free‑form prompt (e.g. “Summarise the last week’s news on data centres and fibre for UK and EU and keep the tone technical”).  The manager uses an LLM to parse this into a structured run state (time window, verticals to include, voice, regional focus, etc.) with sensible defaults if fields are missing.
- **No embeddings** and **no analytics tools**. Agents rely on **LLM reasoning** plus deterministic retrieval tools.  Research agents may devise follow‑up search queries based on the themes they observe, within a defined call budget.
- Output stored as **.md files** (newsletter + per‑section artefacts) and served via **FastAPI**.
- Initial use‑case: **generate last‑week/news within a chosen timeframe** with configurable style prompt.  A future targeted edit mode will be supported by the same architecture, allowing update of a specific section without regenerating the entire issue.

Target audience voice: **sector‑experts (operators, investors, practitioners)** by default, but **tweakable in the user’s natural language request**.

---

## 1) Scope

### In scope (MVP)

- Verticals:
  1) **Data Centers**
  2) **Connectivity & Fibre**
  3) **Towers & Wireless Infrastructure**

- Newsletter format for each vertical:
  - **Big picture paragraph** (key themes/trends/macro news).
  - **Up to 5 one‑line bullets** each referencing updates to a deterministic list of “major players”.

- Deterministic list: generate **10 large comps per vertical** now; user may augment later.

- Retrieval tooling (deterministic):
  - Web search tool (e.g. Tavily).
  - Article fetch/parse tool (newspaper3k).
  - Market data tool (yfinance) (optional inclusion for public players; does not compute analytics).

- Evidence packs + citations:
  - Every claim/bullet must cite one or more **evidence IDs** from retrieved sources.

- FastAPI backend endpoints:
  - Create newsletter issue from a natural language prompt.  The manager uses an LLM to extract `time_window`, `voice_profile`, `region_focus`, `style_prompt` and other fields (see Section 8).  Defaults are used when fields are omitted (e.g. last 7 days for time window, expert tone, global scope).
  - Retrieve generated newsletter markdown.
  - Retrieve section artefacts (evidence pack, review logs).

- Storage:
  - Filesystem‑based `.md` and `.json` artefacts (no DB required for MVP).

### Out of scope (for now)

- Scheduled automation / cron (we will run via API calls or UI, not time‑based triggers yet).
- Embeddings / vector DB / clustering / dedupe via embeddings.
- Advanced analytics (keyword drift, anomaly detection).
- Full “targeted edit” UI; only backend scaffolding for updates.
- SEC filings ingestion (can be added later).

---

## 2) System Overview

### User‑facing behaviours

**Mode A: Generate Newsletter (Natural language input)**

1. **User writes a free‑form request** describing the desired newsletter.  The system should recognise key signals such as date range (time window), region or company focus, desired voice, and any style preferences.  Example: “Give me a rundown of the last two weeks of data centre news in Europe with a more conversational tone”.
2. **Manager parses the request** via a system prompt to the LLM, extracting structured fields:
   - `time_window`: start/end timestamps or a relative phrase like “last week” (default: last 7 days ending today).
   - `verticals`: which of the three supported sectors to include (default: all three).
   - `voice_profile`: desired voice; defaults to expert/operator tone.
   - `region_focus`: optional region filters like “UK”, “EU”, “US”; default is global.
   - `style_prompt`: freeform tone/style override (optional).
3. Manager instantiates a run state with the extracted fields and triggers the LangGraph workflow.
4. System returns the newsletter output and associated artefact paths.

**Mode B: Update Existing Newsletter Section (designed but not primary MVP)**

1. User specifies an existing `newsletter_id` and a `section_id`, along with a natural language instruction (e.g. “Expand the connectivity section to include more about Latin America” or “Tone down the hype in towers section”).
2. Manager parses the instruction and triggers only the relevant research and review loop for that section, preserving the rest of the newsletter.
3. On success, the system writes an updated section and changelog entry.

The targeted edit mode shares the same architecture; the natural language parsing extracts the new time window or region focus if present.

---

## 3) Architecture

### Components
1. **FastAPI** service (HTTP API for requests/responses).
2. **LangGraph** workflow (agent graph orchestrating research, review, edit, assembly).
3. **Tooling layer** (deterministic retrieval via Tavily, newspaper3k, yfinance).  Tools return lists of `EvidenceItem` objects; they do not interpret or compute statistics.
4. **Artifact store** (filesystem for .md and .json files per issue).
5. **OpenAI** (LLM calls for research agents, reviewer, editor, and manager input parsing).

### High‑level flow
1. **Manager** receives a natural language request, calls the LLM to extract the run state (time window, verticals, voice, region, style, etc.).  It initialises the issue state and spawns research agents.
2. **Research agents** (one per vertical) gather sources with the retrieval tools, build an `EvidencePack`, and draft a section (one paragraph + up to five bullets, each citing evidence).  Agents may generate follow‑up search queries based on the initial evidence and observed trends, subject to call limits.
3. **Reviewer** scores each section, enforcing grounding, clarity, balance and voice.  It produces a `FixPlan` with targeted instructions if issues are found.
4. **Manager** routes fix plans back to the appropriate research agents.  The loop continues until all sections pass or a maximum number of review rounds is reached.
5. **Editor** does a minor voice/consistency pass without adding facts.
6. **Assembly** composes the final newsletter markdown and writes all artefacts.

---

## 4) Verticals and deterministic “major players” lists

These lists are **deterministic**; bullets should map to these names when possible.  The research agent should prioritise updates about these entities in the bullet section.  User can augment the lists later via configuration.

### 4.1 Data Centers — major players (10)
1. Equinix
2. Digital Realty
3. CyrusOne
4. QTS Data Centers
5. NTT Global Data Centers
6. Iron Mountain Data Centers
7. Switch
8. STACK Infrastructure
9. Google Cloud (as hyperscaler operator signal)
10. Amazon Web Services (AWS)

Notes:
- The last two are demand‑side operators with major infra buildouts; they can be swapped later.

### 4.2 Connectivity & Fibre — major players (10)
1. Lumen Technologies
2. Zayo
3. Crown Castle Fiber (fibre assets)
4. Colt Technology Services
5. euNetworks
6. CityFibre
7. Openreach
8. Telxius
9. Sparkle (Telecom Italia Sparkle)
10. Subsea7 / major subsea build signals (operator/project references)

Notes:
- Some are operators; some are asset platforms.  User can refine per region later.

### 4.3 Towers & Wireless Infrastructure — major players (10)
1. American Tower
2. Cellnex Telecom
3. Vantage Towers
4. SBA Communications
5. IHS Towers
6. Indus Towers
7. Crown Castle
8. Phoenix Tower International
9. Helios Towers
10. DigitalBridge (platform / tower & infra exposure)

Notes:
- Mix of global listed + large private platforms.  Can be adjusted later.

---

## 5) Newsletter Output Format (Markdown)

### 5.1 File layout (per issue)

- `issues/{newsletter_id}/newsletter.md` (final assembled output).
- `issues/{newsletter_id}/sections/{section_id}.md` (final section text).
- `issues/{newsletter_id}/sections/{section_id}.json` (structured section output).
- `issues/{newsletter_id}/evidence/{section_id}_pack.json` (evidence pack).
- `issues/{newsletter_id}/reviews/{section_id}_review_round_{k}.json` (review outputs).
- `issues/{newsletter_id}/meta.json` (inputs, timestamps, model versions, extracted fields).
- `issues/{newsletter_id}/changelog.json` (diff summary, especially for updates).

### 5.2 Markdown template (final newsletter)

```md
# Digital Infra Newsletter — {issue_date}

_Time window: {start_date} to {end_date}_  
_Voice: {voice_profile}_

---

## Data Centers
{big_picture_paragraph}

**Major player updates**
- {bullet_1} [evidence: ev_x, ev_y]
- {bullet_2} [evidence: ev_a]
...

---

## Connectivity & Fibre
{big_picture_paragraph}

**Major player updates**
- ...

---

## Towers & Wireless Infrastructure
{big_picture_paragraph}

**Major player updates**
- ...
```

Constraints:
- Big picture paragraph: ~80–140 words (configurable via prompt).
- Bullets: maximum 5; one line each.
- Each paragraph/bullet must include at least one evidence ID reference.

---

## 6) Agents & Responsibilities

### 6.1 Manager (Orchestrator)

**Responsibilities**
- Receive a **natural language request** to generate or update a newsletter.  Use an LLM with a prompt schema to extract structured fields: `time_window`, `verticals`, `voice_profile`, `region_focus`, `style_prompt`, `max_review_rounds`, etc.  Provide sensible defaults (e.g. last 7 days, all verticals, expert tone) when fields are missing.
- Initialises the run state and orchestrates the LangGraph workflow: spawns research agents, collects drafts, triggers reviewer, handles fix loops, invokes editor, assembles outputs, and persists artefacts.
- Supports two modes: `generate_issue` (build all verticals) and `update_section` (regenerate only one section based on a new instruction).

### 6.2 Research Agents (vertical specialists)

**Responsibilities**
- Use the retrieval tools to gather sources relevant to the vertical and timeframe.  They start with a set of seeded queries derived from the run state (e.g. sector keywords, major players, region focus).  They may **generate additional queries** based on observed trends or themes in the initial evidence (e.g. if multiple sources mention “power constraint”, the agent can craft a follow‑up search around that concept).  A configurable call budget (e.g. 12 tool calls) limits the number of follow‑up queries.
- Build an `EvidencePack` (curated sources + minimal notes) containing all collected evidence.
- Draft the section in the required markdown structure (one paragraph + up to 5 bullets).  Ensure each claim references at least one `evidence_id`.  Bullets should prioritise news about the deterministic major players list; if the news is sector‑wide rather than player‑specific, note that.
- Highlight any uncertainties or missing context via a `risk_flags` list.

**Hard constraints**
- Must not introduce claims without evidence.
- Must not invent statistics or analytics; the tool layer does not compute analytics.
- Follow the word/bullet limits.

### 6.3 Reviewer Agent

**Responsibilities**
- Score each draft by rubric (see below) and identify issues.
- Produce a `FixPlan` with actionable requests to the specific research agent (e.g. “Find one more source corroborating claim 2 using `web_search`”, “Clarify the timeframe for the capacity announcement”).
- Block acceptance if there are unsupported claims, if clarity is too low, or if tone is inappropriate.

**Rubric (0–5 per criterion)**
1. **Grounding**: How well claims are supported by evidence (citations present and relevant).
2. **Clarity**: Are the paragraph and bullets concise and comprehensible to the expert audience?
3. **Newsworthiness**: Does the section surface timely and important information?
4. **Balance**: Does it avoid hype, include caveats and constraints where relevant?
5. **Voice fit**: Does the tone match the requested voice/profile?

Acceptance requires:
- Grounding ≥ 4 and clarity ≥ 4.
- No blocking issues (e.g. unsupported claims, duplicated bullets).

### 6.4 Editor Agent (minor pass)

**Responsibilities**
- Perform a minor rewrite for consistency across sections, adjusting phrasing and structure to ensure a smooth and cohesive newsletter.
- Enforce consistent style (tense, concision, formatting).
- **Must not add new facts or remove evidence references**.  If the editor detects an unsupported claim, it should raise an error back to the manager rather than silently fixing it.

---

## 7) Tools (Deterministic Retrieval)

All tools must return lists of **EvidenceItem** objects.  Tools do not interpret data or compute analytics; they retrieve and parse content.

### 7.1 Tool: `web_search` (Tavily or similar)

**Inputs**
- `query: string` – the search string.
- `max_results: int` – maximum number of results.
- optional: `time_window` – if the provider supports date filtering.

**Output**
- Evidence items with `title`, `url`, `snippet`/`text`, and `retrieved_at`.

### 7.2 Tool: `fetch_article` (newspaper3k)

**Inputs**
- `url: string` – the article URL to fetch and parse.

**Output**
- Evidence item with clean text, title, authors, publish_date (if available), and reliability level.

### 7.3 Tool: `get_price_history` (yfinance)

**Inputs**
- `tickers: string[]` – list of tickers to fetch.
- `start: date` – start date.
- `end: date` – end date.
- `interval: 1d | 1h` (default `1d`).

**Output**
- Evidence item with a structured OHLCV payload.  No analytics are computed in tool; agents can mention price movements only if they have retrieved and verified the data.

### 7.4 EvidenceItem schema

```json
{
  "evidence_id": "ev_ab12cd34",
  "source_type": "web|news|market_data",
  "source_name": "tavily|newspaper3k|yfinance",
  "retrieved_at": "ISO-8601 timestamp",
  "url": "optional string",
  "title": "optional string",
  "text": "optional cleaned text",
  "data": "optional structured payload",
  "reliability": "high|medium|low",
  "tags": ["optional", "strings"]
}
```

---

## 8) LangGraph Design

### 8.1 State object (conceptual)

```json
{
  "run_id": "newsletter_2026-02-02_001",
  "mode": "generate_issue|update_section",
  "time_window": {"start": "...", "end": "..."},
  "verticals": ["data_centers", "connectivity_fibre", "towers_wireless"],
  "voice_profile": "expert_operator_default",
  "region_focus": "optional region string",
  "style_prompt": "optional freeform override",
  "comps": { "data_centers": [...], ... },
  "evidence_budgets": { "data_centers": 12, ... },
  "max_review_rounds": 2,
  "artifacts": {
    "evidence_packs": {},
    "drafts": {},
    "reviews": {},
    "final_sections": {}
  }
}
```

The state also stores intermediate information like extracted input fields, LLM model versions, and timestamps.

### 8.2 Nodes
- `manager_init` – parse natural language input, initialise state, dispatch research agents.
- `research_data_centers`, `research_connectivity_fibre`, `research_towers_wireless` – gather evidence, draft section.
- `review_sections` – reviewer node to score drafts and produce fix plans.
- `route_fix_plans` – manager node to route fix requests and control loop.
- `editor_pass` – editor node for minor consistency edits.
- `assemble_newsletter` – combine final sections into newsletter markdown.
- `persist_artifacts` – write files to disk.

### 8.3 Edges (Generate mode)
1. `manager_init` → parallel research nodes.
2. Research nodes → `review_sections`.
3. `review_sections` → if any sections are rejected and rounds remain → `route_fix_plans` → back to specific research nodes.
4. If all sections are accepted or rounds exhausted → `editor_pass` → `assemble_newsletter` → `persist_artifacts`.

### 8.4 Edges (Update section mode)
1. `manager_init` → only targeted research node.
2. → `review_sections` loop for that section.
3. → `editor_pass`.
4. → `assemble_newsletter` (replace section) → `persist_artifacts`.

---

## 9) FastAPI API Design

### 9.1 Endpoints

#### POST `/newsletter/generate`
Generate a full issue from a natural language description.

**Request Body (JSON)**
```json
{
  "prompt": "natural language describing timeframe, region focus, voice, etc.",
  "max_review_rounds": 2
}
```

If `max_review_rounds` is omitted, default to 2.  The manager will call the LLM to parse the prompt into structured inputs; invalid or missing fields will fall back to defaults.

**Response**
```json
{
  "newsletter_id": "newsletter_20260202_abcdef",
  "paths": {
    "newsletter_md": "issues/.../newsletter.md",
    "meta": "issues/.../meta.json"
  }
}
```

#### POST `/newsletter/{newsletter_id}/update-section`
Update one section (scaffold for targeted edits).

**Request Body (JSON)**
```json
{
  "section_id": "data_centers|connectivity_fibre|towers_wireless",
  "instruction": "natural language describing how to modify the section",
  "time_window": {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}
}
```
If `time_window` is omitted, the original issue’s timeframe is used.  The manager will parse the instruction into structured modifications.

### 9.2 GET endpoints

- `GET /newsletter/{newsletter_id}` → returns newsletter markdown.
- `GET /newsletter/{newsletter_id}/sections/{section_id}` → returns section markdown.
- `GET /newsletter/{newsletter_id}/artifacts/{artifact_path}` → returns JSON artefacts (evidence packs, reviews).

### 9.3 Authentication (MVP)
- None required initially (local testing).  Add API key header later.

---

## 10) Prompting & Guardrails

### 10.1 Manager input parsing prompt

The manager uses an LLM prompt to extract structured fields from the user’s natural language request.  The prompt should:
- Identify any explicit date ranges or relative date phrases.  Use the user’s locale/timezone (`Europe/London`) and the current date to interpret relative phrases like “last week”.
- Determine which of the supported verticals are requested.  If not specified, include all verticals.
- Extract any region focus (e.g. “UK”, “EU”, “Asia”).  If none, assume global.
- Extract voice preferences (e.g. “more conversational”, “academic tone”).  If none, use default expert/operator voice.
- Copy any additional stylistic instructions into the `style_prompt`.
- Provide defaults for any missing fields.

### 10.2 Research agent prompting

Research agents receive the structured run state plus an overarching system prompt emphasising:
- Use retrieval tools to gather evidence relevant to the vertical, timeframe and region.
- Formulate initial search queries from the sector keywords, major players, and region focus.  Then, based on evidence themes, craft limited follow‑up queries (bounded by call budget).  For example, if many sources mention “grid constraints in UK”, the agent may issue a query around “grid constraints UK data centres {time_window}”.
- Build an EvidencePack with all evidence items retrieved.
- Draft one paragraph summarising big picture themes, followed by up to five bullets keyed to major players.
- Include at least one evidence ID after every claim.
- Record any uncertainties or missing data in `risk_flags`.

### 10.3 Review agent prompting

The reviewer receives the draft and evidence pack.  Its system prompt instructs it to:
- Score the draft by the rubric (grounding, clarity, newsworthiness, balance, voice fit).
- Identify unsupported claims, unclear phrasing, duplications, or tone mismatches.
- Produce a FixPlan specifying the target agent, the nature of the fix (e.g. fetch more sources, rewrite bullet to align with evidence), and the suggested tool(s) if applicable.
- Respect the maximum number of review rounds; avoid unnecessary nit‑picks when minor issues could be resolved in the editor pass.

### 10.4 Editor agent prompting

The editor receives accepted drafts and is instructed to:
- Harmonise tone across sections.
- Shorten or rearrange sentences for readability and consistency.
- Maintain citations and not add facts.
- Raise an exception if any unsupported claim remains.

### 10.5 Citation convention in markdown

Use inline suffix notation:
- `… [evidence: ev_ab12cd34, ev_98ef7654]`

Every paragraph and bullet must have at least one evidence citation.

---

## 11) Configuration

### 11.1 Environment variables

- `OPENAI_API_KEY` – API key for OpenAI.
- `TAVILY_API_KEY` – API key for the web search provider.
- `MODEL_MANAGER` – model for input parsing (e.g. `gpt-4-0613`).
- `MODEL_RESEARCH` – model for research agents (e.g. `gpt-4-0613`).
- `MODEL_REVIEW` – model for reviewer agent.
- `MODEL_EDIT` – model for editor agent.
- `MAX_TOOL_CALLS_PER_AGENT` – default call budget for follow‑up queries (e.g. 12).
- `ISSUES_DIR` – base directory to write issues (default `./issues`).

### 11.2 Runtime options

- `time_window` – start/end; default: last 7 days ending today.
- `voice_profile` – default expert/operator voice; user can override.
- `region_focus` – optional filter; default global.
- `style_prompt` – optional free‑form styling instructions.
- `max_review_rounds` – default 2; can be set per request.

---

## 12) Query Guidance and Follow‑up Search

Rather than rigid “default query templates”, the system offers **guiding heuristics** for research agents.  Each research agent will craft their own queries based on the run state and what they discover.  To ensure coverage without over‑searching:

1. **Initial seed queries** are derived from:
   - Sector keywords (e.g. “data centre capacity expansion”, “fibre network investments”, “tower leasing agreements”).
   - Major players list (entity names plus the timeframe and region).
   - Region focus, if specified (e.g. “UK data centre planning applications 2026”).

2. **Follow‑up queries** may be generated by the research agent after reviewing initial evidence.  For example:
   - If multiple articles mention a common theme (e.g. “grid constraints”, “AI workloads”, “5G densification”), the agent can craft a query combining that theme with the vertical and region.
   - If a major player appears frequently but is absent from the bullets, the agent can search specifically for that player.

3. **Call budget**: Each research agent is limited to a configurable number of tool calls (e.g. 12).  They must balance breadth and depth.

4. **Deterministic anchors**: Agents should always attempt to cover the major players list, but they can include sector‑wide or macro bullets if player‑specific news is sparse.

5. **Information currency**: Agents must prioritise sources within the specified time window and should avoid outdated content.  If the user’s time window extends into the future (due to mis‑interpretation), the manager should correct it to “up to current date” to avoid confusion.

---

## 13) Testing Plan (MVP)

### 13.1 Unit tests

- Validate that tool outputs conform to the `EvidenceItem` schema.
- Ensure that the manager’s input parsing extracts fields correctly from various natural language prompts (e.g. “last 5 days in UK in a more casual tone”).
- Ensure that the assembly logic builds the expected markdown structure.

### 13.2 Integration tests

- Run `/newsletter/generate` with a short timeframe and validate:
  - All sections exist.
  - Each section has 1 paragraph + ≤ 5 bullets.
  - Each paragraph/bullet includes evidence IDs.
  - Reviewer loop enforces grounding and structure; no unsupported claims remain.
  - Editor produces a consistent voice across sections without adding facts.

### 13.3 Golden‑file snapshot test

- For a known timeframe, store output markdown and compare structure (not exact text, as LLM output may vary but structure and citation counts should hold).

---

## 14) Acceptance Criteria

The MVP is complete when:
1. The API can generate an issue from a natural language prompt specifying timeframe and optionally voice/region.
2. Output includes 3 verticals with the required format and evidence IDs.
3. Reviewer loop enforces grounding and structure; no unsupported claims remain.
4. Editor produces a consistent voice across sections without adding facts.
5. Artefacts (evidence packs, reviews, meta) are persisted on disk.

---

## 15) Future Extensions (explicitly not MVP)

- Targeted edit mode UI and full diff rendering.
- Automated schedule (weekly cron) + email delivery.
- Add SEC EDGAR / Companies House filings tools.
- Add dedupe and source‑quality weighting (without embeddings, use heuristics).
- Add per‑region variants (UK/EU/US editions).
- Add multi‑issue archive + search.

---
