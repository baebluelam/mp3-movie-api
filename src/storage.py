import logging
import sqlite3

import pandas as pd

from .database import get_connection, initialize_database

logger = logging.getLogger(__name__)

MOVIE_COLUMNS = ["title", "release_year", "rating", "genre"]


class MovieStorage:
    def __init__(self, db_path="data/movies.db"):
        """Initialize the storage and create the database table."""
        self.db_path = db_path
        initialize_database(self.db_path)

    def save(self, df):
        """Replace all stored movies with the movies in the DataFrame."""
        records = (
            df[MOVIE_COLUMNS]
            .astype(object)
            .where(pd.notna(df[MOVIE_COLUMNS]), None)
        )

        connection = get_connection(self.db_path)

        try:
            connection.execute("DELETE FROM movies")

            connection.executemany(
                """
                INSERT INTO movies (
                    title,
                    release_year,
                    rating,
                    genre
                )
                VALUES (?, ?, ?, ?)
                """,
                list(records.itertuples(index=False, name=None)),
            )

            connection.commit()

            logger.debug(
                "Stored movies in SQLite: rows=%s",
                len(records),
            )

        except sqlite3.Error:
            connection.rollback()
            logger.exception("Failed to store movies")
            raise

        finally:
            connection.close()

    def get(self):
        """Return all stored movies as a pandas DataFrame."""
        connection = get_connection(self.db_path)

        try:
            rows = connection.execute(
                """
                SELECT
                    title,
                    release_year,
                    rating,
                    genre
                FROM movies
                ORDER BY id
                """
            ).fetchall()

            return pd.DataFrame(
                [dict(row) for row in rows],
                columns=MOVIE_COLUMNS,
            )

        finally:
            connection.close()

    def _validate_columns(self, columns):
        """Check that requested columns are supported movie columns."""
        if not columns:
            logger.error("Select at least one column")
            raise ValueError("Select at least one column")

        for column in columns:
            if column not in MOVIE_COLUMNS:
                logger.error("Unsupported column: %s", column)
                raise ValueError(f"Unsupported column: {column}")

    def select_columns(self, columns, limit=5):
        """Return the ID and requested columns for a limited number of movies."""
        self._validate_columns(columns)

        selected_columns = ", ".join(["id"] + columns)
        connection = get_connection(self.db_path)

        try:
            rows = connection.execute(
                f"""
                SELECT {selected_columns}
                FROM movies
                ORDER BY id
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

            results = [dict(row) for row in rows]

            logger.debug(
                "Selected movie columns: columns=%s, rows=%s",
                columns,
                len(results),
            )

            return results

        finally:
            connection.close()

    def count_movies(self):
        """Return the total number of stored movies."""
        connection = get_connection(self.db_path)

        try:
            row = connection.execute(
                "SELECT COUNT(*) FROM movies"
            ).fetchone()

            return row[0]

        finally:
            connection.close()

    def query_movies(self, columns, min_rating, limit):
        """Search movies using a minimum rating and selected columns."""
        self._validate_columns(columns)

        selected_columns = ", ".join(["id"] + columns)
        connection = get_connection(self.db_path)

        try:
            rows = connection.execute(
                f"""
                SELECT {selected_columns}
                FROM movies
                WHERE rating >= ?
                ORDER BY rating DESC, id ASC
                LIMIT ?
                """,
                (min_rating, limit),
            ).fetchall()

            results = [dict(row) for row in rows]

            logger.debug(
                "Queried movies: columns=%s, min_rating=%s, rows=%s",
                columns,
                min_rating,
                len(results),
            )

            return results

        finally:
            connection.close()

    def clear(self):
        """Delete all stored movies. This is used by the automated tests."""
        connection = get_connection(self.db_path)

        try:
            connection.execute("DELETE FROM movies")
            connection.commit()

        except sqlite3.Error:
            connection.rollback()
            logger.exception("Failed to clear stored movies")
            raise

        finally:
            connection.close()