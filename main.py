import uvicorn


def main() -> None:
    """Entry point for local execution of the FastAPI application server."""
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
