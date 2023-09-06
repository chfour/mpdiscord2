from mpd.asyncio import MPDClient
from pypresence import AioPresence
from string import Formatter
from urllib.parse import urljoin
from copy import deepcopy
import json
import asyncio
import httpx

from typing import Union


class EvalFormatter(Formatter):
    """
        `string.Formatter` that `eval()`s all fields.
        only kwargs passed to `format()` matter here and will be passed as globals to `eval()`
    """

    def get_field(self, field_name, args, kwargs) -> str:
        # we don't reaaaally need to return the second argument as it's just used for unused args checking
        # (which we don't do)
        return eval(field_name, kwargs, {}), ""


async def get_cover_thumbnail(release: str, api_base=None, size="small") -> Union[None, str]:
    """
        return a coverartarchive cover image url for a release, or None if not found
        will use `api_base` instead of "https://coverartarchive.org/" if not None
        https://musicbrainz.org/doc/Cover_Art_Archive/API
        (i would have used musicbrainzngs but it doesn't support asyncio)
    """

    async with httpx.AsyncClient(  # probably not the best way to do it
        # https://musicbrainz.org/doc/MusicBrainz_API/Rate_Limiting#Provide_meaningful_User-Agent_strings
        headers={"user-agent": "mpdiscord2/1.0 ( https://github.com/chfour/mpdiscord2 )"},
        follow_redirects=True
    ) as client:
        try:
            r = await client.get(urljoin((api_base or "https://coverartarchive.org/"), f"/release/{release}/"))
            r.raise_for_status()
            data = r.json()
            front = next((img for img in data["images"] if img["front"]))
            return front["thumbnails"][size]
        except (httpx.HTTPError, json.JSONDecodeError, StopIteration, KeyError):
            return None


async def update(mpd: MPDClient, rpc: AioPresence, config: dict) -> None:
    """
        update an aiopresence with data from an mpd client
    """

    status = await mpd.status()
    print(f"status: {status!r}")
    track = await mpd.currentsong()
    print(f"track: {track!r}")

    if status.get("state", None) == "play":
        presence = deepcopy(config["rpc"]["presence"])

        formatter = EvalFormatter()  # why isn't format() a classmethod
        for k in "state", "details", "large_text", "small_text":
            if k not in presence:
                continue
            presence[k] = formatter.format(presence[k], status=status, track=track)[:128]

        for b in presence["buttons"]:
            for k in "label", "url":
                b[k] = formatter.format(b[k], status=status, track=track)  # i don't know what the limits are for that
        
        presence["buttons"] = [b for b in presence["buttons"] if b["label"] != "" and b["url"] != ""]
        if len(presence["buttons"]) == 0:
            presence.pop("buttons", None)

        cover_url = None
        for k in "large_image", "small_image":
            if k not in presence or not presence[k].startswith("$cover"):
                continue

            if cover_url is None:
                # we want to only fetch the stuff once and only if needed at all
                cover_url = ""
                if "musicbrainz_albumid" in track:
                    cover_url = await get_cover_thumbnail(track["musicbrainz_albumid"], api_base=config.get('coverartarchive'))
                    print(f"cover url: {cover_url}")

            fallback = ""
            if "/" in presence[k]:
                fallback = presence[k][presence[k].find("/") + 1:]

            presence[k] = cover_url or fallback

        for k in presence:
            if presence[k] == "":
                presence[k] = None

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

    await update(mpd, rpc, config)
    async for subsys in mpd.idle(("player",)):
        print(f"change: {subsys}")
        await update(mpd, rpc, config)


if __name__ == "__main__":
    with open("config.json", "rt") as cf:
        config = json.load(cf)

    asyncio.run(main(config))
