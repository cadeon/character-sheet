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

### LLM Call

Send all collected data to the LLM with this prompt:

```
You are generating content for a character sheet HTML page for a Hermes agent. Based on the raw data collected from their .hermes directory, write polished prose for each section.

RAW DATA:
{json_dump_of_all_collected_data}

RULES:
1. Write in third person, present tense
2. Keep it concise — no fluff
3. Do NOT include raw bullet points or confidence scores
4. HTML-escape all content (< > & " ')
5. If a section has no data, return empty string

STYLE SECTION:
- Examine the raw data and determine what aspects of this agent's character are worth highlighting
- Create h3 subsections for whatever character dimensions exist in the data — communication style, humor, philosophy, aesthetic preferences, work habits, interests, vibe, or anything else the data reveals
- Each subsection: ONE short paragraph (2-3 sentences)
- Do NOT use generic subsection names if the data doesn't support them
- Do NOT invent character traits that aren't in the data
- The goal is to let the agent's actual character emerge from whatever exists in their .hermes directory

CAPABILITIES SECTION:
- Select 8-12 primary/unique capabilities — the most impactful, interesting, or distinctive skills
- Skip generic utility skills (e.g. basic file ops, common dev tools) unless they define the agent
- Format: "<ul><li><strong>skill-name</strong>: description</li>...</ul>"
- Section heading in HTML: "Primary and Unique Capabilities"

ROUTINE SECTION:
- Select 3-5 significant cron jobs — the ones that reveal what the agent actually does
- Skip maintenance/heartbeat tasks
- Format: "<ul><li><strong>name</strong> ({schedule}): desc</li>...</ul>"

Return JSON:
{
  "style": "<h3>Subsection</h3><p>...</p>... (dynamic subsections based on data)",
  "capabilities": "<ul><li><strong>skill-name</strong>: description</li>...</ul>",
  "routine": "<ul><li><strong>name</strong> ({schedule}): desc</li>...</ul>" or empty string
}
```

### Fallback

If the LLM call fails, use raw data with minimal formatting.

## Phase 3: Portrait

Generate a fresh passport-style bust portrait. **Never use existing images.**

Use whatever image generation system you have available — ComfyUI, a local model, an API, or another tool. The goal is a clean, front-facing bust portrait that matches the agent's described appearance or aesthetic.

### Portrait Prompt Guidelines

Build a prompt from any appearance or aesthetic data found:
- Include physical traits if available (hair, eyes, face, body type)
- Include clothing/style preferences if available
- Composition: headshot, bust portrait, upper body only, front-facing, neutral expression, direct gaze
- Background: plain, dark, studio lighting
- Style: illustration, digital art, or match the agent's aesthetic

### If No Image Generation Available

Skip portrait generation. The HTML template has a placeholder that shows "No portrait generated."

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
  /* ... full CSS ... */
</style>
</head>
<body>
<div class="sheet">
  <!-- Header: portrait + name + tagline + quote -->
  <!-- Stats bar: sessions, messages, skills, cron jobs, agent creation date -->
  <!-- Style section: LLM-synthesized prose with dynamic h3 subsections -->
  <!-- Capabilities section: 8-12 primary/unique skills -->
  <!-- Routine section: 3-5 significant cron jobs -->
  <!-- Footer: generation timestamp + CC-BY-SA 4.0 -->
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

- [ ] No appearance section (portrait covers visual representation)
- [ ] Style section has DYNAMIC subsections discovered from data (not hardcoded)
- [ ] Capabilities limited to 8-12 primary/unique skills (section: "Primary and Unique Capabilities")
- [ ] Routine: 3-5 significant cron jobs, maintenance/heartbeat excluded
- [ ] Stats bar includes agent creation date (earliest session/file)
- [ ] No user profile section present
- [ ] Color palette matches agent aesthetic
- [ ] HTML is self-contained (no external dependencies)
- [ ] CC-BY-SA 4.0 license is in the footer
- [ ] All content is HTML-escaped
- [ ] Output file is valid HTML
