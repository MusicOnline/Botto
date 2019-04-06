import functools

from discord.ext import commands  # type: ignore
from discord.ext.commands.core import hooked_wrapped_callback  # type: ignore


class Command(commands.Command):
    pass


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


class Group(GroupMixin, Command):
    def __init__(self, *args, **attrs):
        self.invoke_without_command = attrs.pop("invoke_without_command", False)
        super().__init__(*args, **attrs)

    def copy(self):
        ret = super().copy()
        for cmd in self.commands:
            ret.add_command(cmd.copy())
        return ret

    async def invoke(self, ctx):
        early_invoke = not self.invoke_without_command
        if early_invoke:
            await self.prepare(ctx)

        view = ctx.view
        previous = view.index
        view.skip_ws()
        trigger = view.get_word()

        if trigger:
            ctx.subcommand_passed = trigger
            ctx.invoked_subcommand = self.all_commands.get(trigger, None)

        if early_invoke:
            injected = hooked_wrapped_callback(self, ctx, self.callback)
            await injected(*ctx.args, **ctx.kwargs)

        if trigger and ctx.invoked_subcommand:
            ctx.invoked_with = trigger
            await ctx.invoked_subcommand.invoke(ctx)
        elif not early_invoke:
            # undo the trigger parsing
            view.index = previous
            view.previous = previous
            await super().invoke(ctx)

    async def reinvoke(self, ctx, *, call_hooks=False):
        early_invoke = not self.invoke_without_command
        if early_invoke:
            ctx.command = self
            await self._parse_arguments(ctx)

            if call_hooks:
                await self.call_before_hooks(ctx)

        view = ctx.view
        previous = view.index
        view.skip_ws()
        trigger = view.get_word()

        if trigger:
            ctx.subcommand_passed = trigger
            ctx.invoked_subcommand = self.all_commands.get(trigger, None)

        if early_invoke:
            try:
                await self.callback(*ctx.args, **ctx.kwargs)
            except:
                ctx.command_failed = True
                raise
            finally:
                if call_hooks:
                    await self.call_after_hooks(ctx)

        if trigger and ctx.invoked_subcommand:
            ctx.invoked_with = trigger
            await ctx.invoked_subcommand.reinvoke(ctx, call_hooks=call_hooks)
        elif not early_invoke:
            # undo the trigger parsing
            view.index = previous
            view.previous = previous
            await super().reinvoke(ctx, call_hooks=call_hooks)


command = functools.partial(commands.command, cls=Command)
group = functools.partial(commands.command, cls=Group)
