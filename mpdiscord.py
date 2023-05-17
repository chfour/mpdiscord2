from mpd.asyncio import MPDClient
from pypresence import AioPresence
import json
import asyncio


async def update(mpd: MPDClient, rpc: AioPresence) -> None:
    """
        update an aiopresence with data from an mpd client
    """

    status = await mpd.status()
    print(f"status: {status!r}")
    track = await mpd.currentsong()
    print(f"track: {track!r}")

    if status.get("state", None) == "play":
        await rpc.update(state=f"{track.get('artist', '?')}", details=f"{track.get('title', '?')}", large_image="unknown")
    else:
        await rpc.clear()
        # rpc.close()
        # i really wish i could close the rpc but pypresence is STUPId and wants to close the event loop
        # also AioPresence.close() is not an async method?????


async def main(config: dict):
    """
        main loop
    """
    mpd = MPDClient()
    await mpd.connect(config["mpd"]["server"])
    print(f"connected to mpd at {config['mpd']!r}")

    rpc = AioPresence(config["clientid"])  # , loop=asyncio.get_event_loop())
    await rpc.connect()
    print("connected to rpc")

    await update(mpd, rpc)
    async for subsys in mpd.idle(("player",)):
        print(f"change: {subsys}")
        await update(mpd, rpc)


if __name__ == "__main__":
    with open("config.json", "rt") as cf:
        config = json.load(cf)

    asyncio.run(main(config))
