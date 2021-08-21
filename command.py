from dataclasses import dataclass
from collections import defaultdict
import discord
from discord.ext import commands

from .enums import ApplicationCommandOptionType
from .context import SlashContext

__all__ = (
    "SlashCommand",
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
    name: str = ...
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

        for arg in data.get("options", []):
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
                value = discord.Member(data=member_data, state=ctx.bot._connection, guild=ctx.interaction.guild)
            elif arg["type"] == ApplicationCommandOptionType.role.value:
                role_data = data["resolved"]["roles"][arg["value"]]
                value = discord.Role(data=role_data, state=ctx.bot._connection, guild=ctx.interaction.guild)
                
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
        print(ctx.view)
        await super()._parse_arguments(ctx)

        # after parsing is done, we need to pass default values
        # this might be a problem as all arguments have instance of Option as a default value
        # so here we transform these into real default values
        for idx, arg in enumerate(ctx.args):
            if isinstance(arg, Option):
                print("argument: " + str(arg))
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
                
                    
    def to_json(self):
        data = {
            "name": self.name,
            "description": self.short_doc,
            "type": 1
        }
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
