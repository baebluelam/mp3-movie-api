import io
import logging
from pathlib import Path

import pandas as pd
from fastapi import (
    FastAPI,
    File,
    HTTPException,
    Query,
    UploadFile,
)

from data_pipeline import (
    create_cleaning_report,
    process_data,
    validate_dataframe,
)
from src import (
    HealthResponse,
    MovieDataResponse,
    MovieProcessingReport,
    MovieStorage,
    MovieUploadInfo,
    ProcessConfig,
    log_requests,
    setup_logging,
)
from src.storage import MOVIE_COLUMNS


setup_logging(verbose=True)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Movie Processing API",
    version="1.0.0",
)

app.middleware("http")(log_requests)

storage = MovieStorage()


@app.get("/health", response_model=HealthResponse)
def health_check():
    """Return the application status and version."""
    return {
        "status": "ok",
        "version": "1.0.0",
    }


@app.post("/upload", response_model=MovieUploadInfo)
async def upload_movies(
    file: UploadFile = File(...),
):
    """Upload a CSV and replace the movie collection."""
    extension = Path(file.filename or "").suffix.lower()

    if extension != ".csv":
        logger.warning(
            "Unsupported file format: %s",
            extension,
        )
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are supported",
        )

    try:
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))

    except (
        pd.errors.EmptyDataError,
        pd.errors.ParserError,
        UnicodeDecodeError,
    ) as error:
        logger.warning(
            "Unreadable CSV upload: %s",
            error,
        )
        raise HTTPException(
            status_code=400,
            detail="Unable to parse CSV file",
        ) from error

    if list(df.columns) != MOVIE_COLUMNS:
        raise HTTPException(
            status_code=400,
            detail=(
                "CSV must contain exactly these columns: "
                f"{MOVIE_COLUMNS}"
            ),
        )

    if df.empty:
        raise HTTPException(
            status_code=400,
            detail="CSV must contain at least one movie",
        )

    df = df[MOVIE_COLUMNS]
    storage.save(df)

    logger.info(
        "Uploaded movies: filename=%s, rows=%s",
        file.filename,
        len(df),
    )

    return {
        "filename": file.filename,
        "rows": len(df),
        "columns": len(df.columns),
        "column_names": list(df.columns),
    }


@app.get(
    "/movies",
    response_model=MovieDataResponse,
)
def get_movies(
    limit: int = Query(default=100, ge=1),
):
    """Return up to limit stored movies."""
    total_rows = storage.count_movies()

    if total_rows == 0:
        data = []
    else:
        data = storage.select_columns(
            MOVIE_COLUMNS,
            limit,
        )

    logger.info(
        "Retrieved movies: returned_rows=%s",
        len(data),
    )

    return {
        "data": data,
        "total_rows": total_rows,
    }


@app.get(
    "/movies/search",
    response_model=list[dict],
)
def query_movies(
    columns: list[str] = Query(
        default=["title"]
    ),
    min_rating: float = Query(
        default=0,
        ge=0,
        le=10,
    ),
    limit: int = Query(
        default=100,
        ge=1,
    ),
):
    """Search movies using SQL."""
    try:
        result = storage.query_movies(
            columns,
            min_rating,
            limit,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    logger.info(
        (
            "Queried movies: columns=%s, "
            "min_rating=%s, returned_rows=%s"
        ),
        columns,
        min_rating,
        len(result),
    )

    return result


@app.post(
    "/movies/process",
    response_model=MovieProcessingReport,
)
def process_movies(config: ProcessConfig):
    """Validate, clean, and replace stored movies."""
    df = storage.get()

    if df.empty:
        raise HTTPException(
            status_code=400,
            detail="No movies have been uploaded",
        )

    settings = config.model_dump()
    validation = settings["validation"]

    try:
        validated = validate_dataframe(
            df,
            validation["required_columns"],
            validation["numeric_columns"],
        )

        validation_rows_removed = (
            len(df) - len(validated)
        )

        before_processing = validated.copy()

        processed = process_data(
            validated,
            settings,
        )

        report = create_cleaning_report(
            before_processing,
            processed,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    storage.save(processed)

    logger.info(
        (
            "Processed movies: validation_removed=%s, "
            "rows_before=%s, rows_after=%s"
        ),
        validation_rows_removed,
        report["rows_before"],
        report["rows_after"],
    )

    return {
        "validation_rows_removed": (
            validation_rows_removed
        ),
        "cleaning_report": report,
    }