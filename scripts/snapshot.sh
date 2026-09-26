#!/usr/bin/env bash
# Read-only snapshot: public REST API (balance/utxo-index side vs indexer-DB side) + local node.
A=${A:-kaspatest:qzffl5xy9np46gkttyuftqnv2w04pr8g3wsp7c3vv8se3txtelx6q7c0v0ldx}; B=${B:-https://api-tn10.kaspa.org}
echo "== $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "api balance (kaspad utxoindex): $(curl -s $B/addresses/$A/balance | python3 -c 'import json,sys;print(json.load(sys.stdin)["balance"]/1e8)')"
echo "api transactions-count (indexer DB): $(curl -s $B/addresses/$A/transactions-count)"
curl -s "$B/addresses/$A/full-transactions?limit=1&resolve_previous_outpoints=no" | python3 -c '
import json,sys,datetime;t=json.load(sys.stdin)[0]
print("api newest indexed tx:",t["transaction_id"],"block_time",datetime.datetime.fromtimestamp(t["block_time"]/1000),"accepting_blue_score",t["accepting_block_blue_score"])'
echo "api virtual-chain-blue-score (kaspad): $(curl -s $B/info/virtual-chain-blue-score)"
echo "api /info/health: $(curl -s $B/info/health)"
[ -f /tmp/chk-node.py ] && (cd /tmp && timeout 40 python3 /tmp/chk-node.py | sed 's/^/node: /')
