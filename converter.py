from discord.ext import commands

class AutocompleteConverter(commands.Converter):
    async def get_suggestions(self, ctx, argument):
        """|coro|

        The method to override to get option suggestions when the user starts filling in param with autocomplete.

        Parameters
        -----------
        ctx: :class:`.Context`
            The invocation context that the argument is being used in.
        argument: :class:`str`
            The argument that the suggestions are being queried for.

        Raises
        -------
        :exc:`.CommandError`
            A generic exception occurred when converting the argument.
        :exc:`.BadArgument`
            The converter failed to convert the argument.
        """
        raise NotImplementedError("Derived classes need to implement this.")