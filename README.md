# Claude Code Skills

A collection of custom skills for [Claude Code](https://claude.ai/code) — drop these into `~/.claude/skills/` to extend Claude with new capabilities.

## What are Skills?

Skills are slash commands you can invoke in Claude Code via `/skill-name`. Each skill bundles a prompt definition (`SKILL.md`) and optional helper scripts that Claude can execute to complete the task.

## Skills

### [`video-notes`](./video-notes/)

Transcribe a local video file and produce structured Markdown notes — all in one command.

**What it does:**
- Extracts audio from any video format (via ffmpeg)
- Transcribes speech using [OpenAI Whisper](https://github.com/openai/whisper) (local, offline)
- Generates a timestamped SRT subtitle file
- Produces a Markdown note with metadata, summary, key takeaways, and full transcript

**Invoke in Claude Code:**
```
/video-notes D:/videos/my-lecture.mp4 --lang zh --title "My Lecture" --category "Courses"
```

**Dependencies:** Python, ffmpeg, `openai-whisper` (auto-installed on first run)

---

## Installation

1. Clone this repo into your Claude skills directory:
   ```bash
   git clone https://github.com/lucius-115/skills ~/.claude/skills-repo
   ```

2. Copy (or symlink) the skill folder you want into `~/.claude/skills/`:
   ```bash
   cp -r ~/.claude/skills-repo/video-notes ~/.claude/skills/
   ```

3. Restart Claude Code — the skill will appear as a `/` command.

## Environment Variables

Some skills require credentials via environment variables (never hardcoded):

| Variable | Used By | Description |
|----------|---------|-------------|
| `BYTEDANCE_APPID` | video-notes | ByteDance ASR App ID (optional, fallback engine) |
| `BYTEDANCE_TOKEN` | video-notes | ByteDance ASR Access Token (optional, fallback engine) |

Set these in your shell profile or a `.env` file that is **not** committed to version control.
