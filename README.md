# Haze Check SG

How hazy is Singapore right now, what should you do about it, and how has it changed this week?

A small static website built from NEA's open air-quality data:

- **Latest reading**: the haze level in the worst region, with NEA's health advice for healthy adults, vulnerable groups and people with heart or lung conditions.
- **Region map**: PSI for North, South, East, West and Central, with the towns each region roughly covers.
- **Past week**: the worst reading each day, an hour-by-hour chart, and a replay on the map.
- **What NEA has said**: plain-English summaries of NEA's daily Haze Situation Updates.
- **Explore the data**: Changi weather and how it lines up with the haze.

No framework, no build tooling beyond Python's standard library. The whole site is `public/index.html` plus `public/data.json`.

## Run it locally

```bash
python3 scripts/build.py           # builds public/index.html
python3 -m http.server -d public   # open http://localhost:8000
```

## Update the data

```bash
python3 scripts/fetch.py           # yesterday and today
python3 scripts/fetch.py --days 7  # backfill a week
```

NEA's daily update summaries live in `data/nea.json` and are written by hand (see `CLAUDE.md`). Run `python3 scripts/build.py` after editing them.

Once the repo is on GitHub, `.github/workflows/update-data.yml` fetches new readings at 8:10am and 9:10pm Singapore time and commits them. You can also run it from the **Actions** tab. An optional `DATA_GOV_SG_API_KEY` repo secret raises data.gov.sg's rate limits.

## Deploy

The site is static, so any host works. Point it at the `public/` folder with no build command (or `python3 scripts/build.py` if you'd rather build on deploy).

| Host | Setup |
|---|---|
| GitHub Pages | Settings → Pages → Source: **GitHub Actions**. `deploy-pages.yml` publishes `public/` on every data update. |
| Netlify | New site from Git, publish directory `public`, no build command. |
| Vercel | Import the repo, framework "Other", output directory `public`. |
| Cloudflare Pages | Connect the repo, build output directory `public`, no build command. |

With Netlify, Vercel or Cloudflare, each data commit from the update workflow triggers a redeploy automatically. Delete `deploy-pages.yml` if you're not using GitHub Pages.

## Data sources

- Air quality: National Environment Agency (NEA), 24-hour PSI and PM2.5 by region, via the [data.gov.sg real-time API](https://data.gov.sg). Contains information from data.gov.sg made available under the [Singapore Open Data Licence v1.0](https://data.gov.sg/open-data-licence).
- NEA daily Haze Situation Updates: [nea.gov.sg advisories](https://www.nea.gov.sg/media/news/advisories), summarised by hand.
- Health advice: NEA's PSI health advisory, as published in [MOH's haze FAQ](https://www.moh.gov.sg/newsroom/faq-impact-of-haze-on-health/).
- Weather: Changi Airport (WSSS) observations from [aviationweather.gov](https://aviationweather.gov).
- Region outlines: URA Master Plan planning areas, via [yinshanyang/singapore](https://github.com/yinshanyang/singapore), merged into NEA's five regions. Check that repo's licence before redistributing the generated shapes.

This is not an official NEA service. For decisions that matter, check [haze.gov.sg](https://www.haze.gov.sg).
