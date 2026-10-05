# Runbook: how to do things

Part 1 is for the owner (clicks in GitHub and Cloudflare). Part 2 is what to ask Claude. Claude's own
step-by-step procedures are the skills in `.claude/skills/`.

## Part 1: things the owner does

### See whether everything is working
1. Open **github.com/ankgta/aerojobs** and click **Actions**.
2. The newest **Update jobs and website** run should have a green tick and be less than 13 hours old.
3. Check the **Issues** tab: an open issue called **Job fetcher needs attention** means an employer needs a
   look. Ask Claude: "Check the open fetcher alert."

### Run the site update now (instead of waiting)
Actions → **Update jobs and website** → **Run workflow** → green **Run workflow** button.

### Run the full website and security tests
Actions → **Test the live website** → **Run workflow**. Takes about 10 minutes. Then ask Claude for the
report.

### Change the site name, contact email or Google IDs
Open `config/site.yaml` on GitHub → pencil icon → change the value on the right → **Commit changes**.
The site rebuilds in about a minute.

### Add a GitHub secret (for example the Anthropic key)
Repository **Settings** → **Secrets and variables** → **Actions** → **New repository secret**. Paste the
value there only, never into a chat.

### Give Claude access to the repository (new Claude account or new connection)
1. In Claude, open **Settings → Connectors** and connect **GitHub**, signing in as **ankgta**.
2. On GitHub, open **github.com/settings/installations** → **Claude** → **Configure** →
   **Only select repositories** → add **aerojobs** → **Save**.

### If a run shows a red cross
Click the run, then the red step, copy the error text and paste it to Claude.

### Cloudflare
- Site and domains: dash.cloudflare.com → **Workers & Pages** → **aerojobs** (Deployments, Custom domains).
- Email forwarding for hello@aerojobs.work: click the domain → **Email** → **Email Routing**.
- Turn off Web Analytics (if decided): **Workers & Pages** → **aerojobs** → **Metrics** → Web Analytics.

### Keep accounts safe
Two-step login (authenticator app) on Gmail, GitHub and Cloudflare. Registrar lock and DNSSEC on the domain
in Cloudflare. Never click your own ads once AdSense is on.

## Part 2: what to ask Claude

| You want | Say |
| --- | --- |
| A health check | "Check AeroJobs is healthy." |
| More employers | "Find and switch on more employers." or "Add <company>." |
| A new hiring system supported | "Build the SuccessFactors reader." |
| A full test and report | "Run the full tests and give me the report." |
| More guides | "Write the next guide about <topic>." |
| A design or filter change | Describe what you see and what you want; screenshots help. |
| To know where things stand | "What's the status?" (Claude reads `docs/STATUS.md`.) |

Claude updates `docs/STATUS.md` after each piece of work, so a new conversation always starts from the
right place.
