import logging

import pandas as pd


logger = logging.getLogger(__name__)


def remove_duplicates(df):
    """Remove duplicate rows."""

    rows_before = len(df)
    result = df.drop_duplicates()
    rows_removed = rows_before - len(result)

    logger.debug(
        f"remove_duplicates: removed={rows_removed}"
    )

    return result


def handle_missing(df, axis="rows"):
    """Drop rows or columns containing missing values."""

    if axis == "rows":
        rows_before = len(df)
        result = df.dropna()
        rows_removed = rows_before - len(result)

        logger.debug(
            f"handle_missing: removed={rows_removed} rows"
        )

        return result

    if axis == "columns":
        columns_before = len(df.columns)
        result = df.dropna(axis=1)
        columns_removed = columns_before - len(result.columns)

        logger.debug(
            f"handle_missing: removed={columns_removed} columns"
        )

        return result

    logger.error(f"Unsupported missing-value axis: {axis}")
    raise ValueError(f"Unsupported missing-value axis: {axis}")


def remove_outliers(df, columns, method, threshold):
    """Remove outliers from the specified numeric columns."""

    if method not in ["iqr", "zscore"]:
        logger.error(f"Unsupported outlier method: {method}")
        raise ValueError(f"Unsupported outlier method: {method}")

    result = df.copy()

    for column in columns:
        if column not in result.columns:
            logger.warning(f"Column not found: {column}")
            continue

        if not pd.api.types.is_numeric_dtype(result[column]):
            logger.warning(f"Column is not numeric: {column}")
            continue

        rows_before = len(result)

        if method == "iqr":
            q1 = result[column].quantile(0.25)
            q3 = result[column].quantile(0.75)
            iqr = q3 - q1

            lower = q1 - threshold * iqr
            upper = q3 + threshold * iqr

            keep_rows = (
                result[column].between(lower, upper)
                | result[column].isna()
            )

            result = result[keep_rows]
            rows_removed = rows_before - len(result)

            logger.debug(
                f"{column}: method={method}, "
                f"threshold={threshold}, lower={lower}, "
                f"upper={upper}, removed={rows_removed}"
            )

        elif method == "zscore":
            mean = result[column].mean()
            standard_deviation = result[column].std(ddof=0)

            if standard_deviation == 0 or pd.isna(standard_deviation):
                rows_removed = 0
            else:
                z_scores = (
                    (result[column] - mean) / standard_deviation
                ).abs()

                keep_rows = (
                    (z_scores <= threshold)
                    | result[column].isna()
                )

                result = result[keep_rows]
                rows_removed = rows_before - len(result)

            logger.debug(
                f"{column}: method={method}, "
                f"threshold={threshold}, removed={rows_removed}"
            )

    return result


def process_data(df, config):
    """Apply the processing steps enabled in the configuration."""

    processing_config = config["processing"]
    result = df.copy()

    if processing_config.get("remove_duplicates", False):
        result = remove_duplicates(result)

    missing_config = processing_config.get("missing", {})

    if missing_config.get("enabled", False):
        result = handle_missing(
            result,
            axis=missing_config.get("axis", "rows")
        )

    outlier_config = processing_config.get("outliers", {})

    if outlier_config.get("enabled", False):
        result = remove_outliers(
            result,
            columns=outlier_config.get("columns", []),
            method=outlier_config.get("method", "iqr"),
            threshold=outlier_config.get("threshold", 1.5)
        )

    return result


def create_cleaning_report(df_before, df_after):
    """Return a dictionary summarizing the cleaning results."""

    return {
        "rows_before": len(df_before),
        "rows_after": len(df_after),
        "rows_removed": len(df_before) - len(df_after),
        "columns_before": len(df_before.columns),
        "columns_after": len(df_after.columns),
        "columns_removed": (
            len(df_before.columns) - len(df_after.columns)
        )
    }