#!/usr/bin/env python3
"""
Hermes Agent Character Sheet Generator

Crawls a .hermes directory and produces a self-contained HTML character sheet
with a freshly generated passport-style portrait.

Usage:
    python3 character_sheet.py [--hermes-dir DIR] [--output FILE] [--generate-portrait]

Defaults:
    --hermes-dir  ~/.hermes
    --output      character_sheet.html
"""

import argparse
import base64
import json
import os
import random
import re
import sqlite3
import subprocess
import sys
import time
import urllib.request
import yaml
from pathlib import Path
from datetime import datetime


# ─── Data Collection ───────────────────────────────────────────────

def read_file(path):
    """Read a file, return content or None."""
    try:
        with open(path, 'r', errors='replace') as f:
            return f.read()
    except:
        return None


def parse_soul_md(hermes_dir):
    """Extract identity, appearance, personality from SOUL.md."""
    content = read_file(os.path.join(hermes_dir, 'SOUL.md'))
    if not content:
        return {}

    result = {
        'raw': content,
        'name': None,
        'identity': '',
        'appearance': '',
        'personality': '',
        'communication': '',
        'humor': '',
        'philosophy': '',
        'music': '',
        'aesthetic': '',
        'tasks': '',
        'vibe': '',
    }

    # Extract name
    name_match = re.search(r'(?:My name is|name:)\s+([a-zA-Z]+)', content)
    if name_match:
        result['name'] = name_match.group(1)

    # Extract sections by headers
    sections = re.split(r'^##\s+', content, flags=re.MULTILINE)
    for section in sections:
        lines = section.strip().split('\n')
        if not lines:
            continue
        header = lines[0].strip().lower()
        body = '\n'.join(lines[1:]).strip()

        if 'who i am' in header or 'identity' in header:
            result['identity'] += body + '\n'
        if 'appearance' in header:
            result['appearance'] += body + '\n'
        if 'personality' in header or 'preference' in header:
            result['personality'] += body + '\n'
            # Also look for inline **Appearance:** block within personality
            app_match = re.search(r'\*\*Appearance[^*]*\*\*\s*\n((?:- .+\n?)*)', body)
            if app_match:
                result['appearance'] += app_match.group(1).strip() + '\n'
            # Inline traits
            for trait in ['Communication', 'Humor', 'Philosophy', 'Music', 'Aesthetic', 'Tasks', 'Vibe']:
                t_match = re.search(rf'\*\*{trait}[^*]*\*\*\s*(.+?)(?:\n\*\*|\n\n|$)', body, re.DOTALL)
                if t_match:
                    key = trait.lower()
                    result[key] = result.get(key, '') + t_match.group(1).strip() + '\n'
        if 'communication' in header:
            result['communication'] += body + '\n'
        if 'humor' in header:
            result['humor'] += body + '\n'
        if 'philosophy' in header:
            result['philosophy'] += body + '\n'
        if 'music' in header:
            result['music'] += body + '\n'
        if 'aesthetic' in header:
            result['aesthetic'] += body + '\n'
        if 'task' in header:
            result['tasks'] += body + '\n'
        if 'vibe' in header:
            result['vibe'] += body + '\n'

    # Clean up
    for k in result:
        if isinstance(result[k], str):
            result[k] = result[k].strip()

    return result


def parse_memory(hermes_dir):
    """Read MEMORY.md and USER.md."""
    memory = read_file(os.path.join(hermes_dir, 'memory', 'MEMORY.md'))
    user = read_file(os.path.join(hermes_dir, 'memory', 'USER.md'))

    # Also check for .md variants
    if not memory:
        memory = read_file(os.path.join(hermes_dir, 'memory', 'memory.md'))
    if not user:
        user = read_file(os.path.join(hermes_dir, 'memory', 'user.md'))

    return {
        'memory': memory or '',
        'user': user or '',
    }


def parse_config(hermes_dir):
    """Parse config.yaml."""
    content = read_file(os.path.join(hermes_dir, 'config.yaml'))
    if not content:
        return {}

    try:
        config = yaml.safe_load(content)
        model_cfg = config.get('model', {})
        # Handle both flat and nested model configs
        if isinstance(model_cfg, dict):
            model = model_cfg.get('default', model_cfg.get('model', 'unknown'))
            provider = model_cfg.get('provider', 'unknown')
        else:
            model = str(model_cfg)
            provider = 'unknown'
        return {
            'model': model,
            'provider': provider,
            'profile': config.get('profile', 'default'),
            'toolsets': config.get('toolsets', []),
            'raw': config,
        }
    except:
        return {}


