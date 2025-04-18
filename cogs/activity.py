import discord
from discord.ext import commands, tasks
from discord.ext.commands import Context
import discord.app_commands as app_commands
from datetime import datetime # Add datetime import
import typing # Add typing import
import re # Add re import for validation

# Constants
UPDATE_INTERVAL_MINUTES = 1

class Activity(commands.Cog, name="activity"):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.voice_time_tracker.start()
        self.bot.logger.info("Voice time tracking task started.")

    def cog_unload(self) -> None:
        self.voice_time_tracker.cancel()
        self.bot.logger.info("Voice time tracking task stopped.")

    @tasks.loop(minutes=UPDATE_INTERVAL_MINUTES)
    async def voice_time_tracker(self) -> None:
        """
        Tracks active time for users in voice channels every minute.
        """
        if self.bot.database is None:
            self.bot.logger.warning("Database not initialized yet. Skipping voice time tracking cycle.")
            return

        self.bot.logger.debug("Running voice time tracking cycle.")
        for guild in self.bot.guilds:
            afk_channel_id = guild.afk_channel.id if guild.afk_channel else None
            for channel in guild.voice_channels:
                # Skip AFK channel
                if channel.id == afk_channel_id:
                    continue

                for member in channel.members:
                    # Skip bots
                    if member.bot:
                        continue

                    # Check voice state conditions
                    if not member.voice.self_mute and not member.voice.self_deaf:
                        try:
                            # Get current month in YYYY-MM format
                            current_month_year = datetime.now().strftime("%Y-%m")
                            # Call upsert with user ID and current month
                            total_minutes = await self.bot.database.upsert_voice_activity(member.id, current_month_year)
                            # Log success with total minutes if available
                            if total_minutes is not None:
                                # Logging remains focused on total minutes, but monthly is also updated
                                self.bot.logger.info(f"Incremented voice time for {member.name} (ID: {member.id}). Total: {total_minutes} min.")
                            else:
                                # Log if upsert failed (error already logged in DatabaseManager)
                                self.bot.logger.warning(f"Failed to get updated total minutes for {member.name} (ID: {member.id}) after attempting increment.")
                        except Exception as e:
                            # This outer catch is less likely needed now but kept for safety
                            self.bot.logger.error(f"Unexpected error in voice_time_tracker loop for {member.name} (ID: {member.id}): {e}", exc_info=True)

    @voice_time_tracker.before_loop
    async def before_voice_time_tracker(self) -> None:
        """Wait until the bot is ready before starting the loop."""
        await self.bot.wait_until_ready()
        self.bot.logger.info("Bot ready, voice time tracker loop starting.")


    @commands.hybrid_command(
        name="voicetime",
        description="Shows the leaderboard for time spent in voice channels (total or specific month).",
    )
    @app_commands.guilds(discord.Object(id=667561731232497684))
    @app_commands.describe(month="Optional: Month to show leaderboard for (format: YYYY-MM). Defaults to total time.")
    async def voicetime(self, context: Context, month: typing.Optional[str] = None) -> None:
        """
        Displays the voice time leaderboard, either total or for a specific month.

        :param context: The hybrid command context.
        :param month: Optional month in YYYY-MM format.
        """
        if self.bot.database is None:
            embed = discord.Embed(
                title="Error!",
                description="Database connection is not available.",
                color=0xE02B2B,
            )
            await context.send(embed=embed, ephemeral=True) # Make errors ephemeral
            return

        leaderboard_data = []
        title = ""
        is_monthly = False

        try:
            if month is None:
                # Fetch total times when no month is specified
                self.bot.logger.debug("Fetching total voice times for leaderboard.")
                leaderboard_data = await self.bot.database.get_total_voice_times()
                title = "Total Voice Channel Activity Leaderboard"
                is_monthly = False
            else:
                # Validate month format
                if not re.match(r"^\d{4}-\d{2}$", month):
                     embed = discord.Embed(
                        title="Invalid Format",
                        description="Please use the format YYYY-MM for the month (e.g., 2024-04).",
                        color=0xE02B2B,
                    )
                     await context.send(embed=embed, ephemeral=True)
                     return
                # Fetch monthly times when a month is specified
                self.bot.logger.debug(f"Fetching voice times for month: {month}")
                leaderboard_data = await self.bot.database.get_monthly_voice_times(month)
                title = f"Voice Channel Activity Leaderboard for {month}"
                is_monthly = True


            if not leaderboard_data:
                # Use the is_monthly flag correctly determined above
                no_data_message = f"No voice activity recorded yet{' for ' + month if is_monthly else ' overall'}."
                embed = discord.Embed(
                    description=no_data_message,
                    color=0xBEBEFE
                )
                await context.send(embed=embed)
                return

            embed = discord.Embed(
                title=title,
                color=0xBEBEFE,
            )

            leaderboard_text = ""
            # Show top 10 or fewer if less data exists
            for i, (user_id_str, minutes) in enumerate(leaderboard_data[:10], 1):
                try:
                    user_id = int(user_id_str)
                    # Try fetching member from the guild first for nickname/display name
                    member = context.guild.get_member(user_id) if context.guild else None
                    if member:
                        username = member.display_name # Use display name (nickname if set, else username)
                    else:
                        # Fallback to fetching user globally if not in guild or in DMs
                        user = self.bot.get_user(user_id) or await self.bot.fetch_user(user_id)
                        username = user.name if user else f"User ID: {user_id}"
                except (ValueError, discord.NotFound):
                    username = f"Unknown User (ID: {user_id_str})"
                except Exception as fetch_err: # Catch other potential errors during fetch
                    self.bot.logger.warning(f"Could not fetch user {user_id_str} for leaderboard: {fetch_err}")
                    username = f"Unknown User (ID: {user_id_str})"

                leaderboard_text += f"{i}. {username}: {minutes} minute{'s' if minutes != 1 else ''}\n"

            if not leaderboard_text:
                leaderboard_text = f"No voice activity recorded yet{' for ' + month if is_monthly else ''}."

            embed.description = leaderboard_text
            # Add the recording start date note only for the total leaderboard
            footer_text = f"Requested by {context.author}"
            if not is_monthly:
                footer_text += " | Data recording started April 18, 2025"
            embed.set_footer(text=footer_text)
            await context.send(embed=embed)

        except Exception as e:
            self.bot.logger.error(f"Error fetching/displaying voice times (Month: {month}): {e}", exc_info=True)
            embed = discord.Embed(
                title="Error!",
                description="Could not retrieve voice time leaderboard.",
                color=0xE02B2B,
            )
            await context.send(embed=embed, ephemeral=True) # Make errors ephemeral


async def setup(bot) -> None:
    await bot.add_cog(Activity(bot))
    # Add a log message to confirm the cog was added successfully
    bot.logger.info("Successfully added the Activity cog.")