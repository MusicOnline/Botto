import platform
import datetime

import discord
from discord.ext import commands

import botto


class Meta(commands.Cog):
    """Meta commands related to the bot."""

    def __init__(self, bot: botto.Botto) -> None:
        self.bot: botto.Botto = bot

    def get_statistics_embed(self) -> discord.Embed:
        embed: discord.Embed = discord.Embed(
            color=botto.config["MAIN_COLOR"], timestamp=datetime.datetime.utcnow()
        )
        embed.set_thumbnail(url=self.bot.user.avatar_url)

        # Guild Stats field (optional)
        if botto.config["INTENTS"]["GUILDS"]:
            total_guilds: int = self.bot.guild_count
            text_channels: int = sum(
                1
                for channel in self.bot.get_all_channels()
                if isinstance(channel, discord.TextChannel)
            )
            voice_channels: int = sum(
                1
                for channel in self.bot.get_all_channels()
                if isinstance(channel, discord.VoiceChannel)
            )
            embed.add_field(
                name="Guild Stats",
                value=(
                    f"{total_guilds} guilds\n"
                    f"{text_channels} text channels\n"
                    f"{voice_channels} voice channels"
                ),
            )

        # Member Stats field (optional)
        if botto.config["INTENTS"]["MEMBERS"]:
            total_members: int = sum(1 for m in self.bot.get_all_members())
            total_users: int = self.bot.user_count
            extra_user_info: str
            if botto.config["INTENTS"]["PRESENCES"]:
                total_online: int = len(
                    {
                        m
                        for m in self.bot.get_all_members()
                        if m.status is not discord.Status.offline
                    }
                )
                extra_user_info = f"{total_online} users online"
            else:
                total_bots: int = len({m for m in self.bot.get_all_members() if not m.bot})
                extra_user_info = f"incl. {total_bots} bots"
            embed.add_field(
                name="Member Stats",
                value=(
                    f"{total_members} total members\n{total_users} unqiue users\n{extra_user_info}"
                ),
            )

        # Versions field
        embed.add_field(
            name="Versions",
            value=(f"Python {platform.python_version()}\ndiscord.py {discord.__version__}"),
        )

        # Uptime field
        assert self.bot.ready_time is not None
        up_since: str = self.bot.ready_time.strftime("%d %b %y")
        embed.add_field(
            name="Uptime",
            value=(f"{self.bot.humanize_uptime(brief=True)}\n(Since {up_since} UTC)"),
        )

        # Discord connection field
        embed.add_field(name="Discord", value=f"{self.bot.ping} ms latest")

        # Restricted API connection field (optional)
        if self.bot.restricted_api_ping:
            embed.add_field(name="Internal API", value=f"{self.bot.restricted_api_ping} ms latest")

        # Process stats field
        with self.bot.process.oneshot():
            cpu_usage: float = self.bot.process.cpu_percent()
            ram_usage: float = self.bot.process.memory_full_info().uss / 2 ** 20
        embed.add_field(name="Process", value=f"{cpu_usage}% CPU\n{ram_usage:.2f} MiB")

        return embed

    @botto.command()
    async def botstats(self, ctx: botto.Context) -> None:
        """Show general statistics of the bot."""
        embed: discord.Embed = self.get_statistics_embed()
        await ctx.reply(embed=embed)

    @botto.command()
    async def ping(self, ctx: botto.Context) -> None:
        """Show connection statistics of the bot."""
        text: str = f"Discord pong: **{self.bot.ping} ms**"
        if self.bot.restricted_api_ping:
            text += f"\nInternal bot API pong: **{self.bot.restricted_api_ping} ms**"
        await ctx.reply(text)

    @botto.command()
    async def uptime(self, ctx: botto.Context) -> None:
        """Show uptime of the bot."""
        await ctx.reply(f"Online since **{self.bot.humanize_uptime()}** ago.")

    @botto.command()
    async def invite(self, ctx: botto.Context) -> None:
        """Show invite link of the bot."""
        await ctx.reply(f"<{discord.utils.oauth_url(ctx.me.id)}>")

    @botto.command(enabled=bool(botto.config["SOURCE_CODE_URL"]))
    async def source(self, ctx: botto.Context) -> None:
        """Show GitHub link to source code."""
        await ctx.reply(botto.config["SOURCE_CODE_URL"])

    @botto.command(
        aliases=["suggest", "feedback", "report", "contact"],
        enabled=bool(botto.config["SUPPORT_SERVER_INVITE_URL"]),
    )
    async def support(self, ctx: botto.Context) -> None:
        """Show support server link."""
        await ctx.reply(botto.config["SUPPORT_SERVER_INVITE_URL"])

    @botto.command(enabled=bool(botto.config["VOTE_URL"]))
    async def vote(self, ctx: botto.Context) -> None:
        """Support the bot by voting!"""
        await ctx.reply(botto.config["VOTE_URL"])


def setup(bot: botto.Botto) -> None:
    bot.add_cog(Meta(bot))