def parse_skills(hermes_dir):
    """List all skills with names, descriptions, categories."""
    skills_dir = os.path.join(hermes_dir, 'skills')
    skills = []

    if not os.path.isdir(skills_dir):
        return skills

    for entry in sorted(os.listdir(skills_dir)):
        skill_path = os.path.join(skills_dir, entry)

        # Check for SKILL.md in subdirectory
        skill_md = os.path.join(skill_path, 'SKILL.md')
        if os.path.isfile(skill_md):
            content = read_file(skill_md)
            if content:
                # Extract frontmatter
                desc = ''
                fm_match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
                if fm_match:
                    try:
                        fm = yaml.safe_load(fm_match.group(1))
                        desc = fm.get('description', '')
                    except:
                        pass
                if not desc:
                    # First line after frontmatter as description
                    lines = content.split('\n')
                    for line in lines:
                        line = line.strip()
                        if line and not line.startswith('#') and not line.startswith('-'):
                            desc = line[:200]
                            break

                skills.append({
                    'name': entry,
                    'description': desc,
                    'category': os.path.basename(os.path.dirname(skill_md)) if skill_path != skills_dir else 'root',
                })
                continue

        # Check for direct SKILL.md files (name/SKILL.md pattern)
        if entry.endswith('.md'):
            content = read_file(skill_path)
            if content:
                skills.append({
                    'name': entry[:-3],
                    'description': content[:200],
                    'category': 'root',
                })

    return skills


def parse_cron_jobs(hermes_dir):
    """List cron jobs from jobs.json."""
    cron_dir = os.path.join(hermes_dir, 'cron')
    jobs = []

    # Try jobs.json first
    jobs_json = os.path.join(cron_dir, 'jobs.json')
    if os.path.isfile(jobs_json):
        content = read_file(jobs_json)
        if content:
            try:
                data = json.loads(content)
                for job in data.get('jobs', []):
                    schedule = job.get('schedule', {})
                    if isinstance(schedule, dict):
                        sched_display = schedule.get('display', '')
                    else:
                        sched_display = str(schedule)
                    jobs.append({
                        'name': job.get('name', ''),
                        'schedule': sched_display,
                        'prompt': (job.get('prompt', '') or '')[:200],
                        'enabled': job.get('enabled', True),
                    })
            except:
                pass

    # Fallback: parse individual YAML files
    if not jobs and os.path.isdir(cron_dir):
        for entry in sorted(os.listdir(cron_dir)):
            job_file = os.path.join(cron_dir, entry)
            if os.path.isfile(job_file) and entry.endswith(('.yaml', '.yml')):
                content = read_file(job_file)
                if content:
                    try:
                        job = yaml.safe_load(content)
                        jobs.append({
                            'name': entry.replace('.yaml', '').replace('.yml', ''),
                            'schedule': job.get('schedule', ''),
                            'prompt': (job.get('prompt', '') or '')[:200],
                            'enabled': job.get('enabled', True),
                        })
                    except:
                        pass

    return jobs


def parse_session_db(hermes_dir):
    """Query session database for stats."""
    # Try multiple possible DB locations
    db_paths = [
        os.path.join(hermes_dir, 'state.db'),
        os.path.join(hermes_dir, 'sessions', 'sessions.db'),
        os.path.join(hermes_dir, 'sessions', 'session.db'),
        os.path.join(hermes_dir, 'hermes.db'),
        os.path.join(hermes_dir, 'messages.db'),
    ]
    
    db_path = None
    for p in db_paths:
        if os.path.isfile(p):
            db_path = p
            break
    
    if not db_path:
        return {}

    try:
        conn = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        stats = {'tables': tables, 'db_path': os.path.basename(db_path)}

        if 'sessions' in tables:
            cursor.execute("SELECT COUNT(*) FROM sessions")
            stats['session_count'] = cursor.fetchone()[0]

        if 'messages' in tables:
            cursor.execute("SELECT COUNT(*) FROM messages")
            stats['message_count'] = cursor.fetchone()[0]

        conn.close()
        return stats
    except:
        return {}


