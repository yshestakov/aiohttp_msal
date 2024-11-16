#!/usr/bin/env python3
# https://gist.github.com/kellerza/8aad3952086b827a9f32516373df1623?permalink_comment_id=4129893
from redis import asyncio as aioredis
from aiohttp import web
from aiohttp_session import get_session
# from aiohttp_session import new_session
from aiohttp_session import setup as session_setup
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from aiohttp_session.redis_storage import RedisStorage

from aiohttp_msal.routes import ROUTES, URI_USER_AUTHORIZED
from aiohttp_msal.settings import ENV
import logging
# from aiohttp_msal import auth_ok
from aiohttp_msal import msal_session
from aiohttp_msal.msal_async import AsyncMSAL


@ROUTES.get(URI_USER_AUTHORIZED)
@msal_session()
async def got_user_authorized(
        request: web.Request, ses: AsyncMSAL) -> web.Response:
    """What is going on there???"""
    # if not auth_ok(ses):
    #    return web.json_response({"authenticated": False})
    sd = dict(ses.session.items())
    for k in ('redirect', 'token_cache', 'flow_cache'):
        if k in sd:
            sd.pop(k)
    val = dict(
        name=ses.name,
        mail=ses.mail,
        authenticated=ses.authenticated,
        sd=dict(sd.items())
    )
    big_s = await get_session(request)
    resp = web.Response(
        body='''got_authenticated:\n{}\n{}'''.format(val, big_s),
        content_type='text/plain')
    return resp


@ROUTES.get("/")
@msal_session()
async def docroot(request: web.Request, ses: AsyncMSAL) -> web.Response:
    sd = dict(ses.session.items())
    for k in ('redirect', 'token_cache', 'flow_cache'):
        if k in sd:
            sd.pop(k)
    val = dict(
        name=ses.name,
        mail=ses.mail,
        authenticated=ses.authenticated,
        sd=dict(sd.items())
    )
    foo = str(list(request.app.middlewares))
    resp = web.Response(
        body='''
<html>
<head>
 <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
 <title>MSAL - OAuth2 Example</title></head>
<body>
<h1>OAuth2 Examples</h1>
        <ul>
        <li><a href="/user/login">Log in using MS Entra ID</a>
        <li><a href="/user/info">user info (if authenticated)</a>
        <li><a href="/user/debug">user debug (if authenticated)</a>
        </ul>
<tt>
val: {}
        <br/>
foo: {}</tt>
</body>
</html>
        '''.format(str(val), foo),
        content_type="text/html",
    )
    return resp


def main():
    """Main web server."""
    logging.basicConfig(level=0)
    ENV.load()
    app = web.Application()
    redis_url = ENV.REDIS
    c_name = ENV.COOKIE_NAME
    if redis_url:
        redis = aioredis.from_url(redis_url)  # await
        cstor = RedisStorage(redis, cookie_name=c_name)
    else:
        cstor = EncryptedCookieStorage(b"Thirty  two  length  bytes  key.")
    session_setup(app, cstor)
    app.add_routes(ROUTES)
    web.run_app(app, port=5001)


if __name__ == "__main__":
    main()
