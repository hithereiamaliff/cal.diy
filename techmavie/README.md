# TechMavie Booking (Cal.diy fork)

This fork builds the self-hosted booking app at **https://book.techmavie.digital**.

## What is customised

Everything TechMavie-specific lives in this `techmavie/` folder and in
`.github/workflows/techmavie-build-*.yml`. **No upstream files are edited in git**;
the CI builds patch them inside the build only. That keeps
"Sync fork" with `calcom/cal.diy` conflict-free.

| File | Purpose |
|---|---|
| `techmavie/branding/apply.py` | Crops/resizes the official logo into every logo/icon slot and patches app name, company, support email, links, brand colours, web manifest and UI text |
| `.github/workflows/techmavie-build-image.yml` | Runs the branding step, builds the Docker image, pushes to `ghcr.io/hithereiamaliff/cal.diy` |
| `.github/workflows/techmavie-build-api-image.yml` | Builds Cal API v2 (`apps/api/v2/Dockerfile`, Redis TLS made opt-in during the build) and pushes to `ghcr.io/hithereiamaliff/cal.diy-api` — needed by the Cal.com MCP |
| `techmavie/API-V2.md` | How API v2 runs on the VPS: compose services, nginx route, API key, verification |

## Logo policy

Only the official logo (`https://techmavie.digital/logo.png`) is used, verified by SHA-256.
It is **only cropped and resized** - never recoloured or redrawn. To change the logo,
update the file on techmavie.digital and then update `LOGO_SHA256` in `apply.py`.

## Updating from upstream

1. On GitHub, click **Sync fork** on `main`.
2. Both builds run automatically, from the same commit. If an upstream change breaks a
   patch, the build **fails on the patch step** with the exact file and text, so nothing
   ships unpatched. Fix the matching string (in `apply.py` or the workflow) and push.
3. On the VPS: `cd /opt/calcom && docker compose pull && docker compose up -d` (pulls the
   web and API images together — they share the database schema, so keep them in step).

Images are tagged `latest`, `sha-<commit>` and a timestamp, so you can roll back by
pinning a previous tag in `/opt/calcom/docker-compose.yml` (pin both images to the same commit).

## HitPay prices with sen

`apply.py` also patches the HitPay event-type price box to accept two decimals (like
the Stripe app), so prices such as MYR 399.99 can be entered. Pick **MYR** in the
currency box: it defaults to USD.

## Tour With Alan 1-to-1 call (set up on the VPS)

Event types live in the database, not in this repo. After the image with the price
patch is deployed (`docker compose pull && docker compose up -d`), create in the UI:

- Title "1-to-1 call with Alan (Google Meet)", slug `call-with-alan`, 60 minutes,
  location Google Meet, hidden from the profile, about 24 hours minimum notice.
- Booking questions: arrival date, cities you will visit, what you need help with.
- Apps tab → HitPay: price **399.99**, currency **MYR**.

Check the flow first with "Consultation: Test Payment" (MYR 5): the booker should come
back to "This meeting is scheduled". Then put the event's URL
(`https://book.techmavie.digital/techmavie/call-with-alan`) into the Tour With Alan Netlify
env var `VITE_CAL_CALL_URL` and redeploy it. Selamat Datang's 1-to-1 Assistance uses the same
URL unless `VITE_CALCOM_SELAMAT_ASSISTANCE_URL` is set, so clear that one if it holds an older link.
Tour With Alan opens this page in a new tab rather than embedding it: inside an iframe,
a paid booking switches HitPay to its in-page overlay, which skips the redirect fixes above.
