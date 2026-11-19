import asyncio
import logging
from typing import Callable

from playwright.async_api import Error as PlaywrightAsyncError
from playwright.async_api import Page as AsyncPage
from playwright.async_api import expect as expect_async

from config import RESPONSE_CONTAINER_SELECTOR, RESPONSE_TEXT_SELECTOR


async def locate_response_elements(
    page: AsyncPage,
    req_id: str,
    logger: logging.Logger,
    check_client_disconnected: Callable[[str], bool],
) -> None:
    """Locate response container and text elements, including timeout and error handling."""
    logger.info(f"[{req_id}] Locating response elements...")
    response_container = page.locator(RESPONSE_CONTAINER_SELECTOR).last
    response_element = response_container.locator(RESPONSE_TEXT_SELECTOR)

    try:
        await expect_async(response_container).to_be_attached(timeout=20000)
        check_client_disconnected("After Response Container Attached: ")
        await expect_async(response_element).to_be_attached(timeout=90000)
        logger.info(f"[{req_id}] Response elements located.")
    except (PlaywrightAsyncError, asyncio.TimeoutError) as locate_err:
        await _save_locate_failure_snapshot(page, req_id, locate_err)
        from .error_utils import upstream_error

        raise upstream_error(
            req_id, f"Failed to locate AI Studio response elements: {locate_err}"
        )
    except Exception as locate_exc:
        await _save_locate_failure_snapshot(page, req_id, locate_exc)
        from .error_utils import server_error

        raise server_error(
            req_id, f"Unexpected error while locating response elements: {locate_exc}"
        )


async def _save_locate_failure_snapshot(
    page: AsyncPage, req_id: str, error: Exception
) -> None:
    """Persist diagnostics when the response UI cannot be located."""
    try:
        from browser_utils.operations import save_error_snapshot

        await save_error_snapshot(
            f"response_locate_fail_{req_id}",
            extra_context={
                "error": str(error),
                "page_url": page.url,
                "response_container_count": await page.locator(
                    RESPONSE_CONTAINER_SELECTOR
                ).count(),
                "response_text_count": await page.locator(
                    RESPONSE_TEXT_SELECTOR
                ).count(),
            },
        )
    except Exception:
        pass
