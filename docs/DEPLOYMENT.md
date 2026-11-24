# Website deployment

The Hearmark website is a static site served by Caddy on Jobo's `tx-server-119` server. The GitHub repository is the source of truth. Speech recognition, models, and browser cookies run on the user's computer; the server distributes only the website and installable Skill ZIP.

1. Merge and verify changes on `main`. For a Skill package release, tag the commit and wait for the GitHub Release. A website-only change does not require a new package version.
2. Run `bash scripts/deploy-site.sh` from a clean checkout. It builds and verifies `dist/`, uploads it to `/srv/sites/hearmark`, and prints the server-side ZIP hash.
3. Check `https://hearmark.jobo.ink/`, `/manifest.json`, and `/hearmark-package.zip`. For a package release, compare the site's ZIP hash with the GitHub Release asset.

The Caddy block is tracked in [`deploy/hearmark.caddy`](../deploy/hearmark.caddy). When changing it, append or update that block in `/etc/caddy/Caddyfile` on `tx-server-119`, run `caddy fmt` and `caddy validate` on a temporary Caddyfile, then install it and reload Caddy. The Cloudflare DNS record `hearmark.jobo.ink` is an unproxied A record for the server. Do not point it at a separate hosting service.
