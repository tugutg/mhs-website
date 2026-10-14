#!/usr/bin/env bash
# Wait for the "Publish site" run of a commit on main and report how it ended.
#   deploy_wait.sh <commit sha, full or short> [owner/repo]
# Uses the public GitHub API (no login; about 60 requests per hour), polling every 10 s for up to 5 min.
# Exit code: 0 success (prints the job ids; pass the "build" one to GitHub MCP get_job_logs to read the
# build log), 1 failure or cancelled, 2 timed out or unknown commit.
set -u
sha=${1:?usage: deploy_wait.sh <commit sha> [owner/repo]}
repo=${2:-tugutg/mhs-website}
if [[ ! $sha =~ ^[0-9a-f]{40}$ ]]; then
  full=$(git rev-parse --verify --quiet "$sha^{commit}") || { echo "unknown commit $sha; pass the full 40-character sha"; exit 2; }
  sha=$full
fi
for _ in $(seq 1 30); do
  line=$(curl -s --max-time 10 "https://api.github.com/repos/$repo/actions/runs?head_sha=$sha" | python3 -c '
import sys, json
runs = [r for r in json.load(sys.stdin).get("workflow_runs", []) if r["name"] == "Publish site"]
print(" ".join("%s %s %s %s" % (r["status"], r["conclusion"], r["id"], r["html_url"]) for r in runs[:1]) or "none")
' 2>/dev/null)
  echo "$(date -u +%H:%M:%S) ${line:-no answer}"
  case "$line" in
    "completed success"*)
      run=$(echo "$line" | cut -d' ' -f3)
      curl -s --max-time 10 "https://api.github.com/repos/$repo/actions/runs/$run/jobs" | python3 -c '
import sys, json
for j in json.load(sys.stdin).get("jobs", []): print("job_id %s  (%s)" % (j["id"], j["name"]))
' 2>/dev/null
      exit 0 ;;
    completed*) exit 1 ;;
  esac
  python3 -c "import time; time.sleep(10)"
done
echo "timed out; check the Actions tab"
exit 2
