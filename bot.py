from typing import List, Optional, Type
import discord
from discord.ext import commands
from discord.utils import MISSING

from .context import InteractionContext
# from .help import MinimalHelpCommand

class SlashBot(commands.Bot):
    def __init__(self, *,  guild_ids: List[int] = [], sync_commands_on_startup: bool = True, **kwargs):
        super().__init__(**kwargs)
        self.guild_ids = guild_ids

        self.sync_commands_on_startup = sync_commands_on_startup
        self._commands_registered = False

        if sync_commands_on_startup:
            # this is done because bot's application_id is sent only on_ready
            self.add_listener(self.sync_commands, "on_ready")
    
    async def sync_commands(self):
        """Registers all commands"""
        if self.guild_ids:
            for guild in self.guild_ids:
                await self.tree.sync(guild=discord.Object(guild))
        else:
            await self.tree.sync()

        if self.sync_commands_on_startup and not self._commands_registered:
            # if we're here, this function is called first time
            # to prevent this being called when ready event happens one more time
            # we remove it as a listener
            self._commands_registered = True
            self.remove_listener(self.sync_commands, "on_ready")

    async def add_cog(
        self, 
        cog: commands.Cog, 
        /, *, 
        override: bool = False, 
        guild: Optional[discord.abc.Snowflake] = MISSING, 
        guilds: List[discord.abc.Snowflake] = MISSING
    ) -> None:
        print("add cog " + repr(cog))
        if self.guild_ids:
            guild = MISSING
            guilds = [discord.Object(g) for g in self.guild_ids]

        return await super().add_cog(cog, override=override, guild=guild, guilds=guilds)
    
    def get_slash_context(self, interaction: discord.Interaction, *, cls: Type[InteractionContext] = InteractionContext):
        return cls(
            bot=self, 
            interaction=interaction
        )
