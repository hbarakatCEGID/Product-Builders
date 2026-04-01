"""Run the webapp with uvicorn: python -m product_builders.webapp"""

from __future__ import annotations

import argparse
import sys


def main() -> None:
    try:
        import uvicorn
    except ImportError as e:
        print(
            "uvicorn is required to run the webapp. Install with:\n"
            "  pip install -e .\n"
            "or: pip install uvicorn[standard]",
            file=sys.stderr,
        )
        raise SystemExit(1) from e

    parser = argparse.ArgumentParser(description="Product Builders web server")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host")
    parser.add_argument("--port", type=int, default=8000, help="Port")
    parser.add_argument("--reload", action="store_true", help="Dev auto-reload")
    args = parser.parse_args()

    uvicorn.run(
        "product_builders.webapp.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
