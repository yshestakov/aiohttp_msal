"""Graph User Info."""
import logging
import asyncio
from functools import wraps
from typing import Any, Callable
from aiohttp_msal.msal_async import AsyncMSAL
_LOGGER = logging.getLogger('aiohttp_msal')  # DONT import from aiohttp_msal


def retry(func: Callable) -> Callable:
    """Retry if tenacity is installed."""

    @wraps(func)
    async def _retry(*args: Any, **kwargs: Any) -> Any:
        """Retry the request."""
        retries = [2, 4, 8]
        while True:
            try:
                res = await func(*args, **kwargs)
                return res
            except Exception as err:  # pylint: disable=broad-except
                if retries:
                    await asyncio.sleep(retries.pop())
                else:
                    raise err

    return _retry


@retry
async def get_user_info(aiomsal: AsyncMSAL) -> None:
    """Load user info from MS graph API. Requires User.Read permissions."""
    async with aiomsal.get("https://graph.microsoft.com/v1.0/me") as res:
        body = await res.json()
        try:
            _LOGGER.debug(f'get_user_info: {body}')
            if "mail" in body:
                # may be absent for "EXT" user
                aiomsal.session["mail"] = body["mail"]
            aiomsal.session["name"] = body.get("displayName")
            aiomsal.session["id"] = body["id"]
            aiomsal.session["upn"] = body.get("userPrincipalName")
            aiomsal.session["lang"] = body.get("preferredLanguage", "en")
            aiomsal.session["manager"] = body.get("manager")
        except KeyError as err:
            raise KeyError(
                f"Graph endpoint /me: {body}: {err}"
            ) from err


@retry
async def get_manager_info(aiomsal: AsyncMSAL) -> None:
    """
    Load manager info from MS graph API.
    Requires User.Read.All permissions.
    """
    async with aiomsal.get(
            "https://graph.microsoft.com/v1.0/me/manager") as res:
        body = await res.json()
        if 'error' in body:
            e = body['error']
            _LOGGER.error('{}: {}'.format(e['code'], e['message']))
            # {'error': {
            #    'code': 'Request_ResourceNotFound',
            #    'message': "Resource 'manager' does ...',
            #    'innerError': {'date': '2024-11-16T12:17:32',
            #                    'request-id': 'xxx',
            #                    'client-request-id': 'yyy'
            #     }
            #   }
            # }
            return False
        try:
            _LOGGER.debug(f'get_manager_info() resp: {body}')
            aiomsal.session["m_mail"] = body["mail"]
            aiomsal.session["m_name"] = body["displayName"]
            aiomsal.session["m_id"] = body["id"]
            aiomsal.session["m_upd"] = body["userPrincipalName"]
        except KeyError as err:
            raise KeyError(
                f"Graph endpoint /me/manager: {body}: {err}"
            ) from err
        return True


@retry
async def get_member_of(aiomsal: AsyncMSAL) -> None:
    """Load user info from MS graph API. Requires User.Read permissions."""
    async with aiomsal.get(
            "https://graph.microsoft.com/v1.0/me/memberOf") as res:
        body = await res.json()
        if 'error' in body:
            e = body['error']
            _LOGGER.error('{}: {}'.format(e['code'], e['message']))
            return False
        try:
            _LOGGER.debug(f'get_member_of: {body}')
            groups = []
            for rec in body['value']:
                if rec['@odata.type'] == '#microsoft.graph.group':
                    groups.append(rec['id'])
            aiomsal.session["wids"] = groups  # body
        except KeyError as err:
            raise KeyError(
                f"Graph endpoint /me/memberOf: {body}: {err}"
            ) from err
        return True
