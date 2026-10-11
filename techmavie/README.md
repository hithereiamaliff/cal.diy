# TechMavie Booking (Cal.diy fork)

This fork builds the self-hosted booking app at **https://book.techmavie.digital**.

## What is customised

Everything TechMavie-specific lives in this `techmavie/` folder and in
`.github/workflows/techmavie-build-image.yml`. **No upstream files are edited in git**;
the branding script patches them inside the CI build only. That keeps
"Sync fork" with `calcom/cal.diy` conflict-free.

| File | Purpose |
|---|---|
| `techmavie/branding/apply.py` | Crops/resizes the official logo into every logo/icon slot and patches app name, company, support email, links, brand colours, web manifest and UI text |
| `.github/workflows/techmavie-build-image.yml` | Runs the branding step, builds the Docker image, pushes to `ghcr.io/hithereiamaliff/cal.diy` |

## Logo policy

Only the official logo (`https://techmavie.digital/logo.png`) is used, verified by SHA-256.
It is **only cropped and resized** - never recoloured or redrawn. To change the logo,
update the file on techmavie.digital and then update `LOGO_SHA256` in `apply.py`.

## Updating from upstream

1. On GitHub, click **Sync fork** on `main`.
2. The build runs automatically. If an upstream change breaks a patch, the build
   **fails on the branding step** with the exact file and text, so nothing ships
   unbranded. Fix the matching string in `apply.py` and push.
3. On the VPS: `cd /opt/calcom && docker compose pull && docker compose up -d`.

Images are tagged `latest`, `sha-<commit>` and a timestamp, so you can roll back by
pinning a previous tag in `/opt/calcom/docker-compose.yml`.
