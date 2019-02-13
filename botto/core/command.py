import functools

from discord.ext import commands  # type: ignore
from discord.ext.commands.core import hooked_wrapped_callback  # type: ignore


class Command(commands.Command):
    @property
    def signature_without_aliases(self) -> str:
        """Returns a POSIX-like signature useful for help command output."""
        result = []
        parent = self.full_parent_name
        name = self.name if not parent else parent + " " + self.name
        result.append(name)

        if self.usage is not None:
            result.append(self.usage)
            return " ".join(result)

        params = self.clean_params
        if not params:
            return " ".join(result)

        for name, param in params.items():
            if param.default is not param.empty:
                should_print = (
                    param.default
                    if isinstance(param.default, str)
                    else param.default is not None
                )
                if should_print:
                    result.append(f"[{name}={param.default}]")
                else:
                    result.append(f"[{name}]" % name)
            elif param.kind == param.VAR_POSITIONAL:
                result.append(f"[{name}...]")
            else:
                result.append(f"<{name}>")

        return " ".join(result)


class GroupMixin(commands.GroupMixin):
    def command(self, *args, **kwargs):
        """A shortcut decorator that invokes :func:`.command` and adds it to
        the internal command list via :meth:`~.GroupMixin.add_command`.
        """

        def decorator(func):
            result = command(*args, **kwargs)(func)
            self.add_command(result)
            return result

        return decorator

    def group(self, *args, **kwargs):
        """A shortcut decorator that invokes :func:`.group` and adds it to
        the internal command list via :meth:`~.GroupMixin.add_command`.
        """

        def decorator(func):
            result = group(*args, **kwargs)(func)
            self.add_command(result)
            return result

        return decorator


class Group(GroupMixin, Command, commands.Group):
    def __init__(self, **attrs):
        self.invoke_without_command = attrs.pop("invoke_without_command", False)
        super().__init__(**attrs)

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
                await self.callback(  # pylint: disable=not-callable
                    *ctx.args, **ctx.kwargs
                )
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
