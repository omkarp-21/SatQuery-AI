# Hooks

Place hook scripts here and wire them in [`../settings.json`](../settings.json) under a
`"hooks"` key. Hooks are run by the Claude Code harness, not by the model.

Ideas for this project:

- **PostToolUse (Edit|Write on `backend/**/*.py`)** → run `ruff check --fix` + `black` on the file.
- **PostToolUse (Edit|Write on `frontend/src/**`)** → run `prettier --write` on the file.
- **PreToolUse (Bash)** → block commands that touch `.env`, `models/checkpoints/`, or `data/raw/`.
- **Stop** → run `make lint` and surface failures.

Example wiring in `settings.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [{ "type": "command", "command": "bash .claude/hooks/format.sh" }]
      }
    ]
  }
}
```
