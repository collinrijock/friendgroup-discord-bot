"""
Copyright © Krypton 2019-Present - https://github.com/kkrypt0nn (https://krypton.ninja)
Description:
🐍 A simple template to start to code your own and personalized Discord bot in Python

Version: 6.3.0
"""

import aiosqlite
import logging # Add logging import


class DatabaseManager:
    def __init__(self, *, connection: aiosqlite.Connection, logger: logging.Logger) -> None: # Add logger parameter
        self.connection = connection
        self.logger = logger # Store the logger instance

    async def add_warn(
        self, user_id: int, server_id: int, moderator_id: int, reason: str
    ) -> int:
        """
        This function will add a warn to the database.

        :param user_id: The ID of the user that should be warned.
        :param reason: The reason why the user should be warned.
        """
        rows = await self.connection.execute(
            "SELECT id FROM warns WHERE user_id=? AND server_id=? ORDER BY id DESC LIMIT 1",
            (
                user_id,
                server_id,
            ),
        )
        async with rows as cursor:
            result = await cursor.fetchone()
            warn_id = result[0] + 1 if result is not None else 1
            await self.connection.execute(
                "INSERT INTO warns(id, user_id, server_id, moderator_id, reason) VALUES (?, ?, ?, ?, ?)",
                (
                    warn_id,
                    user_id,
                    server_id,
                    moderator_id,
                    reason,
                ),
            )
            await self.connection.commit()
            return warn_id

    async def remove_warn(self, warn_id: int, user_id: int, server_id: int) -> int:
        """
        This function will remove a warn from the database.

        :param warn_id: The ID of the warn.
        :param user_id: The ID of the user that was warned.
        :param server_id: The ID of the server where the user has been warned
        """
        await self.connection.execute(
            "DELETE FROM warns WHERE id=? AND user_id=? AND server_id=?",
            (
                warn_id,
                user_id,
                server_id,
            ),
        )
        await self.connection.commit()
        rows = await self.connection.execute(
            "SELECT COUNT(*) FROM warns WHERE user_id=? AND server_id=?",
            (
                user_id,
                server_id,
            ),
        )
        async with rows as cursor:
            result = await cursor.fetchone()
            return result[0] if result is not None else 0

    async def get_warnings(self, user_id: int, server_id: int) -> list:
        """
        This function will get all the warnings of a user.

        :param user_id: The ID of the user that should be checked.
        :param server_id: The ID of the server that should be checked.
        :return: A list of all the warnings of the user.
        """
        rows = await self.connection.execute(
            "SELECT user_id, server_id, moderator_id, reason, strftime('%s', created_at), id FROM warns WHERE user_id=? AND server_id=?",
            (
                user_id,
                server_id,
            ),
        )
        async with rows as cursor:
            result = await cursor.fetchall()
            result_list = []
            for row in result:
                result_list.append(row)
            return result_list

    async def upsert_voice_activity(self, user_id: int, month_year: str) -> int | None:
        """
        This function will add 1 minute to the user's voice activity time
        for the specified month and also increment the total time.
        If the user/month record doesn't exist, it creates a new record.
        Logs the operation and returns the new *total* minutes for the user.

        :param user_id: The ID of the user whose time should be incremented.
        :param month_year: The month string in 'YYYY-MM' format.
        :return: The new total minutes for the user, or None if an error occurred.
        """
        user_id_str = str(user_id) # Ensure user_id is stored as string
        total_minutes = None # Initialize total_minutes

        try:
            self.logger.debug(f"Attempting to upsert voice activity for user ID: {user_id_str} for month: {month_year}")

            # Upsert monthly record
            await self.connection.execute(
                """
                INSERT INTO voice_activity_monthly (user_id, month_year, monthly_minutes)
                VALUES (?, ?, 1)
                ON CONFLICT(user_id, month_year) DO UPDATE SET
                monthly_minutes = monthly_minutes + 1;
                """,
                (user_id_str, month_year),
            )
            self.logger.debug(f"Upserted monthly record for {user_id_str} / {month_year}")

            # Upsert total record
            await self.connection.execute(
                """
                INSERT INTO voice_activity_total (user_id, total_minutes)
                VALUES (?, 1)
                ON CONFLICT(user_id) DO UPDATE SET
                total_minutes = total_minutes + 1;
                """,
                (user_id_str,),
            )
            self.logger.debug(f"Upserted total record for {user_id_str}")

            await self.connection.commit()
            self.logger.debug(f"Successfully committed upserts for user ID: {user_id_str}")

            # Get the new total minutes
            cursor = await self.connection.execute(
                "SELECT total_minutes FROM voice_activity_total WHERE user_id = ?",
                (user_id_str,)
            )
            result = await cursor.fetchone()
            await cursor.close()

            if result:
                total_minutes = result[0]
                # Keep the INFO log concise, details are in DEBUG logs now
                self.logger.info(f"User ID: {user_id_str} now has {total_minutes} total minutes in voice.")
                return total_minutes
            else:
                self.logger.warning(f"Could not retrieve total minutes for user ID: {user_id_str} after upsert.")
                return None

        except Exception as e:
            self.logger.error(f"Database error during upsert_voice_activity for user ID {user_id_str}, month {month_year}: {e}", exc_info=True)
            # Attempt to rollback if commit failed or error occurred before commit
            try:
                await self.connection.rollback()
                self.logger.warning(f"Rolled back transaction for user ID {user_id_str} due to error.")
            except Exception as rb_e:
                self.logger.error(f"Failed to rollback transaction for user ID {user_id_str}: {rb_e}", exc_info=True)
            return None


    async def get_total_voice_times(self) -> list:
        """
        This function will retrieve all total voice activity records, ordered by minutes descending.

        :return: A list of tuples, each containing (user_id, total_minutes).
        """
        try:
            self.logger.debug("Attempting to fetch all total voice times.")
            rows = await self.connection.execute(
                "SELECT user_id, total_minutes FROM voice_activity_total ORDER BY total_minutes DESC"
            )
            async with rows as cursor:
                result = await cursor.fetchall()
                self.logger.debug(f"Successfully fetched {len(result)} total voice time records.")
                return result if result is not None else []
        except Exception as e:
            self.logger.error(f"Database error during get_total_voice_times: {e}", exc_info=True)
            return [] # Return empty list on error

    async def get_monthly_voice_times(self, month_year: str) -> list:
        """
        This function will retrieve monthly voice activity records for a specific month,
        ordered by minutes descending.

        :param month_year: The month string in 'YYYY-MM' format.
        :return: A list of tuples, each containing (user_id, monthly_minutes).
        """
        try:
            self.logger.debug(f"Attempting to fetch voice times for month: {month_year}.")
            rows = await self.connection.execute(
                """
                SELECT user_id, monthly_minutes
                FROM voice_activity_monthly
                WHERE month_year = ?
                ORDER BY monthly_minutes DESC
                """,
                (month_year,)
            )
            async with rows as cursor:
                result = await cursor.fetchall()
                self.logger.debug(f"Successfully fetched {len(result)} voice time records for month {month_year}.")
                return result if result is not None else []
        except Exception as e:
            self.logger.error(f"Database error during get_monthly_voice_times for month {month_year}: {e}", exc_info=True)
            return [] # Return empty list on error