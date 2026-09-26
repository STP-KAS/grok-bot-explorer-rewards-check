#!/usr/bin/env python3
"""Read-only. Measures, over a short window, (a) the change in getBalanceByAddress for our
mining address and (b) the sum of coinbase outputs paying that address in every block that
was added to the selected (virtual) chain during the window. In Kaspa, a chain block's
coinbase pays the rewards of the blue blocks in its merge set, so (b) is the full reward
inflow. If (a) == (b) the balance growth is entirely mining rewards (no other deposits or spends).
Usage: reward-window.py [seconds] [ws-url]"""
import asyncio, json, sys, time, datetime, websockets
A = "kaspatest:qzffl5xy9np46gkttyuftqnv2w04pr8g3wsp7c3vv8se3txtelx6q7c0v0ldx"
SPK = "20929fd0c42cc35d22cb593895826c539f508ce88ba01f622c61e198accbcfcda0ac"
SECS = int(sys.argv[1]) if len(sys.argv) > 1 else 30
URL = sys.argv[2] if len(sys.argv) > 2 else "ws://127.0.0.1:18210"
async def main():
    async with websockets.connect(URL, max_size=None) as ws:
        n = [0]
        async def c(meth, p={}):
            n[0] += 1; await ws.send(json.dumps({"id": n[0], "method": meth, "params": p}))
            m = json.loads(await asyncio.wait_for(ws.recv(), 120))
            if m.get("error"): raise RuntimeError(m["error"])
            return m["params"]
        async def snap():
            d = await c("getBlockDagInfo"); b = int((await c("getBalanceByAddress", {"address": A}))["balance"])
            return d["sink"], b, time.time()
        s0, b0, t0 = await snap()
        await asyncio.sleep(SECS)
        s1, b1, t1 = await snap()
        vc = await c("getVirtualChainFromBlock", {"startHash": s0, "includeAcceptedTransactionIds": False})
        added, removed = vc.get("addedChainBlockHashes", []), vc.get("removedChainBlockHashes", [])
        if s1 in added: added = added[:added.index(s1) + 1]   # stop at the sink seen with b1
        async def paid_to_us(h):
            blk = (await c("getBlock", {"hash": h, "includeTransactions": True}))["block"]
            amt = cnt = 0
            for o in blk["transactions"][0]["outputs"]:   # coinbase = tx 0
                spk = o["scriptPublicKey"]; spk = spk if isinstance(spk, str) else spk.get("scriptPublicKey", "")
                if spk.endswith(SPK): amt += int(o.get("value", o.get("amount", 0))); cnt += 1
            return amt, cnt, int(blk["header"]["timestamp"])
        paid = npaid = unpaid = 0; first = last = None
        for h in added:
            a, k, ts = await paid_to_us(h); paid += a; npaid += k; first = first or ts; last = ts
        for h in removed:   # chain blocks reorged out during the window: their coinbase is un-applied
            a, k, ts = await paid_to_us(h); unpaid += a
        paid -= unpaid
        f = lambda ms: datetime.datetime.fromtimestamp(ms/1000).strftime("%H:%M:%S") if ms else None
        print(json.dumps(dict(window_wall_s=round(t1 - t0, 1), chain_blocks_added=len(added), chain_blocks_removed=len(removed),
            chain_block_time_first=f(first), chain_block_time_last=f(last),
            balance_before=b0/1e8, balance_after=b1/1e8, balance_delta_tkas=(b1 - b0)/1e8,
            coinbase_outputs_to_us=npaid, coinbase_paid_to_us_tkas=paid/1e8, reorged_out_coinbase_tkas=unpaid/1e8,
            unexplained_tkas=round((b1 - b0 - paid)/1e8, 8)), indent=1))
asyncio.run(main())
