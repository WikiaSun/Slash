import asyncio
import discord
from discord.ext import commands
from contextlib import suppress

from .message import InteractionMessage

class SlashContext(commands.Context):
    def __init__(self, **attrs):
        with suppress(AttributeError): # a weird hack to bypass the lack of state
            super().__init__(**attrs)
        self._state = self.bot._connection
        self.interaction: discord.Interaction = attrs.pop("interaction")
        self.options = None

    @property
    def guild(self):
        return self.interaction.guild

    @property
    def channel(self):
        return self.interaction.channel

    @property
    def author(self):
        return self.interaction.user

    @property
    def response(self):
        return self.interaction.response

    async def send(self, content=None, **kwargs):
        if self.interaction.response.is_done():
            return await self.interaction.followup.send(content, **kwargs)

        task = asyncio.create_task(
            self.bot.wait_for(
                "message", 
                check=lambda m: m.channel == self.channel and m.author == self.me
            )
        )
        await self.response.send_message(content, **kwargs)
        msg = await task
        state = discord.interactions._InteractionMessageState(self.interaction, self.bot._connection)
        msg = InteractionMessage(state=state, message=msg)
        return msg