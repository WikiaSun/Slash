from dataclasses import dataclass
from collections import defaultdict
from typing import Union
import discord
from discord.ext import commands

from .enums import ApplicationCommandOptionType, ApplicationCommandType
from .context import SlashContext

__all__ = (
    "command",
    "group",
    "SlashCommand",
    "SlashGroup",
    "Option"
)

ARGUMENT_TYPES = defaultdict(lambda: ApplicationCommandOptionType.string)
ARGUMENT_TYPES.update({
    int: ApplicationCommandOptionType.integer,
    float: ApplicationCommandOptionType.number,
    bool: ApplicationCommandOptionType.boolean,
    discord.Member: ApplicationCommandOptionType.user,
    discord.TextChannel: ApplicationCommandOptionType.channel,
    discord.VoiceChannel: ApplicationCommandOptionType.channel,
    discord.CategoryChannel: ApplicationCommandOptionType.channel,
    discord.Role: ApplicationCommandOptionType.role
})

@dataclass
class Option:
    name: str = None
    description: str = None
    default: str = ...

    @property
    def required(self):
        return self.default is ...

    @classmethod
    async def convert(cls, ctx, arg):
        # when we declare Option as a default value, discord.py treats it as a converter
        # so we need to implement conversion logic
        # since we haven't to do anything special with the argument
        # we just return it unchanged
        return arg

class SlashCommand(commands.Command):
    def _get_args_iterator(self):
        iterator = iter(self.params.items())
        
        if self.cog is not None:
            try:
                next(iterator)
            except StopIteration:
                raise discord.ClientException(f'Callback for {self.name} command is missing "self" parameter.')

        try:
            next(iterator)
        except StopIteration:
            raise discord.ClientException(f'Callback for {self.name} command is missing "ctx" parameter.')

        return iterator

    async def _parse_slash_arguments(self, ctx):
        args = [ctx] if self.cog is None else [self.cog, ctx]
        kwargs = {}
        data = ctx.interaction.data

        iterator = self._get_args_iterator()
        options = ctx.options if ctx.options is not None else data.get("options", [])

        for arg in options:
            if arg["type"] in (
                ApplicationCommandOptionType.string.value,
                ApplicationCommandOptionType.integer.value,
                ApplicationCommandOptionType.number.value,
                ApplicationCommandOptionType.boolean.value
            ):
                value = arg["value"]
            elif arg["type"] == ApplicationCommandOptionType.user.value:
                member_data = data["resolved"]["members"][arg["value"]]
                member_data["user"] = data["resolved"]["users"][arg["value"]]
                value = discord.Member(data=member_data, state=ctx._state, guild=ctx.interaction.guild)
            elif arg["type"] == ApplicationCommandOptionType.role.value:
                role_data = data["resolved"]["roles"][arg["value"]]
                value = discord.Role(data=role_data, state=ctx._state, guild=ctx.interaction.guild)
                
            kwargs[arg["name"]] = value
        
        # now we need to pass default values to all optional arguments
        # otherwise, an instance of Option will get passed instead
        for name, param in iterator:
            if name not in kwargs:
                kwargs[name] = param.default.default

        ctx.args = args
        ctx.kwargs = kwargs

    async def _parse_arguments(self, ctx):
        if isinstance(ctx, SlashContext):
            # command is being invoked as slash command
            return await self._parse_slash_arguments(ctx)

        # command is being invoked as text command
        await super()._parse_arguments(ctx)

        # after parsing is done, we need to pass default values
        # this might be a problem as all arguments have instance of Option as a default value
        # so here we transform these into real default values
        for idx, arg in enumerate(ctx.args):
            if isinstance(arg, Option):
                if arg.default is ...:
                    param = list(self.params.values())[idx]
                    raise commands.MissingRequiredArgument(param)
                else:
                    ctx.args[idx] = arg.default

        for name, value in ctx.kwargs.items():
            if isinstance(value, Option):
                if value.default is ...:
                    raise commands.MissingRequiredArgument(self.params[name])
                else:
                    ctx.kwargs[name] = value.default
                
    @property
    def signature(self) -> str:
        if self.usage is not None:
            return self.usage

        params = self.clean_params
        if not params:
            return ''

        result = []
        for name, param in params.items():
            greedy = isinstance(param.annotation, commands.Greedy)
            optional = False 

            annotation = param.annotation.converter if greedy else param.annotation
            origin = getattr(annotation, '__origin__', None)
            if not greedy and origin is Union:
                none_cls = type(None)
                union_args = annotation.__args__
                optional = union_args[-1] is none_cls
                if len(union_args) == 2 and optional:
                    annotation = union_args[0]
                    origin = getattr(annotation, '__origin__', None)

            # we don't handle literals for slash commands
            assert isinstance(param.default, Option)
            if (default := param.default.default) is not ...:
                should_print = default if isinstance(default, str) else default is not None
                if should_print:
                    result.append(f'[{name}={default}]' if not greedy else
                                  f'[{name}={default}]...')
                    continue
                else:
                    result.append(f'[{name}]')

            elif param.kind == param.VAR_POSITIONAL:
                if self.require_var_positional:
                    result.append(f'<{name}...>')
                else:
                    result.append(f'[{name}...]')
            elif greedy:
                result.append(f'[{name}]...')
            elif optional:
                result.append(f'[{name}]')
            else:
                result.append(f'<{name}>')

        return ' '.join(result)

    def to_json(self):
        data = {
            "name": self.name,
            "description": self.short_doc,
        }

        if len(self.parents) == 0:
            # this is a top-level command
            data["type"] = ApplicationCommandType.chat_input.value
        elif len(self.parents) <= 2:
            # this is a subcommand
            data["type"] = ApplicationCommandOptionType.subcommand

        options = []
        iterator = self._get_args_iterator()

        for name, param in iterator:

            option = {
                "name": param.default.name or name,
                "type": ARGUMENT_TYPES[param.annotation].value,
                "description": param.default.description,
                "required": param.default.required
            }
            options.append(option)

        data["options"] = options
        return data

