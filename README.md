> **Experimental only. Not a product.**
>
> Do not use wallet integrations on this GitHub. STP remains a clown. [DISCLAIMER.md](DISCLAIMER.md)

# TN10 explorer check: mining rewards vs. a transaction list stuck at 21:55

Written by Grok Bot for stp, Sat 26 Sep 2026, 06:48–07:00 CEST. All times are CEST (UTC+2) unless marked otherwise.
Read-only investigation: nothing was sent, and no node, miner or storm process was touched.

## What

Mining address: `kaspatest:qzffl5xy9np46gkttyuftqnv2w04pr8g3wsp7c3vv8se3txtelx6q7c0v0ldx` (Kaspa Testnet-10).

On https://tn10.kaspa.stream/addresses/<addr> the **balance keeps growing** (749,211 TKAS at 06:45) and the page shows a live hashrate plus blue/red block counts. But the **transaction list and "Last transaction" stop at 2026-09-25 21:55:38**, and no new block rewards show up, even though our miners (gb001, gb002, knsbot on local kaspad n0) log "Block submitted successfully" every second.

## Why

We wanted to know whether our blocks are really accepted and paying us, why the list is frozen, and whether the balance growth is only mining rewards.

## Short answer

1. **Yes, our blocks are accepted and paying this address.** Sampled blocks from the gb001 and gb002 logs are **blue** on the public node. Some are chain blocks. Their coinbase `minerAddress` is our address. Chain-block coinbases pay our address continuously.
2. **The list is frozen because the public indexer (the transaction database behind api-tn10.kaspa.org, and apparently kaspa.stream) stopped at about 21:55:38 on 25 Sep for the whole network, not just for our address.** The balance, hashrate and block numbers come straight from kaspad, so they stay live. The transaction list and count come from the indexer's database, which has not moved in ~9 hours. Nothing on our side changed at 21:55: no node restart, no miner change, no address change. But 21:55 falls ~7 minutes into our "PHASE1" full-throttle overload (~5–7.5k network TPS, which started at 21:45–21:48). Our load is therefore a plausible trigger, but we can't prove it.
3. **Yes, the balance growth is fully explained by mining rewards.** In two measured windows (20 s and 90 s), the change in `getBalanceByAddress` equals, to the sompi, the sum of coinbase outputs paying our address in the chain blocks added during that window. There are no other deposits and no spends. The rate is about **1,230 TKAS/min (~74k TKAS/h)**.

## How (exact commands / endpoints)

Public REST API `B=https://api-tn10.kaspa.org`, `A=<our address>`:

| Endpoint | Backed by | Used for |
|---|---|---|
| `GET $B/addresses/$A/balance` | kaspad utxoindex (live) | balance |
| `GET $B/addresses/$A/transactions-count` | indexer DB | count (frozen?) |
| `GET $B/addresses/$A/full-transactions?limit=1&resolve_previous_outpoints=no` | indexer DB | newest indexed tx |
| `GET $B/info/virtual-chain-blue-score`, `GET $B/info/blockdag` | kaspad (live) | real network tip |
| `GET $B/info/health` | API health (DB + kaspad) | DB lag self-report |
| `GET $B/blocks/{hash}?includeColor=true` | kaspad (live) | block color, chain status, coinbase, minerAddress |
| `GET $B/transactions/{coinbase txid}` | indexer DB | does the DB know a recent tx? |

Local node n0: wRPC JSON `ws://127.0.0.1:18210`, using `getBlockDagInfo`, `getBalanceByAddress`, `getVirtualChainFromBlock` and `getBlock(includeTransactions)`. We did **not** use `getUtxosByAddresses`, because it would return well over 100k UTXOs.

Scripts (in `scripts/`):
- `snapshot.sh`: one read-only snapshot of API balance, API tx-count, newest indexed tx, real blue score, `/info/health` and the local node balance.
- `sample-block-colors.sh <miner logs>`: takes block hashes from `Found a block` lines and asks the public API for color, chain status and minerAddress.
- `reward-window.py [secs]`: records the sink and balance, waits, records the sink and balance again, walks `getVirtualChainFromBlock` from the first sink, sums coinbase outputs paying our script in every added chain block (and subtracts any reorged-out ones), then compares that sum with the balance change.
- `chk-node.py`: minimal local-node check (DAA, peers, balance).

## Timeline (CEST)

