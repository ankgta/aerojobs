# Setup guide: getting your job site live

This takes about an hour, spread over a few sittings. You only do it once. Screens on these websites change from time to time, so if a button has a slightly different name, look for the closest match, or ask Claude.

**Never paste passwords or keys into a chat with Claude.** Keys go only into the GitHub "Secrets" page described below.

---

## Step 1. Choose a name and email

1. Pick the site name. Claude can suggest names and check if the domain is free.
2. Create a new Gmail address for the site, for example `hello.yoursitename@gmail.com`. Use it for every account below.

## Step 2. Put the code on GitHub

GitHub stores the code and runs the job fetcher twice a day for free.

1. Go to **github.com** and sign up with the site Gmail.
2. Click the **+** at the top right, then **New repository**.
3. Name it, for example `aviation-jobs`. Choose **Public** (unlimited free running time; the code and job data become visible, which is fine) or **Private** (2,000 free minutes a month, which is enough at the start).
4. Leave everything else unticked and click **Create repository**.
5. **Easiest:** tell Claude the repository's name (for example `yourname/aviation-jobs`) and Claude uploads all the files for you.
   **Or do it yourself:** on the new repository page click **uploading an existing file**, then drag in everything from the unzipped project folder. On a Mac, press **Cmd + Shift + .** in Finder first so the hidden `.github` folder shows up and gets uploaded too.

## Step 3. Create the Cloudflare account and key

Cloudflare hosts the website for free and will later hold your domain.

1. Go to **dash.cloudflare.com** and sign up with the site Gmail.
2. **Find your Account ID:** in the left menu click **Workers & Pages**. The **Account ID** is shown on the right of that page. Click to copy it and keep it in a note for Step 4.
3. **Create a key (API token) for GitHub to publish the site:**
   1. Click the person icon at the top right, then **My Profile**, then **API Tokens**.
   2. Click **Create Token**, then next to **Create Custom Token** click **Get started**.
   3. Token name: `GitHub publish`.
   4. Under **Permissions**, choose **Account**, then **Cloudflare Pages**, then **Edit**.
   5. Click **Continue to summary**, then **Create Token**.
   6. Copy the token. Cloudflare shows it only once.

## Step 4. Give GitHub the keys

1. In your GitHub repository, click **Settings** (top menu of the repository).
2. In the left menu, click **Secrets and variables**, then **Actions**.
3. On the **Secrets** tab, click **New repository secret** and add:
   - Name `CLOUDFLARE_API_TOKEN`, value: the token from Step 3.
   - Name `CLOUDFLARE_ACCOUNT_ID`, value: the Account ID from Step 3.
   - Optional, for AI sorting of unclear job titles: name `ANTHROPIC_API_KEY`, value: a key from **console.anthropic.com** (set a monthly spending limit of $5 there first).
4. On the **Variables** tab, click **New repository variable**: name `CLOUDFLARE_PROJECT`, value `aviation-jobs` (or your site name in lowercase with dashes).

## Step 5. Run it for the first time

1. In the repository, click the **Actions** tab. If asked, click **I understand my workflows, go ahead and enable them**.
2. Click **Update jobs and website** on the left, then **Run workflow**, then the green **Run workflow** button.
3. Wait a few minutes. A green tick means it worked. A red cross means something needs fixing: click it, copy what it says, and paste it to Claude.
4. In Cloudflare, go to **Workers & Pages**. Your project appears there with a free address ending in `.pages.dev`. Open it: that is your live site.

At this stage the site shows no jobs, because no employer has been switched on yet. That is Step 6.

## Step 6. Switch on employers

Ask Claude: "Verify the employer list and switch on the ones that work." Claude checks each employer's careers system, fills in its source in `config/employers.yaml`, and sets `enabled: true`. The next run then collects real jobs.

## Step 7. Your settings

Open `config/site.yaml` on GitHub (click the file, then the pencil icon to edit), change these lines, and click **Commit changes**:

- `site_name`: your chosen name
- `site_url`: your web address, for example `https://www.yoursite.com` (use the `.pages.dev` address until you have a domain)
- `contact_email`: an inbox you check

The site rebuilds by itself within a few minutes of saving.

## Step 8. Your own domain

1. In Cloudflare, click **Domain Registration**, then **Register Domains**, search for your name and buy it (about $10–15 a year).
2. Go to **Workers & Pages**, open your project, click **Custom domains**, then **Set up a custom domain**, and enter your domain.
3. Update `site_url` in `config/site.yaml` to the new address.

## Step 9. Google Search Console and Analytics

1. **Search Console:** go to **search.google.com/search-console**, sign in with the site Gmail, click **Add property**, choose **Domain**, and type your domain. Choose to verify through Cloudflare when offered, and approve it. Then open **Sitemaps** in the left menu and submit `sitemap.xml`.
2. **Analytics:** go to **analytics.google.com**, create an account and a **Web** data stream for your site. Copy the **Measurement ID** (starts with `G-`) into `google_analytics_id` in `config/site.yaml`.

## Step 10. AdSense (2–4 weeks after launch)

Wait until the site has 500+ live jobs, the guides are published, and Google shows some of your pages in search. Then:

1. Go to **adsense.google.com** and sign up with the site Gmail.
2. Add your site. AdSense shows a code containing `ca-pub-` followed by numbers. Copy just that `ca-pub-...` part into `adsense_client` in `config/site.yaml`. The site then adds the AdSense code to every page and creates the `ads.txt` file AdSense asks for.
3. In AdSense, open **Privacy & messaging** and set up the **European regulations** message (Google's own consent banner for visitors from Europe and the UK).
4. Click **Request review**. Approval usually takes from a few days to a few weeks.
5. Once approved, turn on **Auto ads** in AdSense. Google then places ads automatically; no code changes needed.

---

## If something goes wrong

- **You get an email about an issue called "Job fetcher needs attention".** An employer's careers site changed or blocked the fetcher. The other employers still update normally. Forward it to Claude.
- **A run shows a red cross.** Open it, copy the red error text, and paste it to Claude.
- **"Permission denied" when saving job data.** In the repository, go to **Settings**, **Actions**, **General**, and under **Workflow permissions** choose **Read and write permissions**, then **Save**.
