"""Shared aresponses helpers for the BRP069 control write tests."""

import asyncio

from aiohttp import web

CONTROL = (
    "ret=OK,pow=0,mode=4,adv=13,stemp={stemp},shum=0,dt1=25.0,dt2=M,dt3=25.5,"
    "dt4={stemp},dt5={stemp},dt7=25.0,dh1=0,dh2=50,dh3=0,dh4=0,dh5=0,dh7=0,dhh=50,"
    "b_mode=4,b_stemp={stemp},b_shum=0,alert=255,f_rate=B,b_f_rate=B,dfr1=A,dfr2=A,"
    "dfr3=B,dfr4=B,dfr5=B,dfr6=A,dfr7=A,dfrh=A,f_dir=0,b_f_dir=0,dfd4=0"
)


CONTROL_ALIRA = (
    "ret=OK,pow=1,mode=4,stemp={stemp},shum=0,dt4={stemp},dh4=0,f_rate=B,dfr4=B,"
    "f_dir_ud=S,f_dir_lr=0"
)


SET = "/aircon/set_control_info"


GET = "/aircon/get_control_info"


def add_routes(aresponses, reads, writes, control=CONTROL):
    """Register get_control_info (by stemp) and set_control_info replies in order."""
    for stemp in reads:
        aresponses.add(path_pattern=GET, response=control.format(stemp=stemp))
    for ret in writes:
        aresponses.add(path_pattern=SET, response=ret)


def sent(aresponses, path=SET):
    """Return the query of every request sent to path."""
    return [dict(h.request.query) for h in aresponses.history if h.request.path == path]


TIMED_OUT = []


async def slow_ok(request):
    TIMED_OUT.append(dict(request.query))
    await asyncio.sleep(1)
    return web.Response(text="ret=OK")


async def reset_connection(request):
    request.transport.close()
    return web.Response(text="ret=OK")


def mock_reply(aresponses, reply):
    """Turn a handler or a (status, text) pair into an aresponses response."""
    if callable(reply):
        return reply
    return aresponses.Response(status=reply[0], text=reply[1])
