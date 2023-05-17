from mpd.asyncio import MPDClient
from pypresence import AioPresence
from string import Formatter
import json
import asyncio


class EvalFormatter(Formatter):
    """
        `string.Formatter` that `eval()`s all fields.
        only kwargs passed to `format()` matter here and will be passed as globals to `eval()`
    """

    def get_field(self, field_name, args, kwargs) -> str:
        # we don't reaaaally need to return the second argument as it's just used for unused args checking
        # (which we don't do)
        return eval(field_name, kwargs, {}), ""


async def update(mpd: MPDClient, rpc: AioPresence, formatfields: dict) -> None:
    """
        update an aiopresence with data from an mpd client
    """

    status = await mpd.status()
    print(f"status: {status!r}")
    track = await mpd.currentsong()
    print(f"track: {track!r}")

    if status.get("state", None) == "play":
        presence = formatfields.copy()

        formatter = EvalFormatter()  # why isn't format() a classmethod
        for k in "state", "details", "large_text", "small_text":
            presence[k] = formatter.format(presence[k], status=status, track=track)[:128]

        print(f"presence: {presence!r}")
        await rpc.update(**presence)
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

    rpc = AioPresence(config["rpc"]["clientid"])  # , loop=asyncio.get_event_loop())
    await rpc.connect()
    print("connected to rpc")

    await update(mpd, rpc, config["rpc"]["presence"])
    async for subsys in mpd.idle(("player",)):
        print(f"change: {subsys}")
        await update(mpd, rpc, config["rpc"]["presence"])


if __name__ == "__main__":
    with open("config.json", "rt") as cf:
        config = json.load(cf)

    asyncio.run(main(config))
