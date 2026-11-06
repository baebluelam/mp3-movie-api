import logging

import pandas as pd


logger = logging.getLogger(__name__)


def validate_dataframe(df, required_columns, numeric_columns):
    """Validate the DataFrame and return valid data.

    required_columns: a list of column names that must exist.
    numeric_columns: a list of column names whose values should be numeric.
    """

    result = df.copy()
    rows_before = len(result)

    for column in required_columns:
        if column not in result.columns:
            logger.error(f"Required column missing: {column}")
            raise ValueError(f"Required column missing: {column}")

    for column in numeric_columns:
        invalid_rows = []

        for index, value in result[column].items():
            if pd.notna(value):
                try:
                    float(value)
                except (ValueError, TypeError):
                    invalid_rows.append(index)

        if invalid_rows:
            logger.warning(
                f"Removed {len(invalid_rows)} rows with invalid "
                f"numeric values in {column}"
            )

            result = result.drop(index=invalid_rows)

        result[column] = pd.to_numeric(result[column])

    rows_removed = rows_before - len(result)

    logger.debug(
        f"Validation: {rows_before} -> {len(result)} rows "
        f"({rows_removed} removed)"
    )

    return result