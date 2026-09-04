import asyncio

import structlog

from cartoon_studio.config import get_settings

logger = structlog.get_logger()


async def run() -> None:
    settings = get_settings()
    logger.info(
        "worker_ready",
        environment=settings.environment,
        detail="Task adapter will be connected in the workflow implementation phase.",
    )


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
