def test_upload_replaces_collection(client, sample_csv_bytes):
    files = {
        "file": (
            "sample_movies.csv",
            sample_csv_bytes,
            "text/csv",
        )
    }

    first_response = client.post("/upload", files=files)
    second_response = client.post("/upload", files=files)

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["rows"] == 20

    retrieved = client.get("/movies")

    assert retrieved.status_code == 200
    assert retrieved.json()["total_rows"] == 20


def test_get_and_search_movies(client, uploaded_movies):
    retrieved = client.get(
        "/movies",
        params={"limit": 2},
    )

    assert retrieved.status_code == 200
    assert retrieved.json()["total_rows"] == 20
    assert len(retrieved.json()["data"]) == 2

    searched = client.get(
        "/movies/search",
        params=[
            ("columns", "title"),
            ("columns", "rating"),
            ("min_rating", 8.5),
            ("limit", 2),
        ],
    )

    assert searched.status_code == 200
    assert searched.json() == [
        {
            "id": 4,
            "title": "Movie C",
            "rating": 9.0,
        },
        {
            "id": 2,
            "title": "Movie B",
            "rating": 8.5,
        },
    ]


def test_process_movies(client, uploaded_movies):
    response = client.post(
        "/movies/process",
        json={},
    )

    assert response.status_code == 200

    report = response.json()

    assert report["validation_rows_removed"] == 0
    assert report["cleaning_report"]["rows_before"] == 20
    assert report["cleaning_report"]["rows_after"] == 18

    retrieved = client.get("/movies")

    assert retrieved.status_code == 200
    assert retrieved.json()["total_rows"] == 18


def test_errors_and_health(client):
    bad_upload = client.post(
        "/upload",
        files={
            "file": (
                "movies.txt",
                b"bad",
                "text/plain",
            )
        },
    )

    assert bad_upload.status_code == 400
    assert client.get("/health").status_code == 200

    bad_search = client.get(
        "/movies/search",
        params={"columns": "nope"},
    )

    assert bad_search.status_code == 400