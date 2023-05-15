from mpd.asyncio import MPDClient
from pypresence import AioPresence
import json
import asyncio


async def update(mpd: MPDClient) -> None:
    status = await mpd.status()
    print(f"status: {status!r}")
    track = await mpd.currentsong()
    print(f"track: {track!r}")


async def main(config: dict):
    mpd = MPDClient()
    await mpd.connect(config["mpd"]["server"])
    print(f"connected to mpd at {config['mpd']!r}")

    rpc = AioPresence(config["clientid"])  # , loop=asyncio.get_event_loop())
    await rpc.connect()
    print("connected to rpc")

    await rpc.update(state="test", details="test", large_image="unknown")
    # rpc.close()
    # i really wish i could close the rpc but pypresence is STUPId and wants to close the event loop

    await update(mpd)
    async for subsys in mpd.idle(("player",)):
        print(f"change: {subsys}")
        await update(mpd)


if __name__ == "__main__":
    with open("config.json", "rt") as cf:
        config = json.load(cf)

    asyncio.run(main(config))