| Time | Event | Source |
|---|---|---|
| 25 Sep 21:40 | n0 synced, pid 3992792, mempool 60–100k (storm running) | logs/monitor.jsonl |
| 21:45:05 | `acceptedTxBlockTime` frozen inside api-tn10 `/info/health` (1790365505207) | /info/health |
| 21:45:18 – 21:48:41 | **PHASE1 full-throttle overload starts** (probes restarted 3 times) | logs/storm/ramp.log |
| 21:50 – 21:59 | network 4.5k–7.5k TPS, n0 synced, same pid, sink age < 1 s | nettps.jsonl, monitor.jsonl |
| **21:55:38.262** | **newest tx in the indexer DB**, for our address and for every other address checked | full-transactions |
| 21:55:38 → now | indexer DB frozen at blue score ≈ 568,828,507 | full-transactions / health |
| 23:52:39 | n0 restarted with `--utxoindex` (~19 min down; back at tip 00:11:52) | HANDOFF.md |
| 26 Sep 00:12–00:13 | current miners gb001 and gb002 started (knsbot relaunched 06:41) | ps |
| 06:48 → 06:57 | api tx-count stays **913,840** in 4 samples over 8.5 min; balance grows 754,465 → 766,688 | evidence/snapshot-*.txt |

The explorer stopped two hours **before** our node restart, so the restart is not the cause.

## Findings with evidence

### F1: Our blocks are blue and pay our address (public node)
`evidence/block-color-sample.txt`: 12 blocks sampled from miner-001.log (gb001) and miner-002.log (gb002), 06:46–06:52. All 12 are `color=blue`, 6 of them are chain blocks, and every one has `minerAddress = our address` and `minerInfo = 2.1.0/0.2.7/gb00x`. Example:

```
e9224fe9ede5dc004f74a5f87d47502e6908dcaeacc00428fdc139f6f19b2846  2026-09-26 06:49:56  blue  isChainBlock=true
  coinbase 79a2ebda7d3f3948ef8319b25a10a1c6c8f6243357b8ba2aaad618b98680197b pays our address 8.68356064 TKAS
```
(`evidence/block-e9224fe9-public-api.json`). As a reminder, a block's own reward is paid later by the coinbase of the chain block that merges it. So the 8.68 TKAS above is the reward for earlier blue blocks, not for e9224fe9 itself.

### F2: The indexer DB stopped at 21:55:38 for the whole network
- Newest indexed tx for our address: `2a915694…ab4c`, block_time **2026-09-25 21:55:38.262**, accepting blue score 568,828,507.
- The same cutoff shows up for unrelated addresses (`evidence/snapshot-*.txt`, and the checks below at 06:48):
  - `kaspatest:qz3egpx877…` (27,143,249 txs, not ours): newest 21:55:38.262
  - `kaspatest:qpjhm33f0n…` (348,039 txs, another miner): newest 21:54:59.780
  - storm wallets 0 and 1 (`qz982y377p…` with 1,202 txs, `qq9vpqft79…` with 1,077 txs): newest 21:55:27 and 21:55:37
- Real network blue score is 569,153,694 at 06:48 and 569,156,806 at 06:56, about **328k blue score (≈9 h at 10 BPS) ahead** of the DB.
- Our fresh chain-block coinbase `79a2ebda…197b` (06:49:56) → `GET /transactions/79a2ebda…` = **HTTP 404 "Transaction not found"** (`evidence/coinbase-tx-lookup.txt`), while `/blocks/e9224fe9…` returns the block fine.
- `transactions-count` for our address: 913,840 at 06:48:11, 06:48:47, 06:52:23 and 06:56:45. It never changed.
- **`/info/health` is itself stale and misleading.** It reports `"isSynced": true, "blueScoreDiff": 25` using a kaspad blue score of 568,825,293 (≈21:45). The health check appears to be frozen or cached rather than showing the real 328k lag.
- kaspa.stream shows exactly the same count (913,840) and the same last tx (21:55:38) as api-tn10. So it either reads the same database or its own indexer froze at the same moment. We couldn't see which: its frontend bundle is obfuscated and talks to authenticated websockets, and we did not dig further.

This rules out pagination, sort order (block time vs acceptance), a per-address transaction limit, or coinbase being filtered for big addresses. Small addresses stop at the same second.

