import asyncio, json, websockets
A="kaspatest:qzffl5xy9np46gkttyuftqnv2w04pr8g3wsp7c3vv8se3txtelx6q7c0v0ldx"
async def m():
    async with websockets.connect("ws://127.0.0.1:18210", max_size=None) as ws:
        async def c(i,meth,p={}):
            await ws.send(json.dumps({"id":i,"method":meth,"params":p})); return json.loads(await asyncio.wait_for(ws.recv(),30)).get("params")
        d=await c(1,"getBlockDagInfo"); print("local daa",d.get("virtualDaaScore"),"tips",len(d.get("tipHashes",[])))
        p=await c(2,"getConnectedPeerInfo"); print("peers",len(p.get("peerInfo",[])))
        b=await c(3,"getBalanceByAddress",{"address":A}); print("local balance",int(b.get("balance",0))/1e8)
asyncio.run(m())
