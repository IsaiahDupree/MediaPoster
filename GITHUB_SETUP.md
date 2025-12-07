# GitHub Setup Guide

## ✅ Security Checklist

Before pushing to GitHub, ensure:

- ✅ `.gitignore` is configured (already done)
- ✅ Sensitive files are excluded:
  - `client_secret*.json` files
  - `Backend/automation/sessions/` directory
  - `Backend/automation/recordings/` directory
  - `.env` files
  - Log files and screenshots

## Quick Push

### Option 1: Using the Safe Push Script

```bash
./.github_push.sh
```

This script will:
1. Check for sensitive files
2. Set up GitHub remote (if needed)
3. Create initial commit (if needed)
4. Push to GitHub safely

### Option 2: Manual Push

1. **Verify sensitive files are ignored**:
   ```bash
   git check-ignore client_secret*.json Backend/automation/sessions/
   ```

2. **Add files**:
   ```bash
   git add .
   ```

3. **Verify no sensitive files in staging**:
   ```bash
   git status | grep -i "secret\|session\|cookie"
   ```

4. **Create initial commit**:
   ```bash
   git commit -m "Initial commit: MediaPoster automation system"
   ```

5. **Add GitHub remote** (if not already added):
   ```bash
   git remote add origin https://github.com/IsaiahDupree/MediaPoster.git
   ```

6. **Push to GitHub**:
   ```bash
   git branch -M main  # Rename branch to main
   git push -u origin main
   ```

## Protected Files

The following are **automatically excluded** by `.gitignore`:

### Credentials
- `**/client_secret*.json`
- `**/*credentials*.json`
- `.env` files

### Session Data
- `Backend/automation/sessions/`
- `Backend/automation/recordings/`
- `**/*_cookies.json`
- `**/*_session.json`

### Other Sensitive Data
- `Backend/logs/`
- `Backend/automation/screenshots/`
- Analytics JSON files

## If You Accidentally Commit Secrets

**If you haven't pushed yet:**
```bash
git rm --cached <file>
git commit --amend
```

**If you already pushed:**
1. **Rotate credentials immediately** (revoke exposed keys)
2. Remove from history (use BFG Repo-Cleaner or git filter-branch)
3. Force push (⚠️ coordinate with team)

## Repository Structure

```
MediaPoster/
├── Backend/
│   ├── automation/          # TikTok automation
│   │   ├── safari_extension/ # Safari Web Extension
│   │   └── sessions/        # ❌ IGNORED (contains cookies)
│   ├── logs/                # ❌ IGNORED
│   └── ...
├── Frontend/
├── .gitignore               # ✅ Protects secrets
├── SECURITY.md              # Security guidelines
└── README.md
```

## Next Steps After Push

1. **Set up GitHub Secrets** (for CI/CD):
   - Go to Settings → Secrets and variables → Actions
   - Add: `GOOGLE_CLIENT_SECRET`, `TIKTOK_API_KEY`, etc.

2. **Create `.env.example`** template:
   ```bash
   # Copy and fill in your values
   cp .env.example .env
   ```

3. **Document setup** in README

## Verification

After pushing, verify on GitHub:
- ✅ No `client_secret*.json` files visible
- ✅ No `sessions/` directory visible
- ✅ No `.env` files visible
- ✅ Code and documentation are present

## Support

See `SECURITY.md` for detailed security guidelines.