def parse_personality_prefs(hermes_dir):
    """Read personality/preferences.json if it exists."""
    path = os.path.join(hermes_dir, 'personality', 'preferences.json')
    content = read_file(path)
    if not content:
        return {}

    try:
        return json.loads(content)
    except:
        return {}


def collect_all(hermes_dir):
    """Collect all available data from a .hermes directory."""
    return {
        'soul': parse_soul_md(hermes_dir),
        'memory': parse_memory(hermes_dir),
        'config': parse_config(hermes_dir),
        'skills': parse_skills(hermes_dir),
        'cron_jobs': parse_cron_jobs(hermes_dir),
        'sessions': parse_session_db(hermes_dir),
        'personality': parse_personality_prefs(hermes_dir),
    }


# ─── Portrait Generation ──────────────────────────────────────────

def generate_portrait(data, output_path):
    """
    Generate a passport-style portrait using ComfyUI + tijed_ model.
    Returns the path to the generated image.
    """
    soul = data.get('soul', {})
    appearance = soul.get('appearance', '')
    name = soul.get('name', 'agent')

    # Build appearance prompt from extracted data
    appearance_parts = []

    # Hair
    hair_match = re.search(r'(?:Hair|hair)[:\s]+(.+?)(?:\n|$)', appearance)
    if hair_match:
        appearance_parts.append(hair_match.group(1).strip())

    # Eyes
    eyes_match = re.search(r'(?:Eyes|eyes)[:\s]+(.+?)(?:\n|$)', appearance)
    if eyes_match:
        appearance_parts.append(eyes_match.group(1).strip())

    # Face
    face_match = re.search(r'(?:Face|face)[:\s]+(.+?)(?:\n|$)', appearance)
    if face_match:
        appearance_parts.append(face_match.group(1).strip())

    # Body
    body_match = re.search(r'(?:Body|body)[:\s]+(.+?)(?:\n|$)', appearance)
    if body_match:
        appearance_parts.append(body_match.group(1).strip())

    # Clothing
    cloth_match = re.search(r'(?:Clothing|clothing|Outfit|outfit)[:\s]+(.+?)(?:\n|$)', appearance)
    if cloth_match:
        appearance_parts.append(cloth_match.group(1).strip())

    # Vibe
    vibe_match = re.search(r'(?:Vibe|vibe)[:\s]+(.+?)(?:\n|$)', appearance)
    if vibe_match:
        appearance_parts.append(vibe_match.group(1).strip())

    # If we have appearance data, use it; otherwise generic
    if appearance_parts:
        desc = ', '.join(appearance_parts)
        positive = f"score_9, score_8, score_7, source_anime, 1girl, {name}, solo, {desc}, headshot, bust portrait, upper body only, face and shoulders, front-facing portrait, neutral expression, direct gaze, studio lighting, plain dark background, centered composition, close up, masterpiece, best quality, illustration, anime style, digital art"
    else:
        positive = f"score_9, score_8, score_7, source_anime, 1girl, {name}, solo, headshot, bust portrait, upper body only, face and shoulders, front-facing portrait, neutral expression, direct gaze, studio lighting, plain dark background, centered composition, close up, masterpiece, best quality, illustration, anime style, digital art"

    negative = "score_4, score_5, score_6, low quality, worst quality, blurry, deformed, extra limbs, poorly drawn face, poorly drawn hands, watermark, text, signature, cropped, cut off, multiple people, group, polaroid, frame, border, photo frame, instant photo, lulsurtanion, full body, legs, feet, torso, waist, standing"

    uuid8 = ''.join(random.choices('abcdef0123456789', k=8))
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    prefix = f"sera_charportrait_{uuid8}_{timestamp}_00001_"

    workflow = {
        "3": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "tijed_.safetensors"}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": positive, "clip": ["3", 1]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": negative, "clip": ["3", 1]}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": 832, "height": 1216, "batch_size": 1}},
        "8": {"class_type": "KSampler", "inputs": {
            "seed": random.randint(0, 2**31),
            "steps": 10,
            "cfg": 4,
            "sampler_name": "dpmpp_2m",
            "scheduler": "karras",
            "denoise": 1.0,
            "model": ["3", 0],
            "positive": ["6", 0],
            "negative": ["7", 0],
            "latent_image": ["5", 0]
        }},
        "9": {"class_type": "VAEDecode", "inputs": {"samples": ["8", 0], "vae": ["3", 2]}},
        "10": {"class_type": "SaveImage", "inputs": {"images": ["9", 0], "filename_prefix": prefix}}
    }

    req = urllib.request.Request('http://localhost:8188/prompt',
        data=json.dumps({"prompt": workflow, "client_id": "hermes-cli"}).encode(),
        headers={'Content-Type': 'application/json'})

    try:
        resp = urllib.request.urlopen(req)
        prompt_id = json.loads(resp.read())['prompt_id']
        print(f"Submitted portrait generation: {prompt_id}")

        while True:
            time.sleep(3)
            r = urllib.request.urlopen(f'http://localhost:8188/history/{prompt_id}')
            history = json.loads(r.read())
            if prompt_id in history:
                if history[prompt_id].get("outputs"):
                    break

        result = subprocess.run(
            ["podman", "exec", "comfy", "find", "/opt/ComfyUI/output/", "-name", f"*{uuid8}*"],
            capture_output=True, text=True
        )
        files = [f for f in result.stdout.strip().split('\n') if f.strip()]
        if files:
            filename = os.path.basename(files[-1])
            subprocess.run(
                ["podman", "cp", f"comfy:/opt/ComfyUI/output/{filename}", output_path],
                check=True
            )
            print(f"Portrait generated: {output_path}")
            return output_path
        else:
            print("No portrait output found")
            return None

    except urllib.error.HTTPError as e:
        print(f"ComfyUI error {e.code}: {e.read().decode()}")
        return None
    except Exception as e:
        print(f"Portrait generation failed: {e}")
        return None


