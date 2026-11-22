"""``py -m api`` starts the backend with uvicorn."""

from __future__ import annotations

import argparse

import uvicorn


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description="AmbiLiving backend (FastAPI)")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--reload", action="store_true", help="restart on code changes")
    args = p.parse_args(argv)
    uvicorn.run("api.main:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
