import discord
from discord.ext import commands, tasks
from discord.ext.commands import Context
import discord.app_commands as app_commands
from datetime import datetime 
import typing 
import re
import os
from datetime import datetime, timedelta

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
                if channel.id == afk_channel_id:
                    continue

                for member in channel.members:
                    if member.bot:
                        continue

                    if not member.voice.self_mute and not member.voice.self_deaf:
                        try:
                            current_month_year = datetime.now().strftime("%Y-%m")
                            total_minutes = await self.bot.database.upsert_voice_activity(member.id, current_month_year)
                            if total_minutes is not None:
                                self.bot.logger.info(f"Incremented voice time for {member.name} (ID: {member.id}). Total: {total_minutes} min.")
                            else:
                                self.bot.logger.warning(f"Failed to get updated total minutes for {member.name} (ID: {member.id}) after attempting increment.")
                        except Exception as e:
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
            await context.send(embed=embed, ephemeral=True)
            return

        leaderboard_data = []
        title = ""
        is_monthly = False

        try:
            if month is None:
                self.bot.logger.debug("Fetching total voice times for leaderboard.")
                leaderboard_data = await self.bot.database.get_total_voice_times()
                title = "Total Voice Channel Activity Leaderboard"
                is_monthly = False
            else:
                if not re.match(r"^\d{4}-\d{2}$", month):
                     embed = discord.Embed(
                        title="Invalid Format",
                        description="Please use the format YYYY-MM for the month (e.g., 2024-04).",
                        color=0xE02B2B,
                    )
                     await context.send(embed=embed, ephemeral=True)
                     return
                self.bot.logger.debug(f"Fetching voice times for month: {month}")
                leaderboard_data = await self.bot.database.get_monthly_voice_times(month)
                title = f"Voice Channel Activity Leaderboard for {month}"
                is_monthly = True


            if not leaderboard_data:
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
            for i, (user_id_str, minutes) in enumerate(leaderboard_data[:10], 1):
                try:
                    user_id = int(user_id_str)
                    member = context.guild.get_member(user_id) if context.guild else None
                    if member:
                        username = member.display_name # Use display name (nickname if set, else username)
                    else:
                        user = self.bot.get_user(user_id) or await self.bot.fetch_user(user_id)
                        username = user.name if user else f"User ID: {user_id}"
                except (ValueError, discord.NotFound):
                    username = f"Unknown User (ID: {user_id_str})"
                except Exception as fetch_err: 
                    self.bot.logger.warning(f"Could not fetch user {user_id_str} for leaderboard: {fetch_err}")
                    username = f"Unknown User (ID: {user_id_str})"

                leaderboard_text += f"{i}. {username}: {minutes} minute{'s' if minutes != 1 else ''}\n"

            if not leaderboard_text:
                leaderboard_text = f"No voice activity recorded yet{' for ' + month if is_monthly else ''}."

            embed.description = leaderboard_text
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
            await context.send(embed=embed, ephemeral=True) 

    @tasks.loop(hours=24)
    async def monthly_leaderboard_report(self):
        """Sends the previous month's leaderboard on the first day of the month."""
        now = datetime.now()
        if now.day == 1:
            self.bot.logger.info("First day of the month detected, preparing monthly report.")
            first_day_of_current_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            last_day_of_previous_month = first_day_of_current_month - timedelta(days=1)
            previous_month_year = last_day_of_previous_month.strftime("%Y-%m")
            previous_month_readable = last_day_of_previous_month.strftime("%B %Y")
            self.bot.logger.info(f"Generating report for month: {previous_month_year}")
            channel_id_str = os.getenv("MONTHLY_REPORT_CHANNEL_ID")
            if not channel_id_str:
                self.bot.logger.warning("MONTHLY_REPORT_CHANNEL_ID not set in environment variables. Cannot send monthly report.")
                return

            try:
                channel_id = int(channel_id_str)
                target_channel = self.bot.get_channel(channel_id)

                if not target_channel:
                    self.bot.logger.error(f"Could not find channel with ID: {channel_id}. Cannot send monthly report.")
                    return
                if not isinstance(target_channel, discord.TextChannel):
                     self.bot.logger.error(f"Channel with ID: {channel_id} is not a text channel. Cannot send monthly report.")
                     return
                leaderboard_data = await self.bot.database.get_monthly_voice_times(previous_month_year)
                if not leaderboard_data:
                    self.bot.logger.info(f"No voice activity data found for {previous_month_year}. Skipping report.")
                    return

                title = f"🏆 Monthly Voice Recap: {previous_month_readable}"
                embed = await self._generate_leaderboard_embed(leaderboard_data, title, is_monthly=True, requested_by=None) # No requester for automated task
                await target_channel.send("@everyone Here's the voice activity leaderboard for last month!", embed=embed)
                self.bot.logger.info(f"Successfully sent monthly voice report for {previous_month_year} to channel {channel_id}.")

            except ValueError:
                 self.bot.logger.error(f"Invalid MONTHLY_REPORT_CHANNEL_ID: '{channel_id_str}'. Must be an integer.")
            except discord.Forbidden:
                self.bot.logger.error(f"Missing permissions to send message in channel {channel_id}.")
            except Exception as e:
                self.bot.logger.error(f"Error during monthly leaderboard report for {previous_month_year}: {e}", exc_info=True)
        else:
            self.bot.logger.debug(f"Not the first day of the month (Day: {now.day}). Skipping monthly report.")


    @monthly_leaderboard_report.before_loop
    async def before_monthly_report(self):
        """Wait until the bot is ready before starting the loop."""
        await self.bot.wait_until_ready()
        self.bot.logger.info("Bot ready, monthly leaderboard report loop starting.")

async def setup(bot) -> None:
    await bot.add_cog(Activity(bot))
    bot.logger.info("Successfully added the Activity cog.")