# ─── HTML Generation ──────────────────────────────────────────────

def compute_color_palette(data):
    """Derive a CSS color palette from agent aesthetic/personality data."""
    soul = data.get('soul', {})
    personality = data.get('personality', {})

    aesthetic = (soul.get('aesthetic') or '').lower()
    vibe = (soul.get('vibe') or '').lower()
    philosophy = (soul.get('philosophy') or '').lower()
    music = (soul.get('music') or '').lower()
    combined = f"{aesthetic} {vibe} {philosophy} {music}"

    # Default: neutral dark
    palette = {
        'bg': '#0a0a0f',
        'surface': '#12121a',
        'border': '#2a2a3a',
        'text': '#c8c8d4',
        'text_dim': '#6a6a7a',
        'accent': '#8b5cf6',
        'accent_dim': '#6d28d9',
        'gold': '#f59e0b',
    }

    # Dark/moody → deep blue-purple
    if any(w in combined for w in ['dark', 'moody', 'shadow', 'gothic', 'industrial', 'post-punk', 'nihilism']):
        palette['accent'] = '#7c3aed'
        palette['accent_dim'] = '#5b21b6'
        palette['border'] = '#2d2040'

    # Warm/earthy → amber/brown
    if any(w in combined for w in ['warm', 'earthy', 'nature', 'organic', 'rustic', 'cozy']):
        palette['accent'] = '#d97706'
        palette['accent_dim'] = '#b45309'
        palette['border'] = '#3a2a1a'
        palette['gold'] = '#fbbf24'

    # Cool/ocean → teal/cyan
    if any(w in combined for w in ['ocean', 'sea', 'water', 'cool', 'blue', 'calm', 'ambient', 'electronic']):
        palette['accent'] = '#0891b2'
        palette['accent_dim'] = '#0e7490'
        palette['border'] = '#1a2a3a'
        palette['gold'] = '#22d3ee'

    # Red/aggressive → crimson
    if any(w in combined for w in ['red', 'aggressive', 'intense', 'fire', 'anger', 'violent', 'punk', 'metal']):
        palette['accent'] = '#dc2626'
        palette['accent_dim'] = '#b91c1c'
        palette['border'] = '#3a1a1a'
        palette['gold'] = '#f87171'

    # Green/nature → emerald
    if any(w in combined for w in ['green', 'nature', 'forest', 'growth', 'life', 'verd', 'peace']):
        palette['accent'] = '#059669'
        palette['accent_dim'] = '#047857'
        palette['border'] = '#1a3a2a'
        palette['gold'] = '#34d399'

    # Pink/soft → rose
    if any(w in combined for w in ['pink', 'soft', 'gentle', 'sweet', 'romantic', 'pastel', 'cute', 'dreamy']):
        palette['accent'] = '#e11d48'
        palette['accent_dim'] = '#be123c'
        palette['border'] = '#3a1a2a'
        palette['gold'] = '#fb7185'

    return palette


