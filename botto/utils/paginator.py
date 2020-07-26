"""Embed Paginator (originally for RoboDanny) by Rapptz

Licensed under MIT.
Modified by Music#9755 (MusicOnline).

GitHub source: https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/utils/paginator.py
"""

import asyncio

import discord

from botto import config  # pylint: disable=cyclic-import

FIRST_PAGE = "\N{BLACK LEFT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}"
PREVIOUS_PAGE = "\N{BLACK LEFT-POINTING TRIANGLE}"
NEXT_PAGE = "\N{BLACK RIGHT-POINTING TRIANGLE}"
LAST_PAGE = "\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}"
GOTO_PAGE = "\N{INPUT SYMBOL FOR NUMBERS}"
STOP_PAGINATION = "\N{BLACK SQUARE FOR STOP}"
GOTO_HELP = "\N{WHITE QUESTION MARK ORNAMENT}"


class EmbedPaginator:
    """Implements a paginator that queries the user for the pagination interface.

    Pages are 1-index based, not 0-index based.
    If the user does not reply within 2 minutes then the pagination interface exits
    automatically.

    Parameters
    ------------
    ctx: Context
        The context of the command.
    entries: List[str]
        A list of entries to paginate.
    per_page: int
        How many entries show up per page.
    message_content: Optional[str]
        The message content along with the embed.
    show_entry_count: bool
        Whether to show an entry count in the footer.
    numbered: bool
        Whether the entries should be numbered.
    jump_option: bool
        Whether the jump option should be available.
    help_option: bool
        Whether the usage help option should be available.

    Attributes
    -----------
    embed: discord.Embed
        The embed object that is being used to send pagination info.
        Feel free to modify this externally. Only the description,
    """

    def __init__(
        self,
        ctx,
        *,
        entries,
        per_page=12,
        message_content=None,
        show_entry_count=True,
        numbered=False,
        jump_option=False,
        help_option=False,
    ):
        self.ctx = ctx
        self.bot = ctx.bot
        self.message = ctx.message
        self.channel = ctx.channel
        self.author = ctx.author

        self.entries = entries
        self.per_page = per_page
        self.message_content = message_content
        self.show_entry_count = show_entry_count
        self.numbered = numbered
        self.help_option = help_option
        pages, left_over = divmod(len(self.entries), self.per_page)
        pages += bool(left_over)
        self.current_page = 0
        self.maximum_pages = pages
        self.embed = discord.Embed(color=config["MAIN_COLOR"])
        self.paginating = len(entries) > per_page
        self.match = None
        self.reaction_emojis = [
            (FIRST_PAGE, self.first_page),
            (PREVIOUS_PAGE, self.previous_page),
            (NEXT_PAGE, self.next_page),
            (LAST_PAGE, self.last_page),
            (GOTO_PAGE, self.numbered_page),
            (STOP_PAGINATION, self.stop_pagination),
            (GOTO_HELP, self.show_help),
        ]
        if not jump_option:
            self.reaction_emojis.remove((GOTO_PAGE, self.numbered_page))
        if not help_option:
            self.reaction_emojis.remove((GOTO_HELP, self.show_help))

    def get_page(self, page):
        base = (page - 1) * self.per_page
        return self.entries[base : base + self.per_page]

    async def show_page(self, page, *, first=False):
        self.current_page = page
        entries = self.get_page(page)
        lines = []
        if self.numbered:
            for index, entry in enumerate(entries, 1 + ((page - 1) * self.per_page)):
                lines.append(f"{index}. {entry}")
        else:
            lines.extend(f"{entry}" for entry in entries)

        if self.maximum_pages > 1:
            if self.show_entry_count:
                text = f"Page {page}/{self.maximum_pages} ({len(self.entries)} entries)"
            else:
                text = f"Page {page}/{self.maximum_pages}"

            self.embed.set_footer(text=text)

        if not self.paginating:
            self.embed.description = "\n".join(lines)
            return await self.ctx.send(self.message_content, embed=self.embed)

        if not first:
            self.embed.description = "\n".join(lines)
            await self.message.edit(content=self.message_content, embed=self.embed)
            return

        if self.help_option:
            lines.append("")
            lines.append(f"{GOTO_HELP} React with this for information.")

        self.embed.description = "\n".join(lines)
        self.message = await self.ctx.send(self.message_content, embed=self.embed)

        for (reaction, _) in self.reaction_emojis:
            if self.maximum_pages == 2 and reaction in (FIRST_PAGE, LAST_PAGE):
                # Don't add |<< or >>| buttons if there is only two pages
                # But we still accept it nonetheless if user reacts
                continue
            await self.message.add_reaction(reaction)

    async def checked_show_page(self, page):
        if page != 0 and page <= self.maximum_pages:
            await self.show_page(page)

    async def first_page(self):
        """Navigate to the first page."""
        await self.show_page(1)

    async def last_page(self):
        """Navigate to the last page."""
        await self.show_page(self.maximum_pages)

    async def next_page(self):
        """Go to the next page."""
        await self.checked_show_page(self.current_page + 1)

    async def previous_page(self):
        """Go to the previous page."""
        await self.checked_show_page(self.current_page - 1)

    async def show_current_page(self):
        if self.paginating:
            await self.show_page(self.current_page)

    async def numbered_page(self):
        """Jump to a specified page number."""
        to_delete = []
        to_delete.append(await self.ctx.send("What page do you want to go to?"))

        def check(message):
            return (
                message.author == self.author
                and self.channel == message.channel
                and message.content.isdigit()
            )

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=30.0)
        except asyncio.TimeoutError:
            to_delete.append(await self.ctx.send("Took too long."))
            await asyncio.sleep(5)
        else:
            page = int(msg.content)
            to_delete.append(msg)
            if page != 0 and page <= self.maximum_pages:
                await self.show_page(page)
            else:
                to_delete.append(
                    await self.ctx.send(f"Invalid page given. ({page}/{self.maximum_pages})")
                )
                await asyncio.sleep(5)

        try:
            await self.channel.delete_messages(to_delete)
        except Exception:  # pylint: disable=broad-except
            pass

    async def show_help(self):
        """Show the interactive paginator instructions."""
        messages = ["This is an interactive paginator.\n"]
        messages.append("You can use the following reactions to navigate through its entries:\n")

        for (emoji, func) in self.reaction_emojis:
            messages.append(f"{emoji} {func.__doc__}")

        self.embed.description = "\n".join(messages)
        self.embed.clear_fields()
        self.embed.set_footer(text=f"You were on page {self.current_page} before this message.")
        await self.message.edit(embed=self.embed)

        async def go_back_to_current_page():
            await asyncio.sleep(60)
            await self.show_current_page()

        self.bot.loop.create_task(go_back_to_current_page())

    async def stop_pagination(self):
        """Stop the interactive paginator session."""
        self.bot.loop.create_task(self.remove_reactions())
        self.paginating = False

    async def remove_reactions(self, *, individually=True):
        try:
            await self.message.clear_reactions()
        except Exception:  # pylint: disable=broad-except
            if not individually:
                return

            for (reaction, _) in self.reaction_emojis:
                if self.maximum_pages == 2 and reaction in (FIRST_PAGE, LAST_PAGE):
                    # |<< or >>| buttons were not added so skip
                    continue
                try:
                    await self.message.remove_reaction(reaction, self.ctx.me)
                except Exception:  # pylint: disable=broad-except
                    pass

    def react_check(self, reaction, user):
        if user.id != self.author.id:
            return False

        if reaction.message.id != self.message.id:
            return False

        for (emoji, func) in self.reaction_emojis:
            if reaction.emoji == emoji:
                self.match = func
                return True
        return False

    async def paginate(self):
        """Paginate the entries and run the interactive loop if necessary."""
        first_page = self.show_page(1, first=True)
        if not self.paginating:
            await first_page
        else:
            # Allow us to react to reactions right away if we're paginating
            self.bot.loop.create_task(first_page)

        while self.paginating:
            done, pending = await asyncio.wait(
                [
                    self.bot.wait_for("reaction_add", check=self.react_check, timeout=120),
                    self.bot.wait_for("reaction_remove", check=self.react_check, timeout=120),
                ],
                return_when=asyncio.FIRST_COMPLETED,
            )
            try:
                done.pop().result()
            except asyncio.TimeoutError:
                self.paginating = False
                self.bot.loop.create_task(self.remove_reactions())
            else:
                await self.match()
            finally:
                for future in pending:
                    future.cancel()