class SlashGroup(commands.Group):
    async def _parse_arguments(self, ctx):
        if not isinstance(ctx, SlashContext):
            return await super()._parse_arguments(ctx)
        
        ctx.args = [ctx] if self.cog is None else [self.cog, ctx]
        ctx.kwargs = {}

    async def invoke(self, ctx):
        if not isinstance(ctx, SlashContext):
            return await super().invoke(ctx)
        
        options = ctx.options if ctx.options is not None else ctx.interaction.data.get("options", [])
        ctx.subcommand_passed = options[0]["name"]
        ctx.invoked_subcommand = self.all_commands.get(ctx.subcommand_passed)

        if not self.invoke_without_command:
            await self.prepare(ctx)
            injected = commands.core.hooked_wrapped_callback(self, ctx, self.callback)
            await injected(*ctx.args, **ctx.kwargs)
        
        ctx.invoked_parents.append(ctx.invoked_with)

        ctx.options = options[0].get("options", [])
        await ctx.invoked_subcommand.invoke(ctx)

    def to_json(self):
        data = {
            "name": self.name,
            "description": self.short_doc
        }
        if len(self.parents) == 0:
            # this is a top-level group
            data["type"] = ApplicationCommandType.chat_input.value
        if len(self.parents) == 1:
            # this is a group that is nested inside the other group
            data["type"] = ApplicationCommandOptionType.subcommand_group.value
        else:
            raise commands.CommandError("Maximum group depth exceeded")

        data["options"] = [cmd.to_json() for cmd in self.commands]
        return data
        
def command(
    name = discord.utils.MISSING,
    cls = SlashCommand,
    **attrs
):
    return commands.command(name, cls, **attrs)


def group(
    name = discord.utils.MISSING,
    cls = SlashGroup,
    **attrs
):
    return commands.group(name, cls, **attrs)