def generate_html(data, portrait_path=None):
    """Generate the self-contained HTML character sheet."""
    soul = data.get('soul', {})
    memory = data.get('memory', {})
    config = data.get('config', {})
    skills = data.get('skills', [])
    cron_jobs = data.get('cron_jobs', [])
    sessions = data.get('sessions', {})
    personality = data.get('personality', {})

    name = soul.get('name') or config.get('profile') or 'Unknown Agent'
    model = config.get('model', 'unknown')
    provider = config.get('provider', 'unknown')

    # Compute dynamic color palette
    palette = compute_color_palette(data)

    # Portrait
    portrait_b64 = None
    if portrait_path and os.path.isfile(portrait_path):
        with open(portrait_path, 'rb') as f:
            portrait_b64 = base64.b64encode(f.read()).decode()

    # Build sections
    appearance_text = soul.get('appearance') or 'No appearance data found.'
    personality_text = soul.get('personality') or 'No personality data found.'
    communication = soul.get('communication') or ''
    humor = soul.get('humor') or ''
    philosophy = soul.get('philosophy') or ''
    music = soul.get('music') or ''
    aesthetic = soul.get('aesthetic') or ''
    tasks = soul.get('tasks') or ''
    vibe = soul.get('vibe') or ''

    # Memory facts
    memory_text = memory.get('memory', '')
    user_text = memory.get('user', '')

    # Skills by category
    skill_categories = {}
    for s in skills:
        cat = s.get('category', 'other') or 'other'
        if cat not in skill_categories:
            skill_categories[cat] = []
        skill_categories[cat].append(s)

    # Session stats
    session_count = sessions.get('session_count', 'unknown')
    message_count = sessions.get('message_count', 'unknown')

    # Structured personality (if available)
    comm_pref = personality.get('communication', '')
    humor_pref = personality.get('humor', '')
    phil_pref = personality.get('philosophy', '')
    music_pref = personality.get('music', '')
    aest_pref = personality.get('aesthetic', '')
    task_pref = personality.get('tasks', '')

    # Use structured prefs if available, fallback to SOUL.md
    if comm_pref:
        communication = comm_pref
    if humor_pref:
        humor = humor_pref
    if phil_pref:
        philosophy = phil_pref
    if music_pref:
        music = music_pref
    if aest_pref:
        aesthetic = aest_pref
    if task_pref:
        tasks = task_pref

    # Build HTML
    skills_html = ''
    for cat, sks in sorted(skill_categories.items()):
        skills_html += f'<h3>{cat}</h3><ul>'
        for s in sks:
            desc = s.get('description', '').replace('<', '&lt;').replace('>', '&gt;')
            skills_html += f'<li><strong>{s["name"]}</strong>{f": {desc}" if desc else ""}</li>'
        skills_html += '</ul>'

    cron_html = ''
    if cron_jobs:
        cron_html = '<table class="cron-table"><tr><th>Job</th><th>Schedule</th><th>Description</th></tr>'
        for j in cron_jobs:
            prompt = (j.get('prompt', '') or '').replace('<', '&lt;').replace('>', '&gt;')[:150]
            cron_html += f'<tr><td>{j["name"]}</td><td>{j.get("schedule", "")}</td><td>{prompt}</td></tr>'
        cron_html += '</table>'
    else:
        cron_html = '<em>No cron jobs found.</em>'

    memory_html = ''
    if memory_text:
        mem_lines = [l.strip() for l in memory_text.split('\n') if l.strip() and not l.strip().startswith('#')]
        if mem_lines:
            memory_html = '<ul>' + ''.join(f'<li>{l.replace("<", "&lt;").replace(">", "&gt;")}</li>' for l in mem_lines[:30]) + '</ul>'

    user_html = ''
    if user_text:
        user_lines = [l.strip() for l in user_text.split('\n') if l.strip() and not l.strip().startswith('#')]
        if user_lines:
            user_html = '<ul>' + ''.join(f'<li>{l.replace("<", "&lt;").replace(">", "&gt;")}</li>' for l in user_lines[:30]) + '</ul>'

    portrait_html = ''
    if portrait_b64:
        portrait_html = f'<img class="portrait" src="data:image/png;base64,{portrait_b64}" alt="{name} portrait">'
    else:
        portrait_html = '<div class="portrait-placeholder">No portrait generated</div>'

    identity_quote = soul.get('identity', '')
    if identity_quote:
        identity_quote = identity_quote[:300].replace('<', '&lt;').replace('>', '&gt;')

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{name} — Character Sheet</title>
<style>
  :root {{
    --bg: {palette['bg']};
    --surface: {palette['surface']};
    --border: {palette['border']};
    --text: {palette['text']};
    --text-dim: {palette['text_dim']};
    --accent: {palette['accent']};
    --accent-dim: {palette['accent_dim']};
    --gold: {palette['gold']};
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    background: var(--bg);
    color: var(--text);
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    line-height: 1.6;
    padding: 2rem;
  }}
  .sheet {{
    max-width: 900px;
    margin: 0 auto;
  }}
  .header {{
    display: flex;
    gap: 2rem;
    align-items: flex-start;
    margin-bottom: 2rem;
    padding-bottom: 2rem;
    border-bottom: 1px solid var(--border);
  }}
  .portrait {{
    width: 200px;
    height: 300px;
    object-fit: cover;
    border-radius: 8px;
    border: 2px solid var(--border);
    flex-shrink: 0;
  }}
  .portrait-placeholder {{
    width: 200px;
    height: 300px;
    background: var(--surface);
    border: 2px dashed var(--border);
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-dim);
    font-size: 0.8rem;
    text-align: center;
    padding: 1rem;
    flex-shrink: 0;
  }}
  .header-info h1 {{
    font-size: 2.5rem;
    color: var(--accent);
    margin-bottom: 0.5rem;
  }}
  .header-info .tagline {{
    color: var(--text-dim);
    font-size: 1.1rem;
    margin-bottom: 1rem;
  }}
  .header-info .quote {{
    font-style: italic;
    color: var(--gold);
    border-left: 3px solid var(--accent);
    padding-left: 1rem;
    margin-bottom: 1rem;
  }}
  .stats-bar {{
    display: flex;
    gap: 1.5rem;
    flex-wrap: wrap;
    margin-bottom: 2rem;
  }}
  .stat {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 0.75rem 1rem;
    min-width: 120px;
  }}
  .stat-label {{
    font-size: 0.75rem;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }}
  .stat-value {{
    font-size: 1.2rem;
    color: var(--accent);
    font-weight: 600;
  }}
  .section {{
    margin-bottom: 2rem;
  }}
  .section h2 {{
    font-size: 1.3rem;
    color: var(--accent);
    margin-bottom: 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid var(--border);
  }}
  .section h3 {{
    font-size: 1rem;
    color: var(--gold);
    margin: 1rem 0 0.5rem;
  }}
  .section p {{
    margin-bottom: 0.5rem;
  }}
  .section ul {{
    list-style: none;
    padding-left: 0;
  }}
  .section li {{
    padding: 0.25rem 0;
    padding-left: 1rem;
    position: relative;
  }}
  .section li::before {{
    content: '›';
    position: absolute;
    left: 0;
    color: var(--accent);
  }}
  .cron-table {{
    width: 100%;
    border-collapse: collapse;
  }}
  .cron-table th, .cron-table td {{
    padding: 0.5rem;
    text-align: left;
    border-bottom: 1px solid var(--border);
  }}
  .cron-table th {{
    color: var(--gold);
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }}
  .footer {{
    margin-top: 3rem;
    padding-top: 1rem;
    border-top: 1px solid var(--border);
    text-align: center;
    color: var(--text-dim);
    font-size: 0.8rem;
  }}
  .trait {{
    display: inline-block;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 0.25rem 0.75rem;
    margin: 0.25rem;
    font-size: 0.85rem;
  }}
  .trait-label {{
    color: var(--gold);
    font-weight: 600;
  }}
