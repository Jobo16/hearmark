# Website deployment

The Hearmark website is a static site served by Caddy on Jobo's `tx-server-119` server. The GitHub repository is the source of truth. Speech recognition, models, and browser cookies run on the user's computer; the server distributes only the website and installable Skill ZIP.

1. Merge and verify changes on `main`. The CI workflow tests Linux, macOS, and Windows, then builds `dist/` and publishes it to `/srv/sites/hearmark` over SSH. Its `HEARMARK_DEPLOY_KEY` repository secret authenticates only the dedicated `hearmark-deploy` server user. `deploy/known_hosts` pins the server key.
2. To retry deployment without a new commit, run the CI workflow with `workflow_dispatch` on `main`. The same tests must pass before deployment. For a local fallback from a clean checkout, run `bash scripts/deploy-site.sh` using the `tx-server-119` SSH alias.
3. Check `https://hearmark.jobo.ink/`, `/manifest.json`, and `/hearmark-package.zip`. For a Skill package release, tag the commit and compare the site's ZIP hash with the GitHub Release asset. A website-only change does not require a new package version.

The Caddy block is tracked in [`deploy/hearmark.caddy`](../deploy/hearmark.caddy). When changing it, append or update that block in `/etc/caddy/Caddyfile` on `tx-server-119`, run `caddy fmt` and `caddy validate` on a temporary Caddyfile, then install it and reload Caddy. The Cloudflare DNS record `hearmark.jobo.ink` is an unproxied A record for the server. Do not point it at a separate hosting service.
