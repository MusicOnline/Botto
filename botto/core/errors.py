from typing import Any, List

from discord.ext import commands  # type: ignore


class BotMissingFundamentalPermissions(commands.CheckFailure):
    def __init__(self, missing_perms: List[str], *args: Any) -> None:
        self.missing_perms = missing_perms
        self.send_messages = "send_messages" not in missing_perms

        missing = [
            perm.replace("_", " ").replace("guild", "server").title()
            for perm in missing_perms
        ]

        if len(missing) > 2:
            fmt = "{}, and {}".format(", ".join(missing[:-1]), missing[-1])
        else:
            fmt = " and ".join(missing)

        message = f"Botto requires {fmt} permission(s) to function."

        super().__init__(message, *args)