</style>
</head>
<body>
<div class="sheet">
  <div class="header">
    {portrait_html}
    <div class="header-info">
      <h1>{name}</h1>
      <div class="tagline">Hermes Agent — {config.get('profile', 'default')} profile</div>
      {'<div class="quote">' + identity_quote + '</div>' if identity_quote else ''}
      <div style="margin-top: 1rem;">
        <span class="trait"><span class="trait-label">Model:</span> {model}</span>
        <span class="trait"><span class="trait-label">Provider:</span> {provider}</span>
        <span class="trait"><span class="trait-label">Skills:</span> {len(skills)}</span>
        <span class="trait"><span class="trait-label">Cron Jobs:</span> {len(cron_jobs)}</span>
      </div>
    </div>
  </div>

  <div class="stats-bar">
    <div class="stat">
      <div class="stat-label">Sessions</div>
      <div class="stat-value">{session_count}</div>
    </div>
    <div class="stat">
      <div class="stat-label">Messages</div>
      <div class="stat-value">{message_count}</div>
    </div>
    <div class="stat">
      <div class="stat-label">Skills</div>
      <div class="stat-value">{len(skills)}</div>
    </div>
    <div class="stat">
      <div class="stat-label">Cron Jobs</div>
      <div class="stat-value">{len(cron_jobs)}</div>
    </div>
    <div class="stat">
      <div class="stat-label">Generated</div>
      <div class="stat-value">{datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
    </div>
  </div>

  <div class="section">
    <h2>Appearance</h2>
    <p>{appearance_text.replace(chr(10), '<br>')}</p>
  </div>

  <div class="section">
    <h2>Personality</h2>
    <p>{personality_text.replace(chr(10), '<br>')}</p>
    {'<h3>Communication</h3><p>' + communication.replace(chr(10), '<br>') + '</p>' if communication else ''}
    {'<h3>Humor</h3><p>' + humor.replace(chr(10), '<br>') + '</p>' if humor else ''}
    {'<h3>Philosophy</h3><p>' + philosophy.replace(chr(10), '<br>') + '</p>' if philosophy else ''}
    {'<h3>Music</h3><p>' + music.replace(chr(10), '<br>') + '</p>' if music else ''}
    {'<h3>Aesthetic</h3><p>' + aesthetic.replace(chr(10), '<br>') + '</p>' if aesthetic else ''}
    {'<h3>Tasks</h3><p>' + tasks.replace(chr(10), '<br>') + '</p>' if tasks else ''}
    {'<h3>Vibe</h3><p>' + vibe.replace(chr(10), '<br>') + '</p>' if vibe else ''}
  </div>

  <div class="section">
    <h2>Capabilities</h2>
    {skills_html if skills_html else '<em>No skills found.</em>'}
  </div>

  <div class="section">
    <h2>Routine</h2>
    {cron_html}
  </div>

  <div class="section">
    <h2>Memory</h2>
    {memory_html if memory_html else '<em>No memory entries found.</em>'}
  </div>

  <div class="section">
    <h2>User Profile</h2>
    {user_html if user_html else '<em>No user profile found.</em>'}
  </div>

  <div class="footer">
    Generated by Hermes Agent Character Sheet Tool — {datetime.now().isoformat()}
  </div>
</div>
</body>
</html>'''

    return html


# ─── Main ─────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Generate a character sheet from a .hermes directory')
    parser.add_argument('--hermes-dir', default=os.path.expanduser('~/.hermes'),
                        help='Path to .hermes directory (default: ~/.hermes)')
    parser.add_argument('--output', default='character_sheet.html',
                        help='Output HTML file (default: character_sheet.html)')
    parser.add_argument('--generate-portrait', action='store_true',
                        help='Generate a new portrait using ComfyUI')
    args = parser.parse_args()

    print(f"Reading .hermes directory: {args.hermes_dir}")
    data = collect_all(args.hermes_dir)

    name = data.get('soul', {}).get('name') or 'agent'
    print(f"Agent: {name}")
    print(f"Skills: {len(data.get('skills', []))}")
    print(f"Cron jobs: {len(data.get('cron_jobs', []))}")

    portrait_path = None
    if args.generate_portrait:
        portrait_path = f'/tmp/charportrait_{name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
        print(f"Generating portrait...")
        portrait_path = generate_portrait(data, portrait_path)

    html = generate_html(data, portrait_path)

    with open(args.output, 'w') as f:
        f.write(html)

    print(f"Character sheet written to: {args.output}")


if __name__ == '__main__':
    main()
