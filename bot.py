import asyncio
from slash.command import SlashCommand, SlashGroup
import discord
from discord.ext import commands

from .context import SlashContext
from .help import MinimalHelpCommand

class SlashBot(commands.Bot):
    def __init__(self, *,  help_command=MinimalHelpCommand(), guild_ids=[], register_commands_on_startup=True, **kwargs):
        super().__init__(help_command=help_command, **kwargs)
        self.guild_ids = guild_ids

        self.register_commands_on_startup = register_commands_on_startup
        self._commands_registered = False

        if register_commands_on_startup:
            # this is done because bot's application_id is sent only on_ready
            self.add_listener(self.register_commands, "on_ready")

    async def register_all_commands(self):
        if self.guild_ids:
            routes = [
                discord.http.Route(
                    "PUT", 
                    "/applications/{application_id}/guilds/{guild_id}/commands",
                    application_id=self.application_id,
                    guild_id=guild_id
                ) for guild_id in self.guild_ids
            ]
        else:
            routes = [
                discord.http.Route(
                    "PUT", 
                    "/applications/{application_id}/commands",         
                    application_id=self.application_id
                )
            ]

        payload = [
            command.to_json() 
            for command in self.commands 
            if not command.hidden and (isinstance(command, SlashCommand) or isinstance(command, SlashGroup))
        ]
        tasks = [self.http.request(r, json=payload) for r in routes]
        await asyncio.gather(*tasks)

    async def register_guild_commands(self):
        pass
    
    async def register_commands(self):
        """Registers all commands"""
        await self.register_all_commands()
        if not self.guild_ids:
            await self.register_guild_commands()

        if self.register_commands_on_startup and not self._commands_registered:
            # if we're here, this function is called first time
            # to prevent this being called when ready event happens one more time
            # we remove it as a listener
            self._commands_registered = True
            self.remove_listener(self.register_commands, "on_ready")

    async def process_slash_commands(self, interaction: discord.Interaction):
        if interaction.type == discord.InteractionType.application_command:
            cmd = self.all_commands.get(interaction.data["name"])
            ctx = SlashContext(bot=self, interaction=interaction, prefix="/", command=cmd)
            await self.invoke(ctx)

    async def on_interaction(self, interaction: discord.Interaction):
        await self.process_slash_commands(interaction)