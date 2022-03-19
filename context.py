import asyncio
from typing import TYPE_CHECKING, Optional, Union, Protocol

import discord
from discord.utils import MISSING
from discord.ext import commands

from .message import InteractionMessage

class ContextBase(Protocol):
    bot: "commands.Bot"
    guild: Optional[discord.Guild]
    channel: discord.abc.Messageable
    author: Union[discord.User, discord.Member]
    me: Union[discord.Member, discord.ClientUser]

    message: Optional[discord.Message]
    interaction: Optional[discord.Interaction]
  
    async def send(self, content, *, ephemeral=False, **kwargs) -> Union[discord.Message, InteractionMessage]:
        ...

    async def defer(self):
        ...


class MessageContext(ContextBase):
    def __init__(self, message: discord.Message, bot: "commands.Bot"):
        self.message: discord.Message = message
        self.bot = bot
        self.interaction = None
        self.responded = asyncio.Event()

    @property
    def guild(self):
        return self.message.guild

    @property
    def channel(self):
        return self.message.channel

    @property
    def author(self):
        return self.message.author

    @property
    def me(self):
        return self.guild.me if self.guild is not None else self.bot.user

    async def send(self, *args, ephemeral=False, **kwargs):
        self.responded.set()
        return await super().send(*args, **kwargs)

    async def type_until_response(self):
        async with self.channel.typing():
            await self.responded.wait()

    async def defer(self, ephemeral=False):
        asyncio.create_task(self.type_until_response())


class InteractionContext(ContextBase):
    def __init__(self, interaction: discord.Interaction, bot: "commands.Bot"):
        self.message = None
        self.bot = bot
        self.interaction: discord.Interaction = interaction

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
    def me(self):
        return self.guild.me if self.guild is not None else self.bot.user

    @property
    def response(self):
        return self.interaction.response

    async def defer(self, ephemeral=False):
        await self.interaction.response.defer(ephemeral=ephemeral)

    async def send(self, content = MISSING, **kwargs):
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
        state = discord.interactions._InteractionMessageState(self.interaction, self.interaction._state)
        msg = InteractionMessage(state=state, message=msg)
        return msg
    