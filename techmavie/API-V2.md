# TechMavie Booking — Cal API v2

The Cal.com MCP server ([hithereiamaliff/mcp-calcom](https://github.com/hithereiamaliff/mcp-calcom)) talks to
**Cal API v2**. Cal.diy runs API v2 as a separate NestJS service (`apps/api/v2`), not inside the web image, and has
no API v1 — so without this service `https://book.techmavie.digital/api/v2/*` returns the web app's 404 page.

```
Internet ── nginx (book.techmavie.digital) ──┬── /          → web app (calcom)
                                             └── /api/v2/   → 127.0.0.1:5555  calcom-api ──► calcom-redis
                                                                └── same PostgreSQL database as the web app
```

## Image

`.github/workflows/techmavie-build-api-image.yml` builds `apps/api/v2/Dockerfile` on every push to `main` (same
commit as the web image) and pushes `ghcr.io/hithereiamaliff/cal.diy-api` with the tags `latest`, `sha-<commit>`
and a timestamp.

One build-time patch, applied in CI only: upstream forces TLS on the API's Bull (Redis) connection whenever
`NODE_ENV=production`, which fails against a plain Redis container. The workflow makes it opt-in
(`REDIS_TLS=true`), so the default is a plain `redis://` connection.

## One-time VPS setup (`/opt/calcom`)

1. **Secret** — generate a JWT secret for the API and add it to `/opt/calcom/.env`:

   ```bash
   echo "CAL_API_JWT_SECRET=$(openssl rand -hex 32)" | sudo tee -a /opt/calcom/.env
   ```

2. **Compose** — add these services to `/opt/calcom/docker-compose.yml`. Use the same network (and database
   service) as the existing `calcom` web service; `env_file: .env` gives the API the same `DATABASE_URL`,
   `NEXTAUTH_SECRET`, `CALENDSO_ENCRYPTION_KEY`, SMTP and Google Calendar settings as the web app, so bookings made
   through the API send the same emails and create the same calendar events.

   ```yaml
     calcom-redis:
       image: redis:7-alpine
       container_name: calcom-redis
       restart: always
       command: ["redis-server", "--appendonly", "yes"]
       volumes:
         - calcom-redis-data:/data
       networks:
         - stack                                   # the web app's network

     calcom-api:
       image: ghcr.io/hithereiamaliff/cal.diy-api:latest
       container_name: calcom-api
       restart: always
       env_file: .env
       environment:
         - NODE_ENV=production
         - API_PORT=80
         - API_URL=https://book.techmavie.digital/api
         - WEB_APP_URL=https://book.techmavie.digital
         - DATABASE_READ_URL=${DATABASE_URL}
         - DATABASE_WRITE_URL=${DATABASE_URL}
         - REDIS_URL=redis://calcom-redis:6379
         - JWT_SECRET=${CAL_API_JWT_SECRET}
         - API_KEY_PREFIX=cal_
         - STRIPE_API_KEY=sk_test_unused           # required at startup; Stripe billing is not used
         - STRIPE_WEBHOOK_SECRET=whsec_unused
         - IS_E2E=false
         - LOG_LEVEL=warn
         # - ENABLE_SLOTS_WORKERS=false            # uncomment if memory gets tight
       ports:
         - "127.0.0.1:5555:80"                     # localhost only; nginx is the public entry point
       depends_on:
         - calcom-redis
       mem_limit: 1g
       healthcheck:
         test: ["CMD-SHELL", "wget -qO- http://127.0.0.1:80/health || exit 1"]
         interval: 30s
         timeout: 10s
         retries: 3
         start_period: 60s
       networks:
         - stack

   volumes:
     calcom-redis-data:
   ```

   If `DATABASE_URL` is not defined in `/opt/calcom/.env` (for example because the compose file builds it from
   `POSTGRES_*` variables), write the same connection string into `DATABASE_READ_URL` / `DATABASE_WRITE_URL` here.

3. **Start it**:

   ```bash
   cd /opt/calcom
   docker compose pull calcom-api
   docker compose up -d calcom-redis calcom-api
   docker compose logs -f calcom-api          # wait for "Application started … on port: 80"
   curl -s http://127.0.0.1:5555/health        # → OK
   ```

4. **nginx** — inside the `book.techmavie.digital` server block (no new DNS name or certificate; API v2 rewrites
   `/api/v2/*` to `/v2/*` itself):

   ```nginx
   location /api/v2/ {
       proxy_pass http://127.0.0.1:5555;      # no URI part, so /api/v2 is passed through
       proxy_http_version 1.1;
       proxy_set_header Host $host;
       proxy_set_header X-Real-IP $remote_addr;
       proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
       proxy_set_header X-Forwarded-Proto $scheme;
       proxy_read_timeout 120s;
       client_max_body_size 10m;
   }
   ```

   ```bash
   sudo nginx -t && sudo systemctl reload nginx
   ```

5. **API key and check** — in TechMavie Booking: *Settings → Developer → API Keys → New API key*, then:

   ```bash
   curl -s https://book.techmavie.digital/api/v2/me -H "Authorization: Bearer cal_YOUR_KEY"
   ```

   Expected: `{"status":"success","data":{…}}`.

6. **Connect the MCP** — at https://mcpkeys.techmavie.digital create a **Cal.com / Cal.diy** connection with API URL
   `https://book.techmavie.digital/api/v2`, the API key, and an access level (`read`, `bookings` or `full`). Then run
   `get_instance_info` from Claude.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `/api/v2/…` still returns the web app's 404 page | The nginx `location /api/v2/` block is not active — `sudo nginx -t`, reload |
| `Missing environment variable: …` in the API logs | Add it (JWT_SECRET, REDIS_URL, DATABASE_READ_URL / WRITE_URL, STRIPE_API_KEY, STRIPE_WEBHOOK_SECRET, NEXTAUTH_SECRET) |
| `401 … Your api key is not valid` | Wrong key, or `API_KEY_PREFIX` differs from the web app's (default `cal_`) |
| API bookings send no emails / no Google Calendar event | The API container is missing values from `/opt/calcom/.env` (`CALENDSO_ENCRYPTION_KEY`, `EMAIL_*`, Google credentials) |
| Redis TLS errors | The image was built without the CI patch — rebuild, or end the URL with `#` (`redis://calcom-redis:6379#`) |
| High memory | `ENABLE_SLOTS_WORKERS=false`, keep `mem_limit` |
