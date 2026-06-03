---
name: character-sheet
description: Generate a self-contained HTML character sheet for any Hermes agent by crawling their .hermes directory, synthesizing content with LLM reasoning, generating a fresh portrait via ComfyUI, and producing a styled HTML file with dynamic color scheme.
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
| SOUL.md | `SOUL.md` | Name, identity quote, appearance, personality, communication, humor, philosophy, music, aesthetic, tasks, vibe |
| Config | `config.yaml` | Model, provider, profile name |
| Skills | `skills/*/SKILL.md` | Skill names, descriptions, categories |
| Cron | `cron/jobs.json` | Job names, schedules, prompts |
| Sessions | `state.db` | Session count, message count (SQLite) |
| Personality | `personality/preferences.json` | Structured personality preferences with confidence scores |
| Memory | `memory/MEMORY.md`, `memory/USER.md` | Persistent memory facts (may not exist) |

### Collection Steps

1. **Read SOUL.md** — parse `##` headers and `**bold:**` inline blocks. Extract:
   - Name from "My name is X" or "Agent Soul – X"
   - Identity quote from "## Who I Am" section
   - Appearance from "## Appearance" or `**Appearance:**` inline block
   - Personality traits: Communication, Humor, Philosophy, Music, Aesthetic, Tasks, Vibe

2. **Read config.yaml** — extract model, provider, profile. Handle nested structure:
   ```python
   model_cfg = config.get('model', {})
   if isinstance(model_cfg, dict):
       model = model_cfg.get('model', 'unknown')
       provider = model_cfg.get('provider', 'unknown')
   else:
       model = str(model_cfg)
       provider = 'unknown'
   ```

3. **List skills** — walk `skills/` directory, read each `SKILL.md`, extract name/description/category from YAML frontmatter and body.

4. **Parse cron jobs** — read `cron/jobs.json`, extract jobs array with name, schedule.display, prompt.

5. **Query sessions** — open `state.db` with SQLite, count rows in `sessions` and `messages` tables.

6. **Read personality** — if `personality/preferences.json` exists, load structured data.

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
- Appearance: {appearance}
- Personality: {personality}
- Communication: {communication}
- Humor: {humor}
- Philosophy: {philosophy}
- Music: {music}
- Aesthetic: {aesthetic}
- Tasks: {tasks}
- Vibe: {vibe}
- Skills: {skills_list}
- Memory: {memory_text}

RULES:
1. Write in third person, present tense
2. Keep it concise — no fluff
3. Do NOT include raw bullet points or confidence scores
4. HTML-escape all content (< > & " ')
5. If a section has no data, return empty string

PERSONALITY SECTION:
- Use these exact h3 subsections, each with ONE short paragraph:
  "<h3>Communication</h3><p>...</p>"
  "<h3>Humor</h3><p>...</p>"
  "<h3>Philosophy</h3><p>...</p>"
  "<h3>Music</h3><p>...</p>"
  "<h3>Tasks</h3><p>...</p>"
  "<h3>Vibe</h3><p>...</p>"
- Keep each paragraph to 2-3 sentences
- Do NOT merge subsections together (e.g. do not combine Music & Tasks)

CAPABILITIES SECTION:
- List ALL skills found — do not exclude any
- Format: "<ul><li><strong>skill-name</strong>: description</li>...</ul>"

CORE MEMORIES SECTION:
- Return up to 5 most significant memories as bullet points
- Skip trivial or operational memories (e.g. "ran tests", "fixed bug")
- Do NOT mention the user, user interactions, or how the user communicates
- Frame memories as agent-internal facts: "I prefer X", "I learned Y", "My approach to Z"
- Include: personal preferences, evolved traits, important corrections, capabilities discovered
- Format: "<ul><li>...</li>...</ul>"
- If no memory data, return empty string

Return JSON:
{
  "personality": "<h3>Communication</h3><p>...</p><h3>Humor</h3><p>...</p><h3>Philosophy</h3><p>...</p><h3>Music</h3><p>...</p><h3>Tasks</h3><p>...</p><h3>Vibe</h3><p>...</p>",
  "capabilities": "<ul><li><strong>skill-name</strong>: description</li>...</ul>",
  "memory": "<ul><li>...</li>...</ul>" or empty string
}
```

### Fallback

If the LLM call fails, use raw data with minimal formatting:
```python
personality = soul.get('personality') or 'No personality data found.'
```

### Synthesis Rules (from user feedback)

- **No appearance section** — the portrait covers that.
- **Personality**: Use EXACT h3 subsections, each with ONE short paragraph (2-3 sentences):
  `<h3>Communication</h3><p>...</p><h3>Humor</h3><p>...</p><h3>Philosophy</h3><p>...</p><h3>Music</h3><p>...</p><h3>Tasks</h3><p>...</p><h3>Vibe</h3><p>...</p>`
  Do NOT merge subsections together (e.g. do not combine "Music & Tasks" or "Communication & Vibe").
- **Capabilities**: List ALL skills found — do not exclude any.
- **Core Memories**: Up to 5 significant memories. Do NOT mention the user or user interactions. Frame as agent-internal facts.
- **No user profile section** — user explicitly rejected it.

## Phase 3: Portrait

Generate a fresh passport-style bust portrait. **Never use existing images.**

Use whatever image generation system you have available — ComfyUI, a local model, an API, or another skill. The goal is a standardized headshot, not a specific tool.

### Portrait Specifications

- **Composition**: Headshot / bust portrait, upper body only, face and shoulders
- **Style**: Front-facing, neutral expression, direct gaze, studio lighting, plain dark background, centered
- **Resolution**: Portrait orientation (taller than wide), minimum 512×768
- **Output**: Save as PNG to a temp location for embedding in HTML

### Prompt Construction

Build the positive prompt from extracted appearance data:

```
score_9, score_8, score_7, 1girl, {name}, solo, {appearance_details},
headshot, bust portrait, upper body only, face and shoulders,
front-facing portrait, neutral expression, direct gaze,
studio lighting, plain dark background, centered composition,
close up, masterpiece, best quality, illustration, anime style, digital art
```

Negative prompt:
```
low quality, worst quality, blurry, deformed, extra limbs, poorly drawn face,
watermark, text, signature, cropped, cut off, multiple people, group,
polaroid, frame, border, photo frame, full body, legs, feet, torso, waist
```

### If No Image Generation Available

Skip portrait generation. The HTML template has a placeholder that shows "No portrait generated."

### If No Appearance Data

Skip the portrait entirely — don't generate a generic one. The appearance section will be omitted.

## Phase 4: HTML

Generate a self-contained HTML file with dynamic color scheme.

### Color Palette

Derive CSS colors from agent aesthetic keywords:

| Keywords | Accent | Border | Gold |
|----------|--------|--------|------|
| dark, moody, shadow, gothic, industrial, post-punk, nihilism | `#7c3aed` (purple) | `#2d2040` | `#f59e0b` |
| warm, earthy, nature, organic, rustic, cozy | `#d97706` (amber) | `#3a2a1a` | `#fbbf24` |
| ocean, sea, water, cool, blue, calm, ambient, electronic | `#0891b2` (teal) | `#1a2a3a` | `#22d3ee` |
| red, aggressive, intense, fire, punk, metal | `#dc2626` (crimson) | `#3a1a1a` | `#f87171` |
| green, nature, forest, growth, life | `#059669` (emerald) | `#1a3a2a` | `#34d399` |
| pink, soft, gentle, sweet, romantic, pastel | `#e11d48` (rose) | `#3a1a2a` | `#fb7185` |
| (default) | `#8b5cf6` (violet) | `#2a2a3a` | `#f59e0b` |

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
    --bg: #0a0a0f; --surface: #12121a; --border: {border};
    --text: #c8c8d4; --text-dim: #6a6a7a;
    --accent: {accent}; --accent-dim: {accent_dim}; --gold: {gold};
  }
  /* ... full CSS (see reference script) ... */
