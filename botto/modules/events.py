import asyncio
import datetime
import logging
import traceback
from types import TracebackType
from typing import List, Optional, Tuple, Type

import aiohttp
import discord
from discord.ext import commands

import botto


logger = logging.getLogger("botto.events")  # pylint: disable=invalid-name


class Events(commands.Cog):
    def __init__(self, bot: botto.Botto) -> None:
        self.bot: botto.Botto = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        mentions: List[str] = [f"<@{self.bot.user.id}>", f"<@!{self.bot.user.id}>"]
        if (
            message.author.bot
            or message.content not in mentions
            or not message.channel.permissions_for(self.bot.user).send_messages
        ):
            return
        # Note: Change this if not using commands.when_mentioned_or(*prefixes).
        if botto.config["PREFIXES"]:
            prefixes = botto.config["PREFIXES"]
            content = (
                f"My commands prefixes are {self.bot.user.mention} and "
                f"`{prefixes[0]}`. Commands can be viewed using the "
                f"`{prefixes[0]}help` command."
            )
        else:
            content = (
                f"My command prefix is {self.bot.user.mention}. Commands can be viewed "
                f"using the `@{self.bot.user.name} help` command."
            )

        await message.reply(
            "Hello! " + content, allowed_mentions=discord.AllowedMentions(users=True)
        )

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild) -> None:
        line = f"Joined guild named '{guild}' (ID: {guild.id})."
        logger.info(line)
        embed: discord.Embed = discord.Embed(
            color=discord.Color.green(),
            timestamp=datetime.datetime.utcnow(),
            description=line,
        )
        await self.bot.send_console(embed=embed)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild) -> None:
        line = f"Removed from guild named '{guild}' (ID: {guild.id})."
        logger.info(line)
        embed: discord.Embed = discord.Embed(
            color=discord.Color.gold(),
            timestamp=datetime.datetime.utcnow(),
            description=line,
        )
        await self.bot.send_console(embed=embed)

    @commands.Cog.listener()
    async def on_command(self, ctx: botto.Context) -> None:
        logger.info("Command '%s' was called by %s.", ctx.command, ctx.author)

    @commands.Cog.listener()
    async def on_restricted_api_event_handler_error(
        self, event_method: str, payload: dict, error: Exception
    ) -> None:
        message: Optional[discord.Message] = discord.utils.get(
            self.bot.cached_messages, id=payload["ctx"]["message"]["id"]
        )
        if message is None:
            channel: botto.utils.OptionalChannel = self.bot.get_channel(
                payload["ctx"]["channel"]["id"]
            )
            if channel is not None:
                assert isinstance(channel, (discord.DMChannel, discord.TextChannel))
                try:
                    message = await channel.fetch_message(payload["ctx"]["message"]["id"])
                except discord.HTTPException:
                    pass

        if message:
            ctx: botto.Context = await self.bot.get_context(message, cls=botto.Context)
            await self.on_command_error(ctx, error, restricted_api_event=event_method)

        logger.debug(
            (
                "Unhandled exception in '%s' restricted API handler "
                "with invocation message not found. (%s: %s)"
            ),
            event_method,
            type(error).__name__,
            error,
            exc_info=(type(error), error, error.__traceback__),
        )

    @commands.Cog.listener()  # noqa: C901
    async def on_command_error(
        self, ctx: botto.Context, error: Exception, restricted_api_event: Optional[str] = None
    ) -> None:
        # error is not typehinted as commands.CommandError
        # because error.original is not one

        if isinstance(error, commands.CommandInvokeError):
            error = error.original

        if isinstance(error, botto.BotMissingFundamentalPermissions):
            if error.send_messages:
                await ctx.reply(error)
            return

        if isinstance(error, asyncio.TimeoutError):
            await ctx.reply("Tick tock. You took too long.")
            return

        if isinstance(error, commands.DisabledCommand):
            if hasattr(ctx.command, "disabled_reason"):
                await ctx.reply(
                    "This command has been disabled by the bot owner with the reason:\n"
                    + ctx.command.disabled_reason
                )
            else:
                await ctx.reply("This command has been disabled by the bot owner.")
            return

        if isinstance(error, commands.CommandOnCooldown):
            await ctx.reply(f"You are on cooldown. Retry in {error.retry_after:.1} second(s).")
            return

        if isinstance(error, botto.SubcommandRequired):
            help_command = self.bot.help_command.copy()
            help_command.context = ctx
            await ctx.reply(
                "Please use one of the subcommands listed below.",
                embed=await help_command.get_command_help(ctx.command),
            )
            return

        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply(
                f"You missed the `{error.param.name}` argument. "
                f"Here's the correct usage for the command.\n"
                f"```\n{ctx.prefix}{ctx.command} {ctx.command.signature}\n```"
            )
            return

        if isinstance(error, commands.BadArgument):
            error_msg = str(error)
            bad_conv = botto.utils.is_conversion_err(error)
            if bad_conv:
                conv_type, param = bad_conv
                if conv_type == "int":
                    error_msg = f'Failed to convert parameter "{param}" to an integer.'
                elif conv_type == "float":
                    error_msg = (
                        f'Failed to convert parameter "{param}" to a number with or '
                        f"without decimals."
                    )
            await ctx.reply(
                f"You passed a bad argument. Here's how bad it is.\n```\n{error_msg}\n```"
            )
            return

        if isinstance(error, commands.CheckFailure):
            message: str = str(error)
            if message and not message.startswith("The check functions for command"):
                await ctx.reply(message)
            return

        if isinstance(error, discord.HTTPException):
            too_long = botto.utils.is_too_long_err(error)
            if too_long:
                content_type, length = too_long
                await ctx.reply(
                    f"Tried to send a message with '{content_type}' of size over "
                    f"{length} and failed. If you think this shouldn't have "
                    f"happened, please report this to the developer."
                )
                return
            if botto.utils.is_bad_message_ref_err(error):
                return

        if isinstance(error, botto.NotConnectedToRestrictedApi):
            await ctx.reply("This command is currently unavailable. Please try again later.")
            return

        ignored = (commands.CommandNotFound, discord.Forbidden)

        if isinstance(error, ignored):
            return

        exc_info: Tuple[Type[Exception], Exception, TracebackType] = (
            type(error),
            error,
            error.__traceback__,
        )
        if restricted_api_event:
            logger.error(
                "Unhandled exception in restricted API handler '%s' of command '%s'. (%s: %s)",
                restricted_api_event,
                ctx.command,
                type(error).__name__,
                error,
                exc_info=exc_info,
            )
        else:
            logger.error(
                "Unhandled exception in '%s' command. (%s: %s)",
                ctx.command,
                type(error).__name__,
                error,
                exc_info=exc_info,
            )

        embed: discord.Embed = discord.Embed(
            color=discord.Color.red(),
            description=(
                f"The developer has been notified regarding this error.\n"
                f"Here's an apology cookie. \N{COOKIE}\n"
                f"```\n{type(error).__name__}"
            ),
        )
        if str(error):
            embed.description += f":\n{error}"
        embed.description += "\n```"
        embed.set_author(name="Beep boop. Unhandled exception.")
        try:
            await ctx.reply(embed=embed)
        except discord.HTTPException:
            pass

        # Log error to console channel
        full_tb: str = "".join(traceback.format_exception(*exc_info))
        hastebin_url: Optional[str]
        try:
            hastebin_url = await botto.utils.hastebin(full_tb, session=self.bot.session)
        except aiohttp.ClientResponseError:
            hastebin_url = "Failed to create hastebin."
        except ValueError:
            hastebin_url = None

        partial_tb: str = "".join(traceback.format_exception(*exc_info, limit=5))
        embed = discord.Embed(
            color=discord.Color.red(),
            description=(
                f"```py\n{botto.utils.limit_str(partial_tb, 1900)}\n```"
                + (f"\nFull traceback: {hastebin_url}" if hastebin_url else "")
            ),
            timestamp=ctx.message.created_at,
        )
        embed.set_author(name=f"Unexpected Exception - {type(error).__name__}")
        if restricted_api_event:
            embed.set_footer(
                text=(
                    f"From restricted API handler '{restricted_api_event}' "
                    f"of command '{ctx.command}'"
                )
            )
        else:
            embed.set_footer(text=f"From command '{ctx.command}'")
        embed.add_field(
            name="Command Caller",
            value=f"{ctx.author} `({ctx.author.id})`",
            inline=False,
        )
        if ctx.guild:
            embed.add_field(
                name="Call Origin",
                value=(
                    f"From '{ctx.channel}' `({ctx.channel.id})` "
                    f"of '{ctx.guild}' `({ctx.guild.id})`"
                ),
                inline=False,
            )
        else:
            embed.add_field(
                name="Call Origin",
                value=f"From DM channel `({ctx.channel.id})`",
                inline=False,
            )
        embed.add_field(
            name="Call Message",
            value=botto.utils.limit_str(ctx.message.content, 1024),
            inline=False,
        )

        await self.bot.send_console(embed=embed)


def setup(bot: botto.Botto) -> None:
    bot.add_cog(Events(bot))
