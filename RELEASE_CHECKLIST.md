# Release Checklist — AniListSync

## Version Info
- [ ] `version.py` has the correct version (VERSION, BUILD)
- [ ] `CHANGELOG.md` has the release entry at the top
- [ ] `README.md` roadmap is updated

## Code Quality
- [ ] All `.py` files pass `ast.parse` (no syntax errors)
- [ ] No `print()` debugging statements left in code
- [ ] No hardcoded secrets/tokens in tracked files
- [ ] `config.py` is NOT tracked by git
- [ ] `*.session` files are NOT tracked by git

## Secrets Check
- [ ] No API keys, tokens, or hashes in `config.example.py`
- [ ] No secrets in `CHANGELOG.md`, `README.md`, or any tracked file
- [ ] `git diff` shows only expected changes (no accidental secrets)

## Integrations
- [ ] Telegram: session file exists and client can connect
- [ ] AniList: token valid and connection works
- [ ] MyAnimeList: OAuth tokens valid
- [ ] Discord RPC: plugin enabled and connects (if Discord running)
- [ ] Notifications: toggles/webhook/Telegram push configured

## Plugin Manifests
- [ ] `plugins/discord_rpc/manifest.json` — version bumped, description accurate
- [ ] `plugins/notifications/manifest.json` — version bumped, description accurate
- [ ] `plugins/*/manifest.json` — all plugins have valid JSON

## Build
- [ ] `pip install -r requirements.txt` succeeds
- [ ] App launches without import errors
- [ ] Dashboard displays correctly
- [ ] Sync runs without crashing
- [ ] Exit (option 13) shuts down cleanly (no ResourceWarnings)

## Git
- [ ] `git status` shows only expected modified files
- [ ] Commit message follows repo style
- [ ] Tag name matches version (e.g., `v2.9.0`)
- [ ] Pushed to origin with `--tags`
