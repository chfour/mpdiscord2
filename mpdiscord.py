from mpd.asyncio import MPDClient
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
    print("connected")

    await update(mpd)
    async for subsys in mpd.idle(("player",)):
        print(f"change: {subsys}")
        await update(mpd)


if __name__ == "__main__":
    with open("config.json", "rt") as cf:
        config = json.load(cf)

    asyncio.run(main(config))