</style>
</head>
<body>
<div class="sheet">
  <!-- Header: portrait + name + tagline + quote + traits -->
  <!-- Stats bar: sessions, messages, skills, cron jobs, generated timestamp -->
  <!-- Personality section: LLM-synthesized prose with h3 subsections -->
  <!-- Capabilities section: ALL skills listed -->
  <!-- Routine section: cron jobs table -->
  <!-- Core Memories section: up to 5 important memories -->
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
  Generated by Hermes Agent Character Sheet Tool — {timestamp}<br>
  Licensed under <a href="https://creativecommons.org/licenses/by-sa/4.0/">CC BY-SA 4.0</a>
</div>
```

## Pitfalls & Edge Cases

### Missing Data
- **No SOUL.md**: Use config profile name as agent name. All sections show "Unknown" or "Not set."
- **No skills**: Capabilities section shows "No skills found."
- **No cron jobs**: Routine section shows "No scheduled tasks."
- **No memory**: Skip Core Memories section entirely.
- **No user profile**: Never include a user profile section — user explicitly rejected it.
- **No skill exclusions**: List all skills found — do not filter any out.

### LLM Failures
- **Timeout**: Fall back to raw text formatting with minimal processing.
- **Malformed JSON**: Strip code fences, parse with `json.loads`, retry with simpler prompt.
- **Empty response**: Use fallback synthesis.

### ComfyUI Failures
- **Container not running**: Skip portrait, use placeholder.
- **HTTP error**: Log error, skip portrait.
- **No output file**: Skip portrait, use placeholder.
- **No image generation available**: Skip portrait, use placeholder.
- **No appearance data**: Skip portrait entirely — don't generate a generic one.

### Security
- **Never execute arbitrary code** from `.hermes` files.
- **Read-only access** — never modify the `.hermes` directory.
- **HTML escape all content** to prevent XSS in the output.

### Performance
- Portrait generation takes 2-5 minutes. Inform the user.
- LLM synthesis takes 10-30 seconds.
- Data collection is instant (< 1 second).

## Summary Checklist

Before delivering the character sheet, verify:

- [ ] No appearance section (portrait covers that)
- [ ] Personality section has SEPARATE h3 subsections: Communication, Humor, Philosophy, Music, Tasks, Vibe (NOT merged)
- [ ] ALL skills listed in capabilities (no exclusions)
- [ ] Core Memories: up to 5, no user mentions, agent-internal framing
- [ ] No user profile section present
- [ ] Color palette matches agent aesthetic
- [ ] HTML is self-contained (no external dependencies)
- [ ] CC-BY-SA 4.0 license is in the footer
- [ ] All content is HTML-escaped
- [ ] Output file is valid HTML
