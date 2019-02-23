from typing import Dict, Iterator, List, Sequence, Tuple, Union

import discord  # type: ignore
from discord.ext import commands  # type: ignore

import botto


class Meta(commands.Cog):
    """Meta commands related to the bot."""

    def __init__(self, bot: botto.Botto) -> None:
        self.bot: botto.Botto = bot
        self.owner_show_hidden: bool = False
        self.cog_order: List[str] = ["Meta", "Owner", "Jishaku"]

    def get_statistics_embed(self) -> discord.Embed:
        total_members: int = sum(1 for m in self.bot.get_all_members())
        total_users: int = self.bot.user_count
        total_online: int = len(
            {
                m
                for m in self.bot.get_all_members()
                if m.status is not discord.Status.offline
            }
        )

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
        total_channels: int = text_channels + voice_channels

        total_guilds: int = self.bot.guild_count
        assert self.bot.ready_time is not None
        up_since: str = self.bot.ready_time.strftime("%d %b %y")
        ping: int = self.bot.ping
        with self.bot.process.oneshot():
            cpu_usage: float = self.bot.process.cpu_percent()
            ram_usage: float = self.bot.process.memory_full_info().uss / 2 ** 20

        embed: discord.Embed = discord.Embed(colour=botto.config.MAIN_COLOUR)
        embed.add_field(
            name="Member Stats",
            value=(
                f"{total_members} total members\n"
                f"{total_users} unqiue users\n"
                f"{total_online} users online"
            ),
        )
        embed.add_field(
            name="Channel Stats",
            value=(
                f"{total_channels} total\n"
                f"{text_channels} text channels\n"
                f"{voice_channels} voice channels"
            ),
        )
        embed.add_field(name="Other Stats", value=f"{total_guilds} guilds")
        embed.add_field(
            name="Uptime",
            value=(
                f"{self.bot.humanize_uptime(brief=True)}\n" f"(Since {up_since} UTC)"
            ),
        )
        embed.add_field(name="Connection", value=f"{ping} ms current")
        embed.add_field(name="Process", value=f"{cpu_usage}% CPU\n{ram_usage:.2f} MiB")

        return embed

    def _filter_cmd_list(
        self, ctx: botto.Context, group_or_cog: Union[commands.GroupMixin, commands.Cog]
    ) -> Iterator[commands.Command]:
        show_hidden: bool = self.bot.get_owner() == ctx.author and self.owner_show_hidden
        is_cog: bool = isinstance(group_or_cog, commands.Cog)

        def predicate(cmd: commands.Command) -> bool:
            if cmd.cog_name not in self.cog_order:
                return False
            if cmd.hidden and not show_hidden:
                return False
            if not isinstance(cmd, botto.Command):
                return False
            return True

        cmds: Sequence[
            commands.Command
        ] = group_or_cog.get_commands() if is_cog else group_or_cog.commands
        return filter(predicate, cmds)

    def _sort_cmd_list(
        self, cmd_list: Iterator[commands.Command]
    ) -> List[commands.Command]:
        def predicate(cmd: commands.Command) -> Tuple[int, str]:
            return self.cog_order.index(cmd.cog_name), cmd.name

        return sorted(cmd_list, key=predicate)

    def _format_cmd_list(self, ctx: botto.Context) -> discord.Embed:
        cmd_list: Iterator[commands.Command] = self._filter_cmd_list(ctx, ctx.bot)
        sorted_list: List[commands.Command] = self._sort_cmd_list(cmd_list)
        p: str = botto.config.PREFIXES[
            0
        ] if botto.config.PREFIXES else f"@{ctx.bot.user.name} "

        categories: Dict[str, List[str]] = {}
        for cmd in sorted_list:
            if cmd.cog_name not in categories:
                categories[cmd.cog_name] = []
            categories[cmd.cog_name].append(f"`{p}{cmd}` — {cmd.short_doc or 'TBA'}")

        embed: discord.Embed = discord.Embed(colour=botto.config.MAIN_COLOUR)
        embed.set_author(name="General Commands")
        for category, lines in categories.items():
            embed.add_field(name=category, value="\n".join(lines), inline=False)
        embed.set_footer(
            text=f"Type '{p}help [cmd]' for more information on a command."
        )
        return embed

    # TODO: Dealing with pagination properly with too much cogs!
    @botto.command(name="help")
    async def help_cmd(self, ctx: botto.Context, *command: str) -> None:
        """Show help."""
        embed: discord.Embed = discord.Embed(colour=botto.config.MAIN_COLOUR)
        p: str = botto.config.PREFIXES[
            0
        ] if botto.config.PREFIXES else f"@{ctx.bot.user.name} "

        def handle_command_embed(cmd: botto.Command) -> None:
            embed.set_author(name=cmd.signature_without_aliases)
            embed.description = cmd.help
            if cmd.aliases:
                embed.add_field(name="Aliases", value=" / ".join(cmd.aliases))

            if isinstance(cmd, botto.Group):
                subcmds = sorted(cmd.commands, key=lambda c: c.name)
                paged_subcmds = (subcmds[c : c + 5] for c in range(0, len(subcmds), 5))
                for i, page in enumerate(paged_subcmds, 1):
                    lines: List[str] = []
                    for subcmd in page:
                        lines.append(f"`{p}{subcmd}` — {subcmd.short_doc or 'TBA'}")
                    total_entries = len(subcmds)
                    min_index = 1 + (i - 1) * 5
                    max_index = min((i - 1) * 5, total_entries)
                    indices = f"{min_index} - {max_index} out of {total_entries}"
                    embed.add_field(
                        name=f"Subcommands ({indices})", value="\n".join(lines)
                    )

        if not command:
            embed = self._format_cmd_list(ctx)
        elif len(command) == 1:
            name = command[0]
            cog = self.bot.get_cog(name)
            if cog is not None and name in self.cog_order:
                cmd_list: List[commands.Command] = list(self._filter_cmd_list(ctx, cog))
                if cmd_list:
                    cmd_list = sorted(cmd_list, key=lambda cmd: cmd.name)
                    embed.set_author(name=f"{name} Commands")
                    embed.set_footer(
                        text=(f"Use '{p}help [cmd]' for more information on a command.")
                    )
                    embed.description = "\n".join(
                        f"`{p}{c}` — {c.short_doc or 'TBA'}" for c in cmd_list
                    )

            cmd = self.bot.get_command(name.lower())
            if not embed.author and isinstance(cmd, botto.Command):
                handle_command_embed(cmd)
        else:
            name = " ".join(command).lower()
            cmd = self.bot.get_command(name)
            if isinstance(cmd, botto.Command):
                handle_command_embed(cmd)

        if not embed.author:
            embed.colour = discord.Colour.red()
            embed.set_author(name=f"Could not find '{name}'. What's that?")

        await ctx.send(embed=embed)

    @botto.command()
    async def botstats(self, ctx: botto.Context) -> None:
        """Show general statistics of the bot."""
        embed: discord.Embed = self.get_statistics_embed()
        await ctx.send(embed=embed)

    @botto.command()
    async def ping(self, ctx: botto.Context) -> None:
        """Show connection statistics of the bot."""
        await ctx.send(f"ws pong: **{self.bot.ping} ms**")

    @botto.command()
    async def uptime(self, ctx: botto.Context) -> None:
        """Show uptime of the bot."""
        await ctx.send(f"Online since **{self.bot.humanize_uptime()}** ago.")

    @botto.command()
    async def invite(self, ctx: botto.Context) -> None:
        """Show invite link of the bot."""
        await ctx.send(f"<{discord.utils.oauth_url(ctx.me.id)}>")

    @botto.command(aliases=["suggest", "feedback", "report", "contact"])
    async def support(self, ctx: botto.Context) -> None:
        """Show support server link."""
        await ctx.send("Contact Music#9755 here: https://discord.gg/wp7Wxzs")


def setup(bot: botto.Botto) -> None:
    bot.add_cog(Meta(bot))
