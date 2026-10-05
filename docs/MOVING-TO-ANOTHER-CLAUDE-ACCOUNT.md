# Moving AeroJobs to another Claude account

About 20 minutes. Nothing about the website changes: it keeps running on its own the whole time.

## What moves by itself, and what doesn't

| Part | Where it lives | What to do |
| --- | --- | --- |
| Website, domain, hosting | Cloudflare (your account) | Nothing |
| Code, job data, docs, skills | GitHub repository **ankgta/aerojobs** | Nothing; the new Claude account just connects to it |
| Twice-daily updates and alerts | GitHub Actions | Nothing |
| Project instructions and knowledge files | Old Claude account | Recreate from the export package (step 2) |
| Skills | Old Claude account and the repository | Upload the 4 skill files (step 4) |
| Chat history, the old preview page and plan doc | Old Claude account | Not transferable; their content is in the package and the repository |

## Before you start

Have the export package unzipped (`AeroJobs-Export.zip`). You'll use the `1-claude-project`,
`2-skills` and `4-reference` folders.

## Step 1: Turn on code execution (needed for skills)

In the new account: **Settings → Capabilities** → turn on **code execution** (it may be labelled "Code execution and file creation").
(On a Team or Enterprise plan, an admin turns on skills under **Organization settings**.)

## Step 2: Create the project

1. In the left sidebar, open **Projects** → **Create project**. Name: `AeroJobs`. Description:
   `Aviation job board aerojobs.work`.
2. Open the project's **Instructions** (project settings) and paste everything from
   `1-claude-project/project-instructions.txt`.
3. In the project's **Files** (knowledge) area, upload every file in `1-claude-project/knowledge/`.

## Step 3: Connect GitHub

1. **Settings → Connectors** → **GitHub** → **Connect**, and sign in to GitHub as **ankgta**.
2. If GitHub asks which repositories Claude may use, choose **Only select repositories** → **aerojobs**.
3. Check it on GitHub: **github.com/settings/installations** → **Claude** → **Configure** →
   **aerojobs** is listed under Repository access → **Save**.

## Step 4: Upload the skills

For each zip in `2-skills/` (four files):
**Customize → Skills** → **+** → **Create skill** → **Upload a skill** → choose the zip. Then make sure
each skill's switch is **on**.

(When Claude works directly in the repository, it also finds the same skills in `.claude/skills/`.)

## Step 5: First conversation

Start a new chat inside the AeroJobs project and paste:

> Attach my GitHub repository ankgta/aerojobs, read CLAUDE.md and docs/STATUS.md, then tell me in plain
> words where the project stands and what you need from me.

Claude should come back with the live job count, the 10 employers, and the four open decisions. If it
can't reach the repository, repeat step 3.

## Step 6 (optional): the handbook page

`4-reference/AeroJobs-Handbook.html` is a one-page visual overview. Ask Claude in the new account:
"Publish this handbook as an artifact" and attach the file.

## Step 7: Tidy the old account

Once step 5 works: in the old account, **Settings → Connectors → GitHub → Disconnect**, so two accounts
never change the code at the same time. You can keep or delete the old project; nothing depends on it.

## Good to know

- Your GitHub, Cloudflare and Gmail passwords don't change, and Claude never needed them.
- The `3-code` folder is a backup copy of the repository on 5 October 2026. You only need it if the
  GitHub repository is ever lost.
- If something in this guide doesn't match the screens (menus change), ask Claude in the new account;
  it has this guide in its project files.
