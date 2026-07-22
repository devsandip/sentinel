#!/usr/bin/env bash
# Who actually visited sentinel.sandip.dev.
#
#   AWS_PROFILE=admin ./deploy/aws/traffic-report.sh [days]
#
# Pulls CloudFront standard access logs from S3 and answers the only question
# worth asking: did a human open the app, and where did they come from.
#
# The raw logs are gzipped 33-column TSV, one line per request, and Streamlit
# emits hundreds of requests per visit. Counting lines tells you nothing. So
# this counts two things instead:
#
#   sessions  requests to /_stcore/stream, the Streamlit WebSocket. One per
#             browser tab that actually loaded the app. This is the real
#             number.
#   visitors  distinct client IPs behind those sessions.
#
# Scanner noise is stripped. Every public IP gets a constant background of
# /wp-login, /cgi-bin, zgrab and friends; none of it is a visitor.
#
# Logs are delivered in batches and can lag by up to an hour, so the most
# recent visit may not appear yet.
set -euo pipefail

DAYS="${1:-7}"
BUCKET="sentinel-cf-logs-175110780229"
PREFIX="cloudfront/"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

echo "==> Fetching the last ${DAYS} days of logs from s3://${BUCKET}/${PREFIX}"

# CloudFront names each file <distribution>.YYYY-MM-DD-HH.<hash>.gz, so the
# date is filterable without downloading anything.
for i in $(seq 0 "$((DAYS - 1))"); do
  day="$(date -u -v-"${i}"d +%Y-%m-%d 2>/dev/null || date -u -d "-${i} day" +%Y-%m-%d)"
  aws s3 cp "s3://${BUCKET}/${PREFIX}" "$WORK/" \
    --recursive --exclude "*" --include "*.${day}-*.gz" --only-show-errors 2>/dev/null || true
done

shopt -s nullglob
files=("$WORK"/*.gz)
if [ ${#files[@]} -eq 0 ]; then
  echo "    No logs yet. Delivery lags by up to an hour after the first request."
  exit 0
fi
echo "    ${#files[@]} log files"

gunzip -c "${files[@]}" | grep -v '^#' > "$WORK/all.tsv"

# Field map for the standard log format:
#   1 date  2 time  3 edge-location  5 c-ip  8 uri-stem  10 referer  11 user-agent
# Matched against tolower() of the field, so these stay lowercase. Nearly every
# real crawler capitalises its name (Googlebot, ClaudeBot, SemrushBot), so a
# case-sensitive match here counts crawlers as browsers.
BOTS='bot|crawl|spider|zgrab|scan|curl|wget|python-requests|headlesschrome'
JUNK='/wp-|/cgi-bin|/geoserver|/actuator|/webui|/portal/|/license.txt|/\.env|/phpmyadmin|/admin'

echo ""
echo "=== app sessions per day (one per browser tab that loaded the app) ==="
awk -F'\t' '$8 == "/_stcore/stream" {print $1}' "$WORK/all.tsv" | sort | uniq -c | awk '{printf "  %s  %s\n", $2, $1}'

echo ""
echo "=== distinct visitors per day ==="
awk -F'\t' '$8 == "/_stcore/stream" {print $1"\t"$5}' "$WORK/all.tsv" \
  | sort -u | cut -f1 | uniq -c | awk '{printf "  %s  %s\n", $2, $1}'

echo ""
echo "=== visitors, newest first (ip, sessions, first seen, last seen, edge) ==="
awk -F'\t' '$8 == "/_stcore/stream" {print $5"\t"$1" "$2"\t"substr($3,1,3)}' "$WORK/all.tsv" \
  | sort | awk -F'\t' '
      { n[$1]++; if (!($1 in first)) first[$1]=$2; last[$1]=$2; edge[$1]=$3 }
      END { for (ip in n) printf "%s\t%s\t%s\t%s\t%s\n", last[ip], ip, n[ip], first[ip], edge[ip] }' \
  | sort -r | awk -F'\t' '{printf "  %-40s %4s sessions   %s -> %s   %s\n", $2, $3, $4, $1, $5}'

echo ""
echo "=== where they came from (referrers, excluding self) ==="
awk -F'\t' -v b="$BOTS" '$10 != "-" && $10 !~ /sentinel\.sandip\.dev/ && tolower($11) !~ b {print $10}' "$WORK/all.tsv" \
  | sed 's/%3A/:/g; s/%2F/\//g' | sort | uniq -c | sort -rn | head -15 | sed 's/^/  /'

echo ""
echo "=== browsers on the front page (bots and scanners stripped) ==="
awk -F'\t' -v b="$BOTS" '$8 == "/" && tolower($11) !~ b {print $11}' "$WORK/all.tsv" \
  | sed 's/%20/ /g; s/%2C/,/g; s/%28/(/g; s/%29/)/g; s/%3B/;/g' \
  | sed 's/^\(Mozilla\/5.0 ([^)]*)\).*/\1/' | sort | uniq -c | sort -rn | head -10 | sed 's/^/  /'

echo ""
echo "=== noise, for scale (requests that were never a visitor) ==="
printf "  %s scanner/bot requests of %s total\n" \
  "$(awk -F'\t' -v b="$BOTS" -v j="$JUNK" 'tolower($11) ~ b || tolower($8) ~ j' "$WORK/all.tsv" | wc -l | tr -d ' ')" \
  "$(wc -l < "$WORK/all.tsv" | tr -d ' ')"
