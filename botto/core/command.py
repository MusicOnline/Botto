import asyncio
import functools

import discord
import yaml
from discord.ext import commands


class Command(commands.Command):
    def help_embed(self, coro):
        if not asyncio.iscoroutinefunction(coro):
            raise TypeError("The help embed function must be a coroutine.")

        self._help_embed_func = coro
        return coro

    async def get_help_embed(self, helpcommand) -> discord.Embed:
        if self.cog:
            return await self._help_embed_func(self.cog, helpcommand)
        return await self._help_embed_func(helpcommand)

    def _ensure_assignment_on_copy(self, other):
        # Cogs make copies of commands
        # This needs to be overridden to keep _help_embed_func on copy
        other = super()._ensure_assignment_on_copy(other)

        try:
            other._help_embed_func = self._help_embed_func
        except AttributeError:
            pass
        return other

    @property
    def short_doc(self) -> str:
        if self.brief is not None:
            return self.brief
        if self.help is not None:
            items = yaml.full_load(self.help)
            if isinstance(items, dict):
                return items.get("short", "Information not available.")
            return self.help.split("\n", 1)[0]
        return "Information not available."


class GroupMixin(commands.GroupMixin):
    def command(self, *args, **kwargs):
        def decorator(func):
            kwargs.setdefault("parent", self)
            result = command(*args, **kwargs)(func)
            self.add_command(result)
            return result

        return decorator

    def group(self, *args, **kwargs):
        def decorator(func):
            kwargs.setdefault("parent", self)
            result = group(*args, **kwargs)(func)
            self.add_command(result)
            return result

        return decorator


class Group(GroupMixin, Command, commands.Group):
    pass


command = functools.partial(commands.command, cls=Command)  # pylint: disable=invalid-name
group = functools.partial(commands.command, cls=Group)  # pylint: disable=invalid-name
