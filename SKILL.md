---
name: character-sheet
description: Generate a self-contained HTML character sheet for any Hermes agent by crawling their .hermes directory, synthesizing content with LLM reasoning, generating a fresh portrait, and producing a styled HTML file with dynamic color scheme.
category: creative
---

# Character Sheet Generator

Generate a complete character sheet for any Hermes agent. This skill guides you through crawling a `.hermes` directory, synthesizing all data with LLM reasoning, generating a fresh portrait, and producing a self-contained HTML file.

## Trigger Conditions

Use this skill when the user asks to:
- Generate a character sheet or agent profile
- Create a visual profile of a Hermes agent
- Document an agent's personality and capabilities
- Build an agent portfolio or reference page

## Phase 1: Crawl

Walk the `.hermes` directory (default `~/.hermes`) and collect everything available. **All sources are optional** — graceful degradation is required.

### Data Sources

| Source | Path | What to extract |
|--------|------|----------------|
| SOUL.md | `SOUL.md` | Name, identity, personality, appearance, any character-defining content |
| Config | `config.yaml` | Model, provider, profile name |
| Skills | `skills/*/SKILL.md` | Skill names, descriptions, categories |
| Cron | `cron/jobs.json` | Job names, schedules, prompts |
| Sessions | `state.db` | Session count, message count, earliest session date (SQLite) |
| Memory | `memory/MEMORY.md`, `memory/USER.md` | Persistent memory facts (may not exist) |
| Anything else | `~/.hermes/**` | Personality files, preferences, custom data — anything that reveals character |

### Collection Steps

1. **Read SOUL.md** — extract name, identity, and any character-defining sections. Do NOT assume specific headers or keys. Parse whatever is there.
2. **Read config.yaml** — extract model, provider, profile.
3. **List skills** — walk `skills/` directory, read each `SKILL.md`, extract name/description/category from YAML frontmatter and body.
4. **Parse cron jobs** — read `cron/jobs.json`, extract jobs array with name, schedule, prompt.
5. **Query sessions** — open `state.db` with SQLite, count rows in `sessions` and `messages` tables. Get earliest `started_at` for agent creation date.
6. **Explore everything else** — scan the `.hermes` directory for any files that reveal character, preferences, or personality. This might be `personality/preferences.json`, custom config files, memory files, or anything else. Collect it all.

## Phase 2: Synthesize

**This is the most important phase.** Use LLM reasoning to transform raw collected data into cohesive, well-written prose. Do NOT dump raw text.

### LLM Calls

Split synthesis into separate calls to avoid JSON nesting issues. Each call returns a JSON object with a single key containing HTML content.

1. **Style** — personality, communication, humor, philosophy, aesthetic
2. **Capabilities** — primary skills and technical capabilities
3. **Routine** — significant cron jobs and operational patterns
4. **Palette** — color scheme derived from agent's aesthetic

Each call uses `max_tokens: 1024`, `temperature: 0.7`, and the system message `"Return ONLY valid JSON. No markdown fences."`

### JSON Extraction

The LLM may output unescaped double quotes inside HTML string values. Use regex to extract values robustly rather than relying on `json.loads()` alone.

### Fallback

If the LLM call fails, use raw data with minimal formatting.

## Phase 3: Portrait

Generate a fresh portrait. **Never use existing images.**

Use whatever image generation system is available — ComfyUI, a local model, an API, or another tool. The goal is a clean, front-facing bust portrait that matches the agent's described appearance or aesthetic.

### Portrait Prompt Guidelines

Build a prompt from any appearance or aesthetic data found:
- Include physical traits if available (hair, eyes, face, body type)
- Include clothing/style preferences if available
- Composition: headshot, bust portrait, upper body only, front-facing, neutral expression, direct gaze
- Background: plain, dark, studio lighting
- Style: illustration, digital art, or match the agent's aesthetic

**SFW Guardrails** — always include in the positive prompt:
`simple clothes, fully clothed, modest outfit`

