from discord.ext import commands

from .context import Context
from .errors import NotConnectedToRestrictedApi


def require_restricted_api():
    def predicate(ctx: Context) -> bool:
        cog = ctx.bot.get_cog("RestrictedApi")
        if not cog or not cog.websocket:
            raise NotConnectedToRestrictedApi
        return True

    return commands.check(predicate)
