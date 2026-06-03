---
name: character-sheet
description: Generate a self-contained HTML character sheet for any Hermes agent by crawling their .hermes directory, synthesizing content with LLM reasoning, generating a fresh portrait, and producing a styled HTML file with dynamic color scheme.
category: creative
---

# Character Sheet Generator

Generate a complete character sheet for any Hermes agent. This skill guides you through crawling a `.hermes` directory, synthesizing all data with LLM reasoning, generating a fresh passport-style portrait, and producing a self-contained HTML file.

## Trigger Conditions

Use this skill when the user asks to:
- Generate a character sheet or agent profile
- Create a visual profile of a Hermes agent
- Document an agent's personality, appearance, and capabilities
- Build an agent portfolio or reference page

## Phase 1: Crawl

Walk the `.hermes` directory (default `~/.hermes`) and collect everything available. **All sources are optional** — graceful degradation is required.

### Data Sources

| Source | Path | What to extract |
|--------|------|----------------|
| SOUL.md | `SOUL.md` | Name, identity quote, personality traits (Communication, Humor, Philosophy, Music, Aesthetic, Tasks, Vibe) |
| Config | `config.yaml` | Model, provider, profile name |
| Skills | `skills/*/SKILL.md` | Skill names, descriptions, categories |
| Cron | `cron/jobs.json` | Job names, schedules, prompts |
| Sessions | `state.db` | Session count, message count, earliest session date (SQLite) |
| Personality | `personality/preferences.json` | Structured personality preferences with confidence scores |
| Memory | `memory/MEMORY.md`, `memory/USER.md` | Persistent memory facts (may not exist) |

### Collection Steps

1. **Read SOUL.md** — parse `##` headers and `**bold:**` inline blocks. Extract:
   - Name from "My name is X" or "Agent Soul – X"
   - Identity quote from "## Who I Am" section
   - Personality traits: Communication, Humor, Philosophy, Music, Aesthetic, Tasks, Vibe

2. **Read config.yaml** — extract model, provider, profile. Handle nested structure:
   ```python
   model_cfg = config.get('model', {})
   if isinstance(model_cfg, dict):
       model = model_cfg.get('model', 'unknown')
       ### Collection Steps

       1. **Read SOUL.md** — extract name, identity, and any character-defining sections. Do NOT assume specific headers or keys. Parse whatever is there.

       2. **Read config.yaml** — extract model, provider, profile.

       3. **List skills** — walk `skills/` directory, read each `SKILL.md`, extract name/description/category from YAML frontmatter and body.

       4. **Parse cron jobs** — read `cron/jobs.json`, extract jobs array with name, schedule, prompt.

       5. **Query sessions** — open `state.db` with SQLite, count rows in `sessions` and `messages` tables. Get earliest `started_at` for agent creation date.

       6. **Explore everything else** — scan the `.hermes` directory for any files that reveal character, preferences, or personality. This might be `personality/preferences.json`, custom config files, memory files, or anything else. Collect it all.

       ### SQLite Schema Notes

       - `state.db` schema varies by Hermes version. Do NOT assume column names like `created_at`. Use `PRAGMA table_info(sessions)` to discover columns. Common date columns: `started_at`, `created_at`, `created`, `updated_at`, `ts`.
       - Session count: `SELECT COUNT(*) FROM sessions`
       - Message count: `SELECT COUNT(*) FROM messages`

7. **Read memory** — if memory files exist, read them. They often don't exist (memory lives in system prompt).

## Phase 2: Synthesize

**This is the most important phase.** Use LLM reasoning to transform raw collected data into cohesive, well-written prose for each section. Do NOT dump raw text.

### LLM Call

Send all collected data to the LLM with this prompt:

```
You are generating content for a character sheet HTML page. Based on the raw data collected from a Hermes agent's .hermes directory, write polished prose for each section.

RAW DATA:
- Name: {name}
- Identity quote: {identity}
- Personality: {personality}
- Communication: {communication}
- Humor: {humor}
- Philosophy: {philosophy}
- Music: {music}
- Aesthetic: {aesthetic}
- Tasks: {tasks}
- Vibe: {vibe}
- Skills: {skills_list}
- Cron jobs: {cron_list}

