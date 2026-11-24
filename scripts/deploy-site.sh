#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
if [[ -n "$(git status --porcelain)" ]]; then
  echo 'Commit changes before deploying the site.' >&2
  exit 1
fi

python3 scripts/build.py
python3 scripts/check_package.py

commit="$(git rev-parse --short=12 HEAD)"
staging="/tmp/hearmark-dist-$commit"
server="tx-server-119"

ssh "$server" "mkdir -p '$staging'"
rsync -az --delete dist/ "$server:$staging/"
ssh "$server" "
  set -e
  install -d -o hearmark-deploy -g hearmark-deploy -m 0755 /srv/sites/hearmark
  rsync -a --delete '$staging/' /srv/sites/hearmark/
  chown -R hearmark-deploy:hearmark-deploy /srv/sites/hearmark
  find /srv/sites/hearmark -type d -exec chmod 755 {} \\;
  find /srv/sites/hearmark -type f -exec chmod 644 {} \\;
  rm -rf '$staging'
  sha256sum /srv/sites/hearmark/hearmark-package.zip
"

echo "Hearmark site files deployed from $commit"
