import asyncio

import discord
from discord.ext import commands
import voxelbotutils as utils

from cogs import utils as localutils


class CurrencyCommands(utils.Cog):

    MAX_GUILD_CURRENCIES = 3

    @utils.command()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    @commands.guild_only()
    async def coins(self, ctx: utils.Context, user: discord.Member = None):
        """
        Shows you how many coins you have.
        """

        user = user or ctx.author
        async with self.bot.database() as db:
            rows = await db(
                """SELECT guild_currencies.currency_name, um.money_amount FROM guild_currencies LEFT OUTER JOIN
                (SELECT * FROM user_money WHERE user_money.guild_id=$1 AND user_money.user_id=$2) AS um ON
                guild_currencies.currency_name=um.currency_name WHERE guild_currencies.guild_id=$1""",
                ctx.guild.id, user.id,
            )
        embed = utils.Embed(use_random_colour=True)
        for row in rows:
            name = row['currency_name']
            embed.add_field(name.title() if name.islower() else name, format(row['money_amount'] or 0, ","))
        await ctx.send(embed=embed)

    @utils.group(aliases=['currencies'], invoke_without_command=False)
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    @commands.guild_only()
    async def currency(self, ctx: utils.Context):
        """
        The parent command to set up the currencies on your guild.
        """

        if ctx.invoked_subcommand is not None:
            return
        async with self.bot.database() as db:
            currency_rows = await db("""SELECT * FROM guild_currencies WHERE guild_id=$1 ORDER BY UPPER(currency_name) ASC""", ctx.guild.id)
        if not currency_rows:
            return await ctx.send(f"There are no currencies set up for this guild! Use the `{ctx.clean_prefix}currency create` command to add a new one.")
        embed = utils.Embed(colour=0x1)
        embed.set_footer(f"Add new currencies with \"{ctx.clean_prefix}currency create\"")
        currencies = []
        for row in currency_rows:
            name = row['currency_name']
            currencies.append(f"* {name.title() if name.islower() else name}")
        embed.description = "\n".join(currencies)
        return await ctx.send(embed=embed)

    @currency.command(name="create", aliases=['make', 'new'])
    @commands.has_guild_permissions(manage_guild=True)
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
    async def currency_create(self, ctx: utils.Context):
        """
        Add a new currency to your guild.
        """

        # Make sure they only have 3 currencies already
        async with self.bot.database() as db:
            currency_rows = await db("""SELECT * FROM guild_currencies WHERE guild_id=$1""", ctx.guild.id)
        if len(currency_rows) >= self.MAX_GUILD_CURRENCIES:
            return await ctx.send(f"You can only have **{self.MAX_GUILD_CURRENCIES}** currencies per guild.")

        # Set up the wait_for check here because we're gonna use it multiple times
        def check(message):
            return all([
                message.channel.id == ctx.channel.id,
                message.author.id == ctx.author.id,
            ])

        # Ask what they want the name of the currency to be
        await ctx.send("""What do you want the _name_ of the currency to be? Examples: "dollars", "pounds", "krona", etc.""")
        for _ in range(3):
            try:
                currency_name_message = await self.bot.wait_for("message", check=check, timeout=60)
                assert currency_name_message.content
            except asyncio.TimeoutError:
                return await ctx.send("Timed out on adding a new currency to the guild.", ignore_error=True)
            except AssertionError:
                await currency_name_message.reply("This isn't a valid currency name - please provide another one.")
                continue

            # Check that their provided name is valid
            async with self.bot.database() as db:
                check_rows = await db(
                    """SELECT * FROM guild_currencies WHERE guild_id=$1 AND LOWER(currency_name)=LOWER($2)""",
                    ctx.guild.id, currency_name_message.content,
                )
            if check_rows:
                await currency_name_message.reply(
                    f"You're already using a currency with the name **{currency_name_message.content}** - please provide another one.",
                    allowed_mentions=discord.AllowedMentions.none(),
                )
                continue
            break
        else:
            return await ctx.send("You failed giving a valid currency name too many times - please try again later.")

        # Ask what they want the short form of the currency to be
        await ctx.send("""What do you want the _short form_ of the currency to be? Examples: "USD", "GBP", "RS3", etc.""")
        for _ in range(3):
            try:
                currency_short_message = await self.bot.wait_for("message", check=check, timeout=60)
                assert currency_short_message.content
                break
            except asyncio.TimeoutError:
                return await ctx.send("Timed out on adding a new currency to the guild.", ignore_error=True)
            except AssertionError:
                await currency_short_message.reply("This isn't a valid currency name - please provide another one.")

            # Check that their provided name is valid
            async with self.bot.database() as db:
                check_rows = await db(
                    """SELECT * FROM guild_currencies WHERE guild_id=$1 AND LOWER(short_form)=LOWER($2)""",
                    ctx.guild.id, currency_short_message.content,
                )
            if check_rows:
                await currency_name_message.reply(
                    f"You're already using a currency with the short name **{currency_name_message.content}** - please provide another one.",
                    allowed_mentions=discord.AllowedMentions.none(),
                )
                continue
            break
        else:
            return await ctx.send("You failed giving a valid currency short name too many times - please try again later.")

        # # Ask how much debt the user can go into
        # await ctx.send("""How much debt do you want users to be able to go into with this currency? Use "0" for no debt, or a number for any amount.""")
        # for _ in range(3):
        #     try:
        #         currency_debt_message = await self.bot.wait_for("message", check=check, timeout=60)
        #         assert currency_debt_message.content
        #         int(currency_debt_message.content)
        #         assert int(currency_debt_message.content) >= 0
        #         break
        #     except asyncio.TimeoutError:
        #         return await ctx.send("Timed out on adding a new currency to the guild.", ignore_error=True)
        #     except (AssertionError, ValueError):
        #         await currency_debt_message.reply("This isn't a valid number - please provide another one.")
        # else:
        #     return await ctx.send("You failed giving a valid currency debt amount too many times - please try again later.")

        # Ask if we should add a daily command
        await ctx.send("""Do you want there to be a "daily" command available for this currency, where users can get between 9k and 13k every day?""")
        for _ in range(3):
            try:
                currency_debt_message = await self.bot.wait_for("message", check=check, timeout=60)
                assert currency_debt_message.content
                int(currency_debt_message.content)
                assert int(currency_debt_message.content) >= 0
                break
            except asyncio.TimeoutError:
                return await ctx.send("Timed out on adding a new currency to the guild.", ignore_error=True)
            except (AssertionError, ValueError):
                await currency_debt_message.reply("This isn't a valid number - please provide another one.")
        else:
            return await ctx.send("You failed giving a valid currency debt amount too many times - please try again later.")

        # Add the new currency to the server
        async with ctx.typing():
            async with self.bot.database() as db:
                await db(
                    """INSERT INTO guild_currencies (guild_id, currency_name, short_form, negative_amount_allowed)
                    VALUES ($1, $2, $3, $4)""",
                    ctx.guild.id, currency_name_message.content, currency_short_message.content, 0,
                )
        return await ctx.send("Added a new currency to your server!")

    @currency.command(name="add")
    @commands.has_guild_permissions(manage_guild=True)
    @commands.bot_has_permissions(add_reactions=True)
    @commands.guild_only()
    async def currency_add(self, ctx: utils.Context, user: discord.Member, *, amount: localutils.CurrencyAmount):
        """
        Give some currency to a user.
        """

        async with self.bot.database() as db:
            await db(
                """INSERT INTO user_money (user_id, guild_id, currency_name, money_amount) VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id, guild_id, currency_name) DO UPDATE SET
                money_amount=user_money.money_amount+excluded.money_amount""",
                user.id, ctx.guild.id, amount.currency, amount.amount,
            )
        await ctx.okay()

    @currency.command(name="remove")
    @commands.has_guild_permissions(manage_guild=True)
    @commands.bot_has_permissions(add_reactions=True)
    @commands.guild_only()
    async def currency_remove(self, ctx: utils.Context, user: discord.Member, *, amount: localutils.CurrencyAmount):
        """
        Remove some currency from a user.
        """

        async with self.bot.database() as db:
            await db(
                """INSERT INTO user_money (user_id, guild_id, currency_name, money_amount) VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id, guild_id, currency_name) DO UPDATE SET
                money_amount=user_money.money_amount+excluded.money_amount""",
                user.id, ctx.guild.id, amount.currency, -amount.amount,
            )
        await ctx.okay()


def setup(bot: utils.Bot):
    x = CurrencyCommands(bot)
    bot.add_cog(x)