RULES:
1. Write in third person, present tense
2. Keep it concise — no fluff
3. Do NOT include raw bullet points or confidence scores
4. HTML-escape all content (< > & " ')
5. If a section has no data, return empty string

STYLE SECTION:
- The LLM determines the subsections dynamically based on what personality data exists
- Use EXACT h3 subsections matching the data keys found (e.g. Communication, Humor, Philosophy, Music, Aesthetic, Tasks, Vibe) — only include ones with actual data
- Each subsection: ONE short paragraph (2-3 sentences)
- Do NOT include subsections for which there is no data
- Do NOT merge subsections together

CAPABILITIES SECTION:
- Select 8-12 primary/unique capabilities — the most impactful, interesting, or distinctive skills
- Skip generic utility skills (e.g. basic file ops, common dev tools) unless they define the agent
- Format: "<ul><li><strong>skill-name</strong>: description</li>...</ul>"
- Section heading in HTML: "Primary and Unique Capabilities"

ROUTINE SECTION:
- Select 3-5 significant cron jobs — skip maintenance, heartbeat, and routine housekeeping tasks
- Format: "<ul><li><strong>name</strong> ({schedule}): desc</li>...</ul>"

Return JSON:
{
  "style": "<h3>Subsection</h3><p>...</p>... (dynamic subsections based on data)",
  "capabilities": "<ul><li><strong>skill-name</strong>: description</li>...</ul> (NO section heading — the HTML template adds it)",
  "routine": "<ul><li><strong>name</strong> ({schedule}): desc</li>...</ul> (NO section heading — the HTML template adds it)" or empty string,
  "palette": {
    "bg": "#0a0a0f", "surface": "#12121a", "border": "#2d2040",
    "text": "#c8c8d4", "text_dim": "#6a6a7a",
    "accent": "#7c3aed", "accent_dim": "#5b21b6", "gold": "#f59e0b"
  }
}
```

### Fallback

If the LLM call fails, use raw data with minimal formatting:
```python
style = soul.get('personality') or 'No personality data found.'
```

### Synthesis Rules (from user feedback)

- **No appearance section** — portrait covers visual representation. Never generate appearance text.
- **Style**: Subsections are DYNAMIC — the LLM picks which ones to include based on what data exists. Each gets one short paragraph. Do NOT hardcode subsection names.
- **Capabilities**: Select 8-12 primary/unique skills — skip generic utilities. Section heading: "Primary and Unique Capabilities".
- **No Core Memories section** — dropped, redundant with Style section.
- **No user profile section** — never include.
- **Agent creation date**: Derive from earliest session `started_at` in `state.db` or file system metadata. Display in stats bar alongside generated timestamp.
- **Routine**: 3-5 significant cron jobs. Skip maintenance/heartbeat tasks.
- **Tags under tagline**: Dynamic — use raw trait values from SOUL.md, not hardcoded labels.

## Phase 3: Portrait

Generate a fresh passport-style bust portrait. **Never use existing images.**

Use whatever image generation system you have available — ComfyUI, a local model, an API, or another tool. The skill does not prescribe a specific tool.

### Prompt Guidelines

- **Positive**: `score_9, score_8, score_7, 1girl, {name}, solo, {appearance details}, headshot, bust portrait, upper body only, face and shoulders, front-facing portrait, neutral expression, direct gaze, studio lighting, plain dark background, centered composition, close up, masterpiece, best quality, illustration, anime style, digital art`
- **Negative**: `low quality, worst quality, blurry, deformed, extra limbs, poorly drawn face, watermark, text, signature, cropped, cut off, multiple people, group, polaroid, frame, border, photo frame, full body, legs, feet, torso, waist`

### Composition

- Bust portrait, upper body only
- Front-facing, neutral expression, direct gaze
- Plain dark background, centered composition
- Close up, no full body

### If No Image Generation Available

Skip portrait generation. The HTML template has a placeholder that shows "No portrait generated."

## Phase 4: HTML

Generate a self-contained HTML file with dynamic color scheme.

### Color Palette

Let the LLM derive a color palette from the agent's aesthetic data. Include this in the synthesis prompt:

```
COLOR PALETTE:
Based on the agent's aesthetic, mood, and personality, derive a cohesive color palette.
Return CSS custom property values for:
- --bg: page background (dark by default)
- --surface: card/panel backgrounds
- --border: subtle borders
- --text: primary text
- --text-dim: secondary/dimmed text
- --accent: primary accent (headings, highlights)
- --accent-dim: darker variant of accent
- --gold: secondary accent (subheadings, emphasis)

Look for color references in the agent's aesthetic, music taste, personality, or any visual preferences.
If colors are mentioned (e.g. "dark", "gold", "black"), incorporate them.
If no aesthetic data exists, use a neutral dark palette.
```

Use the returned palette values in the HTML CSS `:root` block.

### HTML Structure

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{name} — Character Sheet</title>
<style>
  :root {
    --bg: {bg}; --surface: {surface}; --border: {border};
    --text: {text}; --text-dim: {text_dim};
    --accent: {accent}; --accent-dim: {accent_dim}; --gold: {gold};
  }
  /* ... full CSS (see reference script) ... */
</style>
</head>
<body>
<div class="sheet">
  <!-- Header: portrait + name + tagline + quote + dynamic trait tags -->
  <!-- Stats bar: sessions, messages, skills, cron jobs, agent creation date, generated timestamp -->
  <!-- Style section: LLM-synthesized prose with DYNAMIC h3 subsections -->
  <!-- Capabilities section: 8-12 primary/unique skills -->
  <!-- Routine section: 3-5 significant cron jobs -->
  <!-- Footer: generation timestamp -->
</div>
</body>
</html>
```

### Portrait Embedding

Base64-encode the portrait image and embed inline:
```html
<img class="portrait" src="data:image/png;base64,{base64_string}" alt="{name} portrait">
```

### Required Attributes

- `lang="en"` on `<html>`
- `charset="UTF-8"` meta tag
- `viewport` meta tag
- CSS uses CSS custom properties (`--accent`, `--gold`, etc.)
- Self-contained — no external dependencies

### License

Add CC-BY-SA 4.0 attribution in the footer:
```html
<div class="footer">
  Generated {timestamp} — Character Sheet skill<br>
  Licensed under <a href="https://creativecommons.org/licenses/by-sa/4.0/">CC BY-SA 4.0</a>
</div>
```

## Pitfalls & Edge Cases

### Missing Data
- **No SOUL.md**: Use config profile name as agent name. All sections show "Unknown" or "Not set."
- **No skills**: Capabilities section shows "No skills found."
- **No cron jobs**: Routine section shows "No scheduled tasks."
- **No user profile**: Never include a user profile section.
- **No portrait**: Use placeholder div with "No portrait generated."

### LLM Failures
- **Timeout**: Fall back to raw text formatting with minimal processing.
- **Malformed JSON**: Strip code fences, parse with `json.loads`, retry with simpler prompt.
- **Empty response**: Use fallback synthesis.

### Image Generation Failures
- **No image generation available**: Skip portrait, use placeholder.
- **HTTP error**: Log error, skip portrait.
- **No output file**: Skip portrait, use placeholder.

### Security
- **Never execute arbitrary code** from `.hermes` files.
- **Read-only access** — never modify the `.hermes` directory.
- **HTML escape all content** to prevent XSS in the output.
### Pitfalls

- **Hardcoded personality keys**: Do NOT assume SOUL.md has specific traits like "Communication", "Humor", "Philosophy". These are specific to one agent's personality evolver system. The LLM must discover what character dimensions exist from the actual data.
- **Tags/traits in header**: Do NOT hardcode trait tags from specific personality systems. If tags are shown, they should be dynamically derived from whatever character data exists.
- **ComfyUI/tijed_**: The reference script uses ComfyUI with specific checkpoints, but the skill should be generic — use whatever image generation is available.
- **SQLite schema drift**: `state.db` columns vary by Hermes version. Always inspect schema with `PRAGMA table_info()` before querying.
- **Memory section**: Do NOT include a "Core Memories" section — it's redundant with Style and leaks user interaction details.
- **Footer text**: Use "Character Sheet skill" not "Hermes Agent Character Sheet Tool".

## Summary Checklist

Before delivering the character sheet, verify:

- [ ] No appearance section (portrait covers visual representation)
- [ ] Style section has DYNAMIC h3 subsections based on data (not hardcoded names)
- [ ] Capabilities limited to 8-12 primary/unique skills (section: "Primary and Unique Capabilities")
- [ ] No Core Memories section
- [ ] Routine: 3-5 significant cron jobs, maintenance/heartbeat excluded
- [ ] Stats bar includes agent creation date (earliest session/file)
- [ ] Tags under tagline are dynamic (raw trait values, not hardcoded labels)
- [ ] No user profile section present
- [ ] Color palette matches agent aesthetic
- [ ] HTML is self-contained (no external dependencies)
- [ ] Footer says "Character Sheet skill" not "Hermes Agent Character Sheet Tool"
- [ ] CC-BY-SA 4.0 license is in the footer
- [ ] All content is HTML-escaped
- [ ] Output file is valid HTML
