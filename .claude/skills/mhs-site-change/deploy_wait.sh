#!/usr/bin/env bash
# Wait for the "Publish site" run of a commit on main and report how it ended.
#   deploy_wait.sh <commit sha, full or short> [owner/repo]
# Uses the public GitHub API (no login; about 60 requests per hour), polling every 10 s.
# Then waits for the "Live check" run that follows it.
# Exit code: 0 success (prints the job ids; pass the "build" one to GitHub MCP get_job_logs to read the
# build log), 1 publish failed or cancelled, 2 timed out or unknown commit, 3 Live check failed.
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
      break ;;
    completed*) exit 1 ;;
  esac
  python3 -c "import time; time.sleep(10)"
done
case "$line" in "completed success"*) ;; *) echo "timed out; check the Actions tab"; exit 2 ;; esac

# The "Live check" workflow (.github/workflows/live-check.yml) starts when Publish site succeeds and may take a
# few minutes while the CDN catches up. Wait for it too (up to about 8 minutes).
echo "waiting for Live check ..."
for _ in $(seq 1 24); do
  live=$(curl -s --max-time 10 "https://api.github.com/repos/$repo/actions/runs?head_sha=$sha" | python3 -c '
import sys, json
runs = [r for r in json.load(sys.stdin).get("workflow_runs", []) if r["name"] == "Live check"]
print(" ".join("%s %s %s" % (r["status"], r["conclusion"], r["html_url"]) for r in runs[:1]) or "none")
' 2>/dev/null)
  case "$live" in
    "completed success"*) echo "Live check passed: ${live##* }"; exit 0 ;;
    completed*) echo "Live check FAILED: ${live##* } (open it: the summary lists what is wrong on the live site)"; exit 3 ;;
  esac
  python3 -c "import time; time.sleep(20)"
done
echo "Live check did not finish in time; look at the Actions tab"
exit 0
