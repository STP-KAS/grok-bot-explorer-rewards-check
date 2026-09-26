#!/usr/bin/env bash
# Read-only: take N recent "Found a block" hashes from each miner log and ask the public
# REST API (backed by its kaspad, not the indexer DB) for color + coinbase payout address.
N=${N:-10}; B=${B:-https://api-tn10.kaspa.org}
for f in "$@"; do
  grep "Found a block" "$f" | tail -600 | awk 'NR%60==0{print $1,$NF}' | tail -$N | while read ts h; do
    curl -s "$B/blocks/$h?includeColor=true" | python3 -c "
import json,sys,datetime
d=json.load(sys.stdin); e=d.get('extra') or {}; v=d.get('verboseData') or {}
t=datetime.datetime.fromtimestamp(int(d['header']['timestamp'])/1000).strftime('%Y-%m-%d %H:%M:%S')
print(f'$(basename $f) $h {t} CEST color={e.get(\"color\")} chain={v.get(\"isChainBlock\")} miner={e.get(\"minerAddress\")} info={e.get(\"minerInfo\")}')" 2>/dev/null || echo "$(basename $f) $h NOT-FOUND"
  done
done
