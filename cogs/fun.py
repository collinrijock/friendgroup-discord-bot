"""
Copyright © Krypton 2019-Present - https://github.com/kkrypt0nn (https://krypton.ninja)
Description:
🐍 A simple template to start to code your own and personalized Discord bot in Python

Version: 6.3.0
"""

import random
import csv # Add csv import
import os # Add os import
import discord.app_commands as app_commands

import aiohttp
import discord
from discord.ext import commands
from discord.ext.commands import Context


class Choice(discord.ui.View):
    def __init__(self) -> None:
        super().__init__()
        self.value = None

    @discord.ui.button(label="Heads", style=discord.ButtonStyle.blurple)
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.value = "heads"
        self.stop()

    @discord.ui.button(label="Tails", style=discord.ButtonStyle.blurple)
    async def cancel(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.value = "tails"
        self.stop()


class RockPaperScissors(discord.ui.Select):
    def __init__(self) -> None:
        options = [
            discord.SelectOption(
                label="Scissors", description="You choose scissors.", emoji="✂"
            ),
            discord.SelectOption(
                label="Rock", description="You choose rock.", emoji="🪨"
            ),
            discord.SelectOption(
                label="Paper", description="You choose paper.", emoji="🧻"
            ),
        ]
        super().__init__(
            placeholder="Choose...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        choices = {
            "rock": 0,
            "paper": 1,
            "scissors": 2,
        }
        user_choice = self.values[0].lower()
        user_choice_index = choices[user_choice]

        bot_choice = random.choice(list(choices.keys()))
        bot_choice_index = choices[bot_choice]

        result_embed = discord.Embed(color=0xBEBEFE)
        result_embed.set_author(
            name=interaction.user.name, icon_url=interaction.user.display_avatar.url
        )

        winner = (3 + user_choice_index - bot_choice_index) % 3
        if winner == 0:
            result_embed.description = f"**That's a draw!**\nYou've chosen {user_choice} and I've chosen {bot_choice}."
            result_embed.colour = 0xF59E42
        elif winner == 1:
            result_embed.description = f"**You won!**\nYou've chosen {user_choice} and I've chosen {bot_choice}."
            result_embed.colour = 0x57F287
        else:
            result_embed.description = f"**You lost!**\nYou've chosen {user_choice} and I've chosen {bot_choice}."
            result_embed.colour = 0xE02B2B

        await interaction.response.edit_message(
            embed=result_embed, content=None, view=None
        )


class RockPaperScissorsView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__()
        self.add_item(RockPaperScissors())


class Fun(commands.Cog, name="fun"):
    def __init__(self, bot) -> None:
        self.bot = bot

    @commands.hybrid_command(name="randomfact", description="Get a random fact.")
    async def randomfact(self, context: Context) -> None:
        """
        Get a random fact.

        :param context: The hybrid command context.
        """
        # This will prevent your bot from stopping everything when doing a web request - see: https://discordpy.readthedocs.io/en/stable/faq.html#how-do-i-make-a-web-request
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://uselessfacts.jsph.pl/random.json?language=en"
            ) as request:
                if request.status == 200:
                    data = await request.json()
                    embed = discord.Embed(description=data["text"], color=0xD75BF4)
                else:
                    embed = discord.Embed(
                        title="Error!",
                        description="There is something wrong with the API, please try again later",
                        color=0xE02B2B,
                    )
                await context.send(embed=embed)

    @commands.hybrid_command(
        name="coinflip", description="Make a coin flip, but give your bet before."
    )
    async def coinflip(self, context: Context) -> None:
        """
        Make a coin flip, but give your bet before.

        :param context: The hybrid command context.
        """
        buttons = Choice()
        embed = discord.Embed(description="What is your bet?", color=0xBEBEFE)
        message = await context.send(embed=embed, view=buttons)
        await buttons.wait()  # We wait for the user to click a button.
        result = random.choice(["heads", "tails"])
        if buttons.value == result:
            embed = discord.Embed(
                description=f"Correct! You guessed `{buttons.value}` and I flipped the coin to `{result}`.",
                color=0xBEBEFE,
            )
        else:
            embed = discord.Embed(
                description=f"Woops! You guessed `{buttons.value}` and I flipped the coin to `{result}`, better luck next time!",
                color=0xE02B2B,
            )
        await message.edit(embed=embed, view=None, content=None)

    @commands.hybrid_command(
        name="rps", description="Play the rock paper scissors game against the bot."
    )
    async def rock_paper_scissors(self, context: Context) -> None:
        """
        Play the rock paper scissors game against the bot.

        :param context: The hybrid command context.
        """
        view = RockPaperScissorsView()
        await context.send("Please make your choice", view=view)

    @commands.hybrid_command(
        name="tippytap",
        description="Does a little tippy tap.",
    )
    async def tippytap(self, context: Context) -> None:
        """
        Does a little tippy tap.

        :param context: The hybrid command context.
        """
        await context.send("*Does a tippy tap aggressively*")

    @commands.hybrid_command(
        name="addstatus",
        description="Adds a new status/meme to the bot's rotation.",
    )
    @commands.cooldown(1, 5, commands.BucketType.user) # Add a cooldown to prevent spam
    @app_commands.guilds(discord.Object(id=667561731232497684))
    async def addstatus(self, context: Context, *, status_text: str) -> None:
        """
        Adds a new status text to the statuses.csv file.

        :param context: The hybrid command context.
        :param status_text: The text of the status to add.
        """
        status_file_path = f"{os.path.realpath(os.path.dirname(__file__))}/../statuses.csv" # Navigate up one directory

        # Basic validation
        if not status_text:
            embed = discord.Embed(
                title="Error!",
                description="Status text cannot be empty.",
                color=0xE02B2B,
            )
            await context.send(embed=embed, ephemeral=True)
            return

        if len(status_text) > 100: # Discord status limit is 128, add some buffer
             embed = discord.Embed(
                title="Error!",
                description="Status text is too long (max 100 characters).",
                color=0xE02B2B,
            )
             await context.send(embed=embed, ephemeral=True)
             return

        try:
            # Check if status already exists (case-insensitive)
            existing_statuses = []
            try:
                with open(status_file_path, mode='r', encoding='utf-8', newline='') as file:
                    reader = csv.reader(file)
                    existing_statuses = [row[0].lower() for row in reader if row]
            except FileNotFoundError:
                self.bot.logger.warning(f"statuses.csv not found when checking for duplicates in addstatus. Will create if needed.")
                # File doesn't exist, so the status can't exist yet. Continue.
            except Exception as e:
                 self.bot.logger.error(f"Error reading statuses.csv during duplicate check: {e}", exc_info=True)
                 # Proceed cautiously, might add a duplicate if read failed
                 pass # Allow adding even if check fails, but log it

            if status_text.lower() in existing_statuses:
                embed = discord.Embed(
                    title="Already Exists",
                    description=f"The status \"{status_text}\" is already in the list.",
                    color=0xF59E42, # Orange color for warning
                )
                await context.send(embed=embed, ephemeral=True)
                return

            # Append the new status
            with open(status_file_path, mode='a', encoding='utf-8', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([status_text])

            self.bot.logger.info(f"User {context.author} (ID: {context.author.id}) added status: '{status_text}'")
            embed = discord.Embed(
                title="Status Added!",
                description=f"Successfully added \"{status_text}\" to the status list.",
                color=0x57F287, # Green color for success
            )
            await context.send(embed=embed)

        except FileNotFoundError:
            self.bot.logger.error(f"statuses.csv not found at {status_file_path} when trying to add status.")
            embed = discord.Embed(
                title="Error!",
                description="Could not find the status file. Please contact the bot owner.",
                color=0xE02B2B,
            )
            await context.send(embed=embed, ephemeral=True)
        except PermissionError:
             self.bot.logger.error(f"Permission denied when trying to write to {status_file_path}.")
             embed = discord.Embed(
                title="Error!",
                description="Bot doesn't have permission to write to the status file. Please contact the bot owner.",
                color=0xE02B2B,
            )
             await context.send(embed=embed, ephemeral=True)
        except Exception as e:
            self.bot.logger.error(f"An unexpected error occurred while adding status: {e}", exc_info=True)
            embed = discord.Embed(
                title="Error!",
                description="An unexpected error occurred. Please try again later.",
                color=0xE02B2B,
            )
            await context.send(embed=embed, ephemeral=True)

    @commands.hybrid_command(
        name="randommemes",
        description="Gets a list of 10 random memes/statuses from the bot's list.",
    )
    async def randommemes(self, context: Context) -> None:
        """
        Sends a list of 10 random statuses from the statuses.csv file.

        :param context: The hybrid command context.
        """
        status_file_path = f"{os.path.realpath(os.path.dirname(__file__))}/../statuses.csv"
        statuses = []

        try:
            with open(status_file_path, mode='r', encoding='utf-8', newline='') as file:
                reader = csv.reader(file)
                statuses = [row[0] for row in reader if row] # Read all non-empty rows

            if not statuses:
                embed = discord.Embed(
                    title="No Memes Found!",
                    description="The status list is currently empty.",
                    color=0xE02B2B,
                )
                await context.send(embed=embed)
                return

            # Determine how many memes to sample (max 10 or total count if less than 10)
            sample_count = min(len(statuses), 10)
            random_memes = random.sample(statuses, sample_count)

            # Format the list for the embed
            meme_list_str = "\n".join(f"{i+1}. {meme}" for i, meme in enumerate(random_memes))

            embed = discord.Embed(
                title=f"Here are {sample_count} random memes:",
                description=meme_list_str,
                color=0xBEBEFE, # Use a standard color
            )
            await context.send(embed=embed)

        except FileNotFoundError:
            self.bot.logger.error(f"statuses.csv not found at {status_file_path} when trying to get random memes.")
            embed = discord.Embed(
                title="Error!",
                description="Could not find the status file. Please contact the bot owner.",
                color=0xE02B2B,
            )
            await context.send(embed=embed, ephemeral=True)
        except Exception as e:
            self.bot.logger.error(f"An unexpected error occurred while getting random memes: {e}", exc_info=True)
            embed = discord.Embed(
                title="Error!",
                description="An unexpected error occurred. Please try again later.",
                color=0xE02B2B,
            )
            await context.send(embed=embed, ephemeral=True)


async def setup(bot) -> None:
    await bot.add_cog(Fun(bot))