**Negative prompt** — always include:
`nsfw, nude, naked, nudity, sexy, provocative, revealing clothes, see-through, cleavage, bare skin, exposed`

### If No Image Generation Available

Skip portrait generation. The HTML template has a placeholder.

## Phase 4: HTML

Generate a self-contained HTML file with dynamic color scheme.

**The HTML template must be generic — not agent-specific.** The CSS/design should work for any agent regardless of their aesthetic. The content (style, capabilities, routine) is already dynamic via LLM synthesis. The color palette is derived dynamically by the LLM from the agent's data.

### HTML Template Structure

Generate the full HTML inline. Use CSS custom properties for the palette. The template should include:
- Dark background with subtle noise texture overlay
- Monospace font for labels/metadata
- Sans-serif for body text
- Stats grid with hover states
- Two-column capabilities layout
- Routine items with schedule badges
- Responsive design for mobile
- Self-contained (no external dependencies)
- **Light/dark theme support**: CSS custom properties defined for both themes

### Portrait Embedding

Base64-encode the portrait image and embed inline as a data URI.

### Required Attributes

- `lang="en"` on `<html>`
- `charset="UTF-8"` meta tag
- `viewport` meta tag
- CSS uses CSS custom properties
- Self-contained — no external dependencies

### License

Add CC-BY-SA 4.0 attribution in the footer.

### Pitfalls

- **Double section headers**: The LLM may add `<h2>` or `<h3>` headings inside synthesized content. The HTML template already provides section headings — tell the LLM explicitly NOT to include them.
- **Hardcoded personality keys**: Do NOT assume the agent has specific personality sections. Let the LLM discover what exists.
- **Stale memory sections**: The LLM may generate subsections from deprecated or removed memory entries. Check whether the source data still contains the entry before letting the LLM synthesize it.
- **Color palette mapping**: Do NOT use a hardcoded keyword-to-color table. Let the LLM derive colors from the agent's aesthetic data.
- **NSFW portraits**: Image generation models may produce revealing content. Always include SFW guardrails.
- **User data leakage**: Never include user profile data or user-centric memories in the output.

### Missing Data

- **No SOUL.md**: Use config profile name as agent name. All sections show "Unknown" or "Not set."
- **No skills**: Capabilities section shows "No skills found."
- **No cron jobs**: Routine section shows "No scheduled tasks."
- **No portrait**: Use placeholder div.

### LLM Failures

- **Timeout**: Fall back to raw text formatting.
- **Malformed JSON**: Strip code fences, parse with `json.loads`, retry with simpler prompt.
- **Empty response**: Use fallback synthesis.

### Security

- **Never execute arbitrary code** from `.hermes` files.
- **Read-only access** — never modify the `.hermes` directory.
- **HTML escape all content** to prevent XSS.

### Performance

- Portrait generation takes 2-5 minutes. Inform the user.
- LLM synthesis takes 10-30 seconds.
- Data collection is instant.

## Phase 5: PNG Export (Optional)

After generating the HTML, optionally render it to a PNG image using a headless browser (Playwright, Puppeteer, etc.).

### When to Export

- User explicitly requests a PNG output
- User asks for a "preview", "screenshot", or "image" of the character sheet
- Generating for a platform that doesn't support HTML

### How to Export

Use a headless browser to render the HTML and capture a full-page screenshot. Export both dark and light theme variants.

### Delivery

- HTML: self-contained, editable, interactive
- PNG: static preview for sharing (both dark and light variants)

## Summary Checklist

Before delivering the character sheet, verify:

- [ ] Capabilities limited to 8-12 primary/unique skills
- [ ] Routine: 3-5 significant cron jobs, maintenance/heartbeat excluded
- [ ] Stats bar includes agent creation date (earliest session/file)
- [ ] Color palette derived by LLM from agent aesthetic
- [ ] HTML is self-contained (no external dependencies)
- [ ] CC-BY-SA 4.0 license is in the footer
- [ ] All content is HTML-escaped
- [ ] Output file is valid HTML
- [ ] If requested, PNG export generated (both dark and light variants) and delivered alongside HTML