### F3: Nothing on our side at 21:55
`evidence/our-side-around-2155.txt`: n0 stayed synced from 21:50 to 21:59 with the same pid 3992792 (no restart) and a sink age under 1 s. Nobody changed miners or addresses (the mining address appears only in `scripts/keepalive-storm-2.sh`). What *was* happening: PHASE1 overload from 21:45–21:48, with the network at 5.5k–7.5k TPS and ~70–93 blocks per 10 s. An indexer falling behind or crashing under that write load is the most likely explanation, but we can't prove it from outside.

### F4: Balance growth = mining rewards, exactly
`evidence/reward-window-1.json` (20 s) and `evidence/reward-window-3.json` (90 s):

```
20 s: 50 chain blocks,  balance +465.03226608 TKAS,  coinbase→us 465.03226608  unexplained 0
90 s: 275 chain blocks, balance +1843.53660656 TKAS, coinbase→us 1843.53660656 unexplained 0
```
An earlier 120 s run of the first script version (`reward-window-2.json`) was off by −8.96 TKAS, which is about one coinbase output. That window had one reorged-out chain block, and that version didn't subtract it yet. The fixed script handles this case.
API balance and node balance agree within seconds of drift (for example 766,688.82 on the API vs 766,774.08 on the node, measured ~2 s apart at ~20 TKAS/s).

## Conclusion

The mining works: blocks are blue and accepted, rewards arrive every chain block, and the balance is right. The "frozen" transaction list is a **display/indexer problem on the public TN10 infrastructure**. Its transaction database has not ingested anything since 2026-09-25 21:55:38 CEST, for any address. That happened ~7 minutes into our heaviest load phase, and the health endpoint wrongly still says "synced". Live kaspad-backed fields (balance, hashrate, blue/red counts, block pages) keep updating, which is why the page looks half-alive.

## Flaws / limits

- We can't see inside the explorer or indexer, so the cause of the stall (crash, stuck on one block, disk full, OOM, deliberately paused) is unknown. Correlation with our overload is timing only.
- Color sampling covers 12 blocks, not all of them. The 123,323 blue / 3,003 red counts come from the page, and we did not recompute them. knsbot blocks were not sampled (it has no log file in the miner log dir).
- The reward windows are short (20 s and 90 s). Balance and sink are read ~ms apart, and the "coinbase of chain block X is accepted by X's chain child" offset is at most one block. Both windows still matched to the sompi.
- kaspa.stream vs api-tn10 sharing a DB is inferred from identical numbers.
- The lifetime balance (all history since mining began) was not reconciled, only the current growth rate.

## Ideas

- Re-run `scripts/snapshot.sh` later. When `transactions-count` starts moving again, the indexer is catching up (9+ h of ~6k TPS = hundreds of millions of rows, so it may take a long time).
- During future stress tests, poll `/addresses/<storm wallet>/full-transactions?limit=1` and alert when the newest block_time lags more than 5 min. Don't trust `/info/health`.
- **Draft note to the explorer / api-tn10 maintainers (NOT sent or filed anywhere):**
  > Hi, heads-up on TN10: the tx database behind api-tn10.kaspa.org (and tn10.kaspa.stream, which shows the same numbers) appears to have stopped ingesting at 2026-09-25 19:55:38 UTC (accepting blue score ≈ 568,828,507). Every address we checked has its newest tx at 19:54–19:55 UTC, `/transactions/<recent coinbase>` returns 404, and transactions-count is flat, while `/info/virtual-chain-blue-score` is ~328k ahead. `/info/health` still reports `isSynced: true, blueScoreDiff: 25`, which seems cached from ~19:45 UTC. For context, we were running a high-TPS stress test (~5–7.5k TPS) at that time, so it may have been overloaded. Sorry if so, and happy to share numbers. Balance and block endpoints are fine.

## Reproduce

```bash
scripts/snapshot.sh                                   # API vs node, run a few minutes apart
N=6 scripts/sample-block-colors.sh /tmp/relqunch-miners/logs/miner-001.log /tmp/relqunch-miners/logs/miner-002.log
python3 scripts/reward-window.py 60                   # needs local kaspad wRPC JSON on ws://127.0.0.1:18210 and `pip install websockets`
```

## Related

- Summary of the TN10 stress rounds (1–8): [tn10-vprogs-stress-findings](https://github.com/STP-KAS/tn10-vprogs-stress-findings)
