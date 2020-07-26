import asyncio
import copy
import datetime
import io
import logging
import os
import platform
import re
import shlex
import textwrap
import time
from contextlib import redirect_stdout
from subprocess import Popen, PIPE
from typing import Any, Dict, List, Match, Optional, Tuple

import aiohttp
import import_expression

import discord
from discord.ext import commands

import botto

actions_logger = logging.getLogger("botto.actions")  # pylint: disable=invalid-name


class Owner(commands.Cog, command_attrs=dict(hidden=True)):  # type: ignore
    """Developer and owner-only commands."""

    def __init__(self, bot: botto.Botto) -> None:
        self.bot: botto.Botto = bot
        self._last_result: Optional[Any] = None

    async def cog_check(  # pylint: disable=invalid-overridden-method
        self, ctx: botto.Context
    ) -> bool:
        return await self.bot.is_owner(ctx.author)

    @staticmethod
    def _cleanup_code(content: str) -> str:
        """Remove code blocks from content for evaluation."""
        if content.startswith("```") and content.endswith("```"):
            return "\n".join(content.split("\n")[1:-1])

        return content.strip("` \n")

    @staticmethod
    def _get_origin(ctx: botto.Context) -> str:
        """Format channel and guild name."""
        origin: str = f"'{ctx.channel}'"
        if ctx.guild:
            origin += f" of '{ctx.guild}'"
        return origin

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        """Delete gist in message by reacting with :wastebucket:."""
        if str(payload.emoji) != "\N{WASTEBASKET}" or payload.user_id != self.bot.owner_id:
            return

        channel: botto.utils.OptionalChannel = self.bot.get_channel(payload.channel_id)
        assert isinstance(channel, discord.abc.Messageable)
        message: discord.Message = await channel.fetch_message(payload.message_id)

        if message.author != self.bot.user or not message.embeds:
            return

        match: Optional[Match] = re.search(
            r"\(https://gist\.github\.com/(.+)\)", message.embeds[0].description or ""
        )
        if match is None:
            return

        gist_id: str = match.group(1)

        if not botto.config["GITHUB_TOKEN"]:
            actions_logger.error(
                "Failed to delete gist %s in message ID: %s, GITHUB_TOKEN not set in "
                "config file.",
                gist_id,
                message.id,
            )
            return

        github_token = botto.config["GITHUB_TOKEN"]
        url: str = f"https://api.github.com/gists/{gist_id}"
        headers: Dict[str, str] = {"Authorization": f"token {github_token}"}

        try:
            await self.bot.session.delete(url, headers=headers)
        except aiohttp.ClientResponseError as exc:
            actions_logger.error(
                "Failed to delete gist %s in message ID: %s, server returned %s %s.",
                gist_id,
                message.id,
                exc.code,
                exc.message,
            )
            return

        actions_logger.info("Deleted gist %s in message ID: %s.", gist_id, message.id)

        embed: discord.Embed = message.embeds[0]
        embed.description = "The gist containing the results was deleted."

        try:
            await message.edit(embed=embed)
            await message.remove_reaction("\N{WASTEBASKET}", self.bot.user)
            await message.remove_reaction("\N{WASTEBASKET}", discord.Object(payload.user_id))
        except (discord.Forbidden, discord.NotFound):
            pass

    # ------ Simple commands ------

    @botto.command()
    async def echo(self, ctx: botto.Context, *, content: str) -> None:
        """Echo a message."""
        await ctx.send(content)

    @botto.command(name="cls")
    async def clear_terminal(self, ctx: botto.Context) -> None:
        """Clear terminal."""
        if os.name == "nt":
            os.system("cls")
        else:
            os.system("clear")
        await ctx.send("Cleared terminal buffer.")

    @botto.command()
    async def shutdown(self, ctx: botto.Context) -> None:
        """Disconnect the bot from Discord and ends its processes."""
        await ctx.send("Shutdown initiated.")
        await self.bot.logout()

    @botto.command()
    async def logs(self, ctx: botto.Context) -> None:
        """DM bot logs."""
        with open("botto.log") as file:
            content: str = file.read()
            mystbin: str = await ctx.mystbin(content)
            await ctx.author.send(f"Logs: {mystbin}")
            await ctx.message.add_reaction("\N{OPEN MAILBOX WITH RAISED FLAG}")

    @botto.command(aliases=["runas"])
    async def pseudo(self, ctx: botto.Context, user: discord.Member, *, message: str) -> None:
        """Run a command as another user."""
        msg: discord.Message = copy.copy(ctx.message)
        msg.content = message
        msg.author = user
        self.bot.dispatch("message", msg)

    # ------ Module loading ------

    @botto.command()
    async def modules(self, ctx: botto.Context) -> None:
        """Show loaded modules."""
        await ctx.send("\n".join(self.bot.extensions.keys()))

    @botto.command()
    async def load(self, ctx: botto.Context, module: str) -> None:
        """Load a module."""
        if not module.startswith("botto.modules."):
            module = f"botto.modules.{module}"

        self.bot.load_extension(module)
        await ctx.send(f"Successfully loaded '{module}' module.")

    @botto.command()
    async def unload(self, ctx: botto.Context, module: str) -> None:
        """Unload a module."""
        if not module.startswith("botto.modules."):
            module = f"botto.modules.{module}"

        self.bot.unload_extension(module)
        await ctx.send(f"Successfully unloaded '{module}' module.")

    @botto.command()
    async def reload(self, ctx: botto.Context, module: str) -> None:
        """Reload a module."""
        if not module.startswith("botto.modules."):
            module = f"botto.modules.{module}"

        self.bot.reload_extension(module)
        await ctx.send(f"Successfully reloaded '{module}' module.")

    # ------ Profile editing ------

    @botto.group(invoke_without_command=True)
    async def edit(self, ctx: botto.Context) -> None:
        """Edit the bot's profile attributes."""
        raise botto.SubcommandRequired

    @edit.command()
    async def username(self, ctx: botto.Context, *, name: str) -> None:
        """Change the bot's username."""
        await self.bot.user.edit(username=name)
        await ctx.send(f"Client's username is now {self.bot.user}.")

    @edit.command()
    async def avatar(self, ctx: botto.Context, *, url: Optional[str] = None) -> None:
        """Change the bot's avatar."""
        avatar: Optional[bytes] = None
        if url is not None:
            avatar = await ctx.get_as_bytes(url)
        elif ctx.message.attachments:
            avatar = await ctx.get_as_bytes(ctx.message.attachments[0].url)
        if avatar is None:
            await ctx.send("No image was passed.")
            return

        await self.bot.user.edit(avatar=avatar)
        await ctx.send("Client's avatar has been updated.")

    # ------ Testing errors ------

    @botto.command()
    async def testerror(self, ctx: botto.Context) -> None:
        """Test response on unexpected error."""
        raise RuntimeError("This is a test error.")

    @botto.command()
    async def testfundamentalerror(self, ctx: botto.Context) -> None:
        """Test response when bot is missing fundamental permissions."""
        raise botto.BotMissingFundamentalPermissions(["abstract_authority"])

    # ------ Code ------

    @botto.command()
    async def codestats(self, ctx: botto.Context) -> None:
        """Show code statistics of the bot."""
        lines: Dict[str, int] = {"py": 0}

        for root, _, files in os.walk("."):
            if any(path in root for path in [".git", "__pycache__", "venv"]):
                continue

            for filename in files:
                if not filename.endswith(tuple(f".{ext}" for ext in lines)):
                    continue

                f_ext: str = filename.split(".")[-1]
                with open(os.path.join(root, filename), encoding="utf-8") as file:
                    lines[f_ext] += sum(1 for line in file.readlines() if line != "\n")

                await asyncio.sleep(0)

        await ctx.send(f"{lines['py']} lines of Python code written.")

    # ------ Eval commands ------

    @botto.command()
    async def shell(self, ctx: botto.Context, *, command: str) -> None:
        """Run a shell command."""

        def run_shell(argv: List[str]) -> List[str]:
            with Popen(argv, stdout=PIPE, stderr=PIPE, shell=True) as proc:
                return [std.decode("utf-8") for std in proc.communicate()]

        await ctx.message.add_reaction(botto.aLOADING)
        command = self._cleanup_code(command)
        argv: List[str] = shlex.split(command)
        start: float = time.perf_counter()
        stdout, stderr = await self.bot.loop.run_in_executor(None, run_shell, argv)
        delta: float = (time.perf_counter() - start) * 1000
        timestamp: datetime.datetime = ctx.message.created_at
        await ctx.message.remove_reaction(botto.aLOADING, ctx.me)

        result: List[str] = ["```"]
        to_upload: List[Tuple[str, str]] = [("command.txt", command)]
        if stdout:
            result.append(f"stdout:\n{stdout}")
            to_upload.append(("stdout.txt", stdout))
        if stderr:
            result.append(f"stderr:\n{stderr}")
            to_upload.append(("stderr.txt", stderr))
        result.append("```")

        await ctx.message.add_reaction(botto.CHECK)

        # If there's no output, the command is done.
        if len(result) == 2:
            return

        result_string: str = "\n".join(result)
        is_uploaded: bool = False

        if len(result_string) > 2048:
            url: str = await ctx.gist(
                *to_upload,
                description=(f"Shell command results from {self._get_origin(ctx)} at {timestamp}."),
            )
            result_string = f"Results too long. View them [here]({url})."
            is_uploaded = True

        embed: discord.Embed = discord.Embed(
            description=result_string, timestamp=timestamp, color=botto.config["MAIN_COLOR"],
        )
        embed.set_author(name="Shell Command Results")
        embed.set_footer(text=f"Took {delta:.2f} ms")

        message = await ctx.send(embed=embed)
        if is_uploaded:
            await message.add_reaction("\N{WASTEBASKET}")

    @botto.command(name="eval")  # noqa: C901
    async def eval_command(self, ctx: botto.Context, *, code: str) -> None:
        """Evaluate a block of code."""
        await ctx.message.add_reaction(botto.aLOADING)
        env = {
            "bot": self.bot,
            "ctx": ctx,
            "channel": ctx.channel,
            "author": ctx.author,
            "guild": ctx.guild,
            "message": ctx.message,
            "session": self.bot.session,
            "_": self._last_result,
        }
        env.update(globals())
        code = self._cleanup_code(code)
        stdout: io.StringIO = io.StringIO()
        to_compile: str = f"async def func():\n{textwrap.indent(code, '  ')}"

        # Defining the async function.
        try:
            import_expression.exec(to_compile, env)
        except Exception as exc:  # pylint: disable=broad-except
            try:
                await ctx.message.remove_reaction(botto.aLOADING, ctx.me)
                await ctx.message.add_reaction(botto.CROSS)
            except discord.NotFound:
                pass  # Ignore if command message was deleted
            await ctx.send(f"{type(exc).__name__} occurred. Check your code.")
            return

        func = env["func"]

        # Executing the async function.
        try:
            start: float = time.perf_counter()
            with redirect_stdout(stdout):
                ret: Any = await func()
        except Exception as exc:  # pylint: disable=broad-except
            try:
                await ctx.message.remove_reaction(botto.aLOADING, ctx.me)
                await ctx.message.add_reaction(botto.CROSS)
            except discord.NotFound:
                pass  # Ignore if command message was deleted
            await ctx.send(f"{type(exc).__name__} occurred.\n{str(exc)}")
            return

        # When code execution is successful
        delta: float = (time.perf_counter() - start) * 1000
        value: str = stdout.getvalue()

        # Try to unreact
        try:
            await ctx.message.remove_reaction(botto.aLOADING, ctx.me)
            await ctx.message.add_reaction(botto.CHECK)
        except discord.NotFound:
            if not value and ret is None:
                await ctx.send(f"{ctx.author.mention} Code execution completed in {delta:.2f} ms.")

        if not value and ret is None:
            return

        # If there is stdout and return value
        embed: discord.Embed = discord.Embed(
            timestamp=ctx.message.created_at, color=botto.config["MAIN_COLOR"]
        )
        embed.set_author(name="Code Evaluation")
        embed.set_footer(text=f"Took {delta:.2f} ms with Python {platform.python_version()}")

        result: List[str] = ["```py"]
        to_upload: List[Tuple[str, str]] = [("code.py", code)]
        if value:
            result.append(f"# stdout:\n{value}")
            to_upload.append(("stdout.txt", value))
        if ret is not None:
            self._last_result = ret
            result.append(f"# return:\n{ret!r}")
            to_upload.append(("return.py", repr(ret)))
        result.append("```")

        result_string: str = "\n".join(result)
        uploaded_to: Optional[str] = None
        file: Optional[discord.File] = None

        if len(result_string) <= 2048:
            embed.description = result_string
        else:
            try:
                url: str = await ctx.gist(
                    *to_upload,
                    description=(
                        f"Eval command results from {self._get_origin(ctx)} "
                        f"at {embed.timestamp}."
                    ),
                )
            except (aiohttp.ClientResponseError, ValueError):
                try:
                    url = await ctx.mystbin(
                        f"Eval command results from {self._get_origin(ctx)} "
                        f"at {embed.timestamp}.\n\n{result_string[6:-4]}"
                    )
                except aiohttp.ClientResponseError:
                    # If 8MB is insufficient, give up
                    file = discord.File(io.StringIO(result_string[6:-4]), "results.txt")
                    embed.description = "Results too long. View them in the file."
                else:
                    uploaded_to = "mystbin"
            else:
                uploaded_to = "github"

        if uploaded_to:
            embed.description = f"Results too long. View them [here]({url})."

        message = await ctx.send(embed=embed, file=file)
        if uploaded_to == "github":
            await message.add_reaction("\N{WASTEBASKET}")


def setup(bot: botto.Botto) -> None:
    bot.add_cog(Owner(bot))
