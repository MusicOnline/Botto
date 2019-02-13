import asyncio
import logging
import traceback
from typing import List

import discord  # type: ignore
from discord.ext import commands  # type: ignore

import botto


logger = logging.getLogger(__name__)


class Events:
    def __init__(self, bot: botto.Botto) -> None:
        self.bot: botto.Botto = bot

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or not message.content:
            return

        mentions: List[str] = [f"<@{self.bot.user.id}>", f"<@!{self.bot.user.id}>"]
        if message.content in mentions:
            try:
                await message.channel.send(
                    f"Hello! My command prefixes are {self.bot.user.mention} "
                    f"and `botto`. Commands can be viewed with the help command."
                )
            except discord.Forbidden:
                pass

    async def on_guild_join(self, guild: discord.Guild) -> None:
        logger.info("Joined guild named '%s' (ID: %s).", guild, guild.id)

    async def on_guild_remove(self, guild: discord.Guild) -> None:
        logger.info("Removed from guild named '%s' (ID: %s).", guild, guild.id)

    async def on_command(self, ctx: botto.Context) -> None:
        logger.info("Command '%s' was called by %s.", ctx.command, ctx.author)

    async def on_command_error(self, ctx: botto.Context, error: Exception) -> None:
        # error is not typehinted as commands.CommandError
        # because error.original is not one

        if isinstance(error, commands.CommandInvokeError):
            error = error.original

        if isinstance(error, botto.BotMissingFundamentalPermissions):
            if error.send_messages:
                await ctx.send(error)
            return

        if isinstance(error, asyncio.TimeoutError):
            await ctx.send("Tick tock. You took too long.")
            return

        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                f"You missed the `{error.param.name}` argument. "
                f"Here's the correct usage for the command.\n"
                f"```\n{ctx.prefix}{ctx.command.signature}\n```"
            )
            return

        if isinstance(error, commands.CheckFailure):
            message: str = str(error)
            if message and not message.startswith("The check functions for command"):
                await ctx.send(message)
            return

        ignored = (commands.CommandNotFound,)

        if isinstance(error, ignored):
            return

        logger.error(
            "Unhandled exception in '%s' command. (%s: %s)",
            ctx.command,
            error.__class__.__name__,
            error,
        )

        exc_info: List[str] = traceback.format_exception(
            type(error), error, error.__traceback__
        )
        logger.error("\n".join(exc_info))

        embed: discord.Embed = discord.Embed(
            colour=discord.Colour.red(),
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
            await ctx.send(embed=embed)
        except discord.HTTPException:
            pass

        # Log error to console channel
        formatted_exc = botto.utils.hidden_format_exc(error, limit=5)
        embed = discord.Embed(
            colour=discord.Colour.red(),
            description=f"```py\n{botto.utils.limit_str(formatted_exc, 2000)}\n```",
            timestamp=ctx.message.created_at,
        )
        embed.set_author(name=f"An Error Occured - {type(error).__name__}")
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

        await self.bot.get_owner().send(embed=embed)


def setup(bot: botto.Botto) -> None:
    bot.add_cog(Events(bot))
