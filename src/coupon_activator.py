from dataclasses import dataclass

from loguru import logger
from playwright.async_api import Page

from .config import Config


@dataclass
class ActivationResult:
    total_found: int = 0
    activated: int = 0
    failed: int = 0
    limit_reached: bool = False


async def _dismiss_cookie_banner(page: Page) -> None:
    """Dismiss cookie consent banner if visible."""
    try:
        btn = page.locator('button:has-text("Alle Cookies akzeptieren")').first
        if await btn.is_visible(timeout=2000):
            await btn.click()
            await page.wait_for_timeout(1000)
    except Exception as e:
        logger.error(e)


async def activate_batch(page: Page, max_count: int, offset: int = 0, total: int | None = None) -> ActivationResult:
    """Activate up to max_count coupons on a fresh page.

    Sets result.limit_reached if max_count was hit (more coupons may remain).
    The caller is responsible for closing the browser and pausing.
    """
    result = ActivationResult()

    await page.goto(Config.COUPONS_URL, wait_until="load")
    await page.wait_for_load_state("networkidle")
    await _dismiss_cookie_banner(page)

    # Wait for content to render
    await page.wait_for_timeout(3000)

    result.total_found = await page.locator("button", has_text="jetzt aktivieren").count()
    logger.info(f"Found {result.total_found} coupons")
    total = total if total is not None else result.total_found

    while result.activated < max_count:
        btn = page.locator("button", has_text="jetzt aktivieren").first
        try:
            if not await btn.is_visible(timeout=500):
                break
            await btn.click()
            result.activated += 1
            done = offset + result.activated
            if done % 25 == 0:
                logger.info(f"Progress: {done}/{total}")
            await page.wait_for_timeout(Config.COOLDOWN_SECONDS * 1000)
        except Exception as e:
            result.failed += 1
            logger.warning(f"Coupon activation failed: {e}")
            break
    else:
        result.limit_reached = True

    return result


async def keep_session_alive(page: Page) -> None:
    """Visit page briefly to keep cookies active."""
    try:
        await page.goto(Config.COUPONS_URL, wait_until="load")
        await page.wait_for_timeout(2000)
        logger.info("Session keepalive done")
    except Exception as e:
        logger.warning(f"Keepalive failed: {e}")
