# Hermes Agent Character Sheet Generator

Crawls a `.hermes` directory and produces a self-contained HTML character sheet with a freshly generated portrait.

## Features

- **Fuzzy input** — works against any `.hermes` installation, graceful degradation when data sources are missing
- **Dynamic color scheme** — CSS palette derived from agent aesthetic/personality data
- **Portrait generation** — bust portrait via ComfyUI (tijed_ checkpoint)
- **Self-contained output** — single HTML file, no external dependencies

## Usage

```bash
python3 character_sheet.py [--hermes-dir DIR] [--output FILE] [--generate-portrait]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--hermes-dir` | `~/.hermes` | Path to a `.hermes` directory |
| `--output` | `character_sheet.html` | Output HTML file |
| `--generate-portrait` | off | Generate a new portrait via ComfyUI |

## Data Sources

All sources are optional — the tool degrades gracefully:

- `SOUL.md` — name, personality, appearance, identity quote
- `config.yaml` — model, provider, profile
- `skills/` — SKILL.md files (names, descriptions, categories)
- `cron/jobs.json` — cron job definitions
- `state.db` — session/message counts
- `personality/preferences.json` — structured personality data

## License

CC BY-SA 4.0
