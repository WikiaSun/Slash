import discord

class InteractionMessage(discord.InteractionMessage):
    """
    Message that is sent as a response to slash command. It may be is returned from ctx.send function.
    It is just a regular InteractionMessage with __init__  changed to allow constructing this just from Message class 
    instead of raw data given by discord.
    """
    def __init__(self, *, state, message: discord.Message):
        for attr in message.__slots__:
            if not(attr.startswith("_cs")):
                setattr(self, attr, getattr(message, attr))
        self._state = state  