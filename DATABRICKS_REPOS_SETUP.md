# Databricks Repos Setup - Step-by-Step Guide

## What is Databricks Repos?

Databricks Repos is like **Dropbox for code** - it automatically syncs your notebooks, Python files, and documentation between your computer and Databricks workspace.

**Benefits:**
- ✅ **Auto-sync** - Changes appear instantly in Databricks
- ✅ **Version control** - Track all changes, undo mistakes
- ✅ **Team collaboration** - Multiple people can use same code
- ✅ **Backup** - Your code is safe in Git/GitHub
- ✅ **No manual uploads** - Just `git push` and it's synced

---

## Prerequisites (Do This First)

### 1. Install Git (if not already installed)

**Check if you have Git:**
```bash
git --version
```

**If not installed:**

**Mac:**
```bash
# Install using Homebrew
brew install git

# Or download from: https://git-scm.com/download/mac
```

**Windows:**
- Download from: https://git-scm.com/download/windows
- Run installer, use default options

### 2. Create GitHub Account (Free)

1. Go to: https://github.com/signup
2. Create free account
3. Verify your email
4. You're done!

---

## Step 1: Initialize Git Repository (Your Computer)

**Open Terminal/Command Prompt:**

```bash
# Navigate to your migration folder
cd "/Users/archana.krishnamurthy/Downloads/Career & Growth/Cursor/Customer-Work/Catalog Migration"

# Initialize Git
git init

# Check status (should show untracked files)
git status
```

**Expected output:**
```
Initialized empty Git repository...
Untracked files:
  config/
  helpers/
  Bundle/
  notebooks/
  ...
```

---

## Step 2: Add Files to Git

**Add all files:**
```bash
# Stage all files for commit
git add .

# Check what will be committed
git status
```

**Expected output:**
```
Changes to be committed:
  new file:   config/config.yaml
  new file:   helpers/__init__.py
  new file:   Bundle/Bundle_01_Export_and_Transform.ipynb
  ...
```

---

## Step 3: Create First Commit

**Commit your files:**
```bash
# Create commit with message
git commit -m "Initial commit: Modular dashboard migration solution"
```

**Expected output:**
```
[main (root-commit) abc1234] Initial commit: Modular dashboard migration solution
 35 files changed, 5000 insertions(+)
```

---

## Step 4: Create GitHub Repository

### Option A: Via GitHub Website (Easier)

1. **Go to GitHub:** https://github.com
2. **Click "+"** (top right) → **"New repository"**
3. **Fill in details:**
   - Repository name: `dashboard-migration` (or your choice)
   - Description: "Databricks dashboard migration solution"
   - Select: **Private** (recommended) or Public
   - **DO NOT** check "Initialize with README" (you already have files)
4. **Click "Create repository"**

5. **Copy the commands shown** (should look like):
```bash
git remote add origin https://github.com/YOUR-USERNAME/dashboard-migration.git
git branch -M main
git push -u origin main
```

6. **Run those commands** in your terminal:
```bash
# Add GitHub as remote
git remote add origin https://github.com/YOUR-USERNAME/dashboard-migration.git

# Rename branch to main (if needed)
git branch -M main

# Push your code to GitHub
git push -u origin main
```

**Enter your GitHub credentials when prompted.**

### Option B: Via Command Line (Advanced)

```bash
# Using GitHub CLI (if installed)
gh repo create dashboard-migration --private --source=. --remote=origin --push
```

---

## Step 5: Connect Databricks to GitHub

### 5a. Generate GitHub Personal Access Token

1. **Go to GitHub Settings:**
   - Click your profile picture (top right)
   - Click **Settings**
   - Scroll down to **Developer settings** (bottom left)
   - Click **Personal access tokens** → **Tokens (classic)**

2. **Generate new token:**
   - Click **"Generate new token (classic)"**
   - Note: `Databricks Repos Access`
   - Expiration: `No expiration` or `90 days`
   - Select scopes:
     - ✅ `repo` (all checkboxes under it)
   - Click **"Generate token"**

3. **Copy the token immediately!**
   - You won't see it again
   - Save it somewhere safe (like password manager)
   - Format: `ghp_xxxxxxxxxxxxxxxxxxxx`

### 5b. Connect Databricks to GitHub

1. **Open Databricks Workspace:**
   - Go to: https://e2-demo-field-eng.cloud.databricks.com

2. **Go to User Settings:**
   - Click your profile icon (top right)
   - Click **User Settings**

3. **Connect Git:**
   - Click **Git Integration** tab
   - Under "Git provider", select **GitHub**
   - Click **Connect to Git**
   - Paste your Personal Access Token
   - Click **Save**

**You should see:** "✅ Connected to GitHub"

---

## Step 6: Add Repo to Databricks

### In Databricks Workspace:

1. **Click "Repos"** in left sidebar
   - (Icon looks like a folder with a branch)

2. **Click "Add Repo"** button

3. **Fill in the form:**
   - **Git repository URL:** 
     ```
     https://github.com/YOUR-USERNAME/dashboard-migration
     ```
   - **Git provider:** GitHub
   - **Repository name:** (auto-fills, keep as is)
   - **Path:** `/Repos/YOUR-EMAIL/dashboard-migration`

4. **Click "Create Repo"**

**Wait 5-10 seconds...**

✅ **Success!** You should see:
- Your repo name in the left sidebar
- All your folders: `config/`, `helpers/`, `Bundle/`, `notebooks/`
- All your files visible in Databricks!

---

## Step 7: Verify It Works

### In Databricks:

1. **Navigate to your repo:**
   - Repos → dashboard-migration → Bundle/

