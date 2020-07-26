from typing import Any, List

from discord.ext import commands


class BotMissingFundamentalPermissions(commands.CheckFailure):
    def __init__(self, missing_perms: List[str], *args: Any) -> None:
        self.missing_perms: List[str] = missing_perms
        self.send_messages: bool = "send_messages" not in missing_perms

        missing: List[str] = [
            perm.replace("_", " ").replace("guild", "server").title() for perm in missing_perms
        ]

        if len(missing) > 2:
            fmt: str = "{}, and {}".format(", ".join(missing[:-1]), missing[-1])
        else:
            fmt = " and ".join(missing)

        message: str = f"The bot requires {fmt} permission(s) to function."

        super().__init__(message, *args)


class SubcommandRequired(commands.CommandError):
    pass
