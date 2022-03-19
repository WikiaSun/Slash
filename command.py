from typing import TYPE_CHECKING, List, Optional, cast
import inspect

import discord
from discord import app_commands
from discord.app_commands.commands import _shorten
from discord.utils import MISSING
import makefun

if TYPE_CHECKING:
    from .bot import SlashBot
else:
    SlashBot = ...

__all__ = (
    "command",
)
        
def command(
    name: str = MISSING,
    description: str = MISSING,
    guild: Optional[discord.abc.Snowflake] = MISSING,
    guilds: List[discord.abc.Snowflake] = MISSING,
):
    def decorator(func):
        if not inspect.iscoroutinefunction(func):
            raise TypeError('command function must be a coroutine function')

        if description is MISSING:
            if func.__doc__ is None:
                desc = '...'
            else:
                desc = _shorten(func.__doc__)
        else:
            desc = description

        @makefun.wraps(func)
        async def callback(*args, **kwargs):
            interaction: discord.Interaction = kwargs["ctx"]
            bot = cast(SlashBot, interaction.client)

            ctx = bot.get_slash_context(interaction)
            kwargs["ctx"] = ctx
            await func(**kwargs)

        command = app_commands.Command(
            name=name if name is not MISSING else func.__name__,
            description=desc,
            callback=callback,
            parent=None,
        )
        return command

    return decorator
