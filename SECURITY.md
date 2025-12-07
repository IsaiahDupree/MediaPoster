# Security Guidelines

## Protected Files

The following files and directories are excluded from version control for security reasons:

### Credentials & Secrets
- `**/client_secret*.json` - OAuth client secrets
- `**/*credentials*.json` - Credential files
- `.env` - Environment variables (use `.env.example` as template)

### Session Data
- `Backend/automation/sessions/` - Session files containing cookies and tokens
- `Backend/automation/recordings/` - Login recordings
- `**/*_cookies.json` - Cookie files
- `**/*_session.json` - Session state files

### Browser Profiles
- `Backend/automation/browser_profile_config.json` - Browser profile paths
- `Backend/automation/chrome_profile_config.json` - Chrome profile configs

### Analytics Data
- `Backend/*_analytics_*.json` - Analytics data files
- `Backend/instagram_*.json` - Instagram data
- `Backend/youtube_*.json` - YouTube data

### Screenshots & Logs
- `Backend/automation/screenshots/` - Screenshots
- `Backend/automation/comment_screenshots/` - Comment screenshots
- `Backend/logs/` - Log files
- `*.log` - Log files

## Setup Instructions

1. **Copy environment template**:
   ```bash
   cp .env.example .env
   ```

2. **Fill in your credentials** in `.env` file

3. **Never commit**:
   - `.env` files
   - `client_secret*.json` files
   - Session/cookie files
   - Any file containing API keys or tokens

## If You Accidentally Commit Secrets

If you accidentally commit sensitive data:

1. **Remove from Git history** (if not yet pushed):
   ```bash
   git rm --cached <file>
   git commit -m "Remove sensitive file"
   ```

2. **If already pushed**, you need to:
   - Rotate/revoke the exposed credentials immediately
   - Remove from Git history using `git filter-branch` or BFG Repo-Cleaner
   - Force push (⚠️ coordinate with team first)

3. **Check for exposed secrets**:
   ```bash
   git log --all --full-history -- <file>
   ```

## Best Practices

- ✅ Use `.env` files for local configuration
- ✅ Use `.env.example` as a template (no secrets)
- ✅ Add new secret patterns to `.gitignore`
- ✅ Review `git status` before committing
- ✅ Use GitHub Secrets for CI/CD
- ❌ Never commit API keys, tokens, or passwords
- ❌ Never commit session cookies or authentication data
- ❌ Never commit OAuth client secrets

