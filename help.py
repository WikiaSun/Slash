import discord
from discord.ext import commands
from .command import Option, SlashCommand

__all__ = (
    "SlashHelpCommand",
    "DefaultHelpCommand",
    "MinimalHelpCommand"
)

class _HelpCommandImpl(commands.help._HelpCommandImpl, SlashCommand):
    pass

class SlashHelpCommand(commands.HelpCommand):
    def __init__(self, **options):
        super().__init__(**options)
        self._command_impl = _HelpCommandImpl(self, **self.command_attrs)

    def _add_to_bot(self, bot):
        command = _HelpCommandImpl(self, **self.command_attrs)
        bot.add_command(command)
        self._command_impl = command

    def get_destination(self):
        return self.context

    async def command_callback(self, ctx, *, command = Option(description="A command or a cog to show help for", default=None)):
        await super().command_callback(ctx, command=command)

class DefaultHelpCommand(SlashHelpCommand, commands.DefaultHelpCommand):
    pass

class MinimalHelpCommand(SlashHelpCommand, commands.MinimalHelpCommand):
    pass