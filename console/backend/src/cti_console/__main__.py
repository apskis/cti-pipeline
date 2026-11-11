"""Start the console API on this machine only: python -m cti_console"""

from __future__ import annotations

import logging
import os

import uvicorn

from .api import create_app

# Loopback only, on purpose, and not configurable: the output holds internal threat
# intelligence and the API has no authentication.
HOST = "127.0.0.1"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    port = int(os.environ.get("CTI_CONSOLE_PORT", "8765"))
    uvicorn.run(create_app(), host=HOST, port=port)


if __name__ == "__main__":
    main()