2. **Open a notebook:**
   - Click `Bundle_01_Export_and_Transform.ipynb`
   - Notebook should open with all your code!

3. **Check helper files:**
   - Navigate to `helpers/`
   - You should see all `.py` files
   - Navigate to `config/`
   - You should see `config.yaml`

**Everything is synced! 🎉**

---

## How to Use Databricks Repos

### Making Changes on Your Computer:

```bash
# 1. Edit files locally (in Cursor, VSCode, etc.)
# 2. Commit changes
git add .
git commit -m "Updated config settings"

# 3. Push to GitHub
git push

# 4. In Databricks, click the refresh icon or:
#    - Go to your Repo
#    - Click "..." menu (top right)
#    - Click "Pull"
#
# Changes appear instantly in Databricks!
```

### Making Changes in Databricks:

```bash
# 1. Edit files in Databricks (notebooks, Python files, etc.)
# 2. In Databricks Repo:
#    - Click "..." menu
#    - Click "Commit and Push"
#    - Enter commit message
#    - Click "Commit"
#
# 3. On your computer, pull changes:
git pull

# Changes appear on your computer!
```

### Two-Way Sync:

```
Your Computer  ←→  GitHub  ←→  Databricks
    ↓                ↓            ↓
  Edit           git push     Auto-updates
   ↓                ↓            ↓
git commit       Syncs        Pull changes
   ↓
git push
```

---

## Running Your Notebooks

### In Databricks Repos:

1. **Navigate to Bundle approach:**
   ```
   Repos → dashboard-migration → Bundle → Bundle_01_Export_and_Transform.ipynb
   ```

2. **The notebook imports will work!**
   ```python
   # This now works because helpers/ is in the Repo
   sys.path.insert(0, '../helpers')
   from helpers import load_config, discover_dashboards
   ```

3. **Config file loads automatically:**
   ```python
   # This works because config/config.yaml is in the Repo
   config = load_config('../config/config.yaml')
   ```

**Everything just works!** No manual uploads needed.

---

## Common Questions

### Q: Do I need to sync manually?

**A:** No! Once set up:
- Push to Git → Auto-appears in Databricks
- Pull from Git → Auto-updates on computer
- Edit in Databricks → Commit and push → Auto-updates Git

### Q: Can multiple people use the same Repo?

**A:** Yes! Perfect for teams:
1. Add collaborators to your GitHub repo
2. They clone the repo in their Databricks workspace
3. Everyone works on same code
4. Git handles version control

### Q: What if I make conflicting changes?

**A:** Git will:
1. Detect conflicts
2. Ask you to resolve them
3. You choose which version to keep
4. Commit the resolution

### Q: Can I use private repos?

**A:** Yes! 
- Keep your code private
- Only you (and collaborators) can access
- Same functionality

### Q: What happens if GitHub is down?

**A:** 
- You can still work in Databricks
- Changes save locally in workspace
- Push/pull when GitHub is back

### Q: Do I need GitHub specifically?

**A:** No! Databricks Repos supports:
- ✅ GitHub
- ✅ GitLab
- ✅ Azure DevOps
- ✅ Bitbucket
- ✅ AWS CodeCommit

---

## Troubleshooting

### Error: "Authentication failed"

**Fix:**
1. Go to Databricks User Settings → Git Integration
2. Generate new GitHub Personal Access Token
3. Update token in Databricks
4. Try again

### Error: "Repository not found"

**Fix:**
1. Check GitHub URL is correct
2. Ensure repo is created in GitHub
3. Verify you have access to the repo
4. Check token has `repo` scope

### Error: "Conflict detected"

**Fix:**
```bash
# On your computer
git pull
# Resolve conflicts in files
git add .
git commit -m "Resolved conflicts"
git push
```

### Can't see changes in Databricks

**Fix:**
1. In Databricks Repo, click "..." menu
2. Click "Pull"
3. Changes should appear

### Can't see changes on computer

**Fix:**
```bash
git pull
```

---

## Quick Reference Card

### Essential Commands:

```bash
# First-time setup
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/USER/REPO.git
git push -u origin main

# Daily workflow
git add .                          # Stage changes
git commit -m "Your message"       # Commit changes
git push                           # Upload to GitHub
git pull                           # Download from GitHub
git status                         # Check status
```

### In Databricks:

- **Pull changes:** Repo menu → Pull
- **Commit & Push:** Repo menu → Commit and Push
- **View history:** Repo menu → History

---

## Next Steps

Once Repos is set up:

1. ✅ **Edit** `config/config.yaml` (in Databricks or locally)
2. ✅ **Run** `Bundle/Bundle_01_Export_and_Transform.ipynb`
3. ✅ **Run** `Bundle/Bundle_02_Generate_and_Deploy.ipynb`
4. ✅ **Make changes** - They auto-sync!

**No more manual uploads! Everything just works! 🚀**

---

## Alternative: Still Want to Use Sync Script?

If Repos seems complicated, you can still use the sync script:

```bash
cd "/Users/archana.krishnamurthy/Downloads/Career & Growth/Cursor/Customer-Work/Catalog Migration"

# Configure Databricks CLI once
databricks configure --token --profile e2-demo-field-eng

# Sync files
python sync_to_databricks.py

# Or use bash version
./sync_to_databricks.sh
```

**But Repos is better because:**
- No manual syncing needed
- Version control included
- Team collaboration easy
- Industry standard practice

---

## Support

**Need help?**
- GitHub docs: https://docs.github.com/en/get-started
- Databricks Repos: https://docs.databricks.com/repos/index.html
- Git tutorial: https://git-scm.com/book/en/v2

**Still stuck?** Follow the TESTING_GUIDE.md and use sync script for now. Set up Repos later when ready.
