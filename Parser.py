from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import json, sys, re

URL = "https://mcx.aero/board/"

_SPACE_RE = re.compile(r"\s+")
def normalize(text: str) -> str:
    cleaned = (
        text.replace("\u00A0", " ")  # NBSP → space
            .replace("\t", " ")
            .replace("\r", " ")
            .replace("\n", " ")
    )
    return _SPACE_RE.sub(" ", cleaned).strip()

def safe_text(node, selector, default=""):
    try:
        el = node.query_selector(selector)
        return normalize(el.inner_text()) if el else default
    except Exception:
        return default


#  Main
def scrape_board(board_type: str = "departures") -> list[dict]:
    assert board_type in ("departures", "arrivals")

    flights = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            page.goto(URL, timeout=60_000)
        except PlaywrightTimeoutError:
            print("Не удалось загрузить страницу", file=sys.stderr)
            browser.close()
            return flights

        # переключение на вкладку «Прилет»
        if board_type == "arrivals":
            page.locator("li#arrival > button.flight-tabs__tab").click()
            # ждём, пока li#arrival станет активным
            page.wait_for_selector("li#arrival.flight-tabs__item--active", timeout=7_000)
            # и появится заголовок «Время прилета»
            page.wait_for_selector(
                "span.c-flight-board__heading:text('Время прилета')", timeout=7_000
            )
            page.wait_for_timeout(1_000)

        # ожидаю строки табло
        page.wait_for_selector(".c-flight-board__item[data-id]", timeout=15_000)
        rows = page.query_selector_all(".c-flight-board__item[data-id]")

        time_key = "Время вылета" if board_type == "departures" else "Время прилета"

        for row in rows:
            flight = {
                "Рейс":            safe_text(row, "a.c-board-info__link"),
                "Авиакомпания":    safe_text(row, "div.c-flight-board__elem:nth-child(2) span:last-child"),
                "Направление":     safe_text(row, "div.c-flight-board__elem:nth-child(3) .c-flight-board__value"),
                time_key:          safe_text(row, "div.c-flight-board__elem:nth-child(4) .c-flight-board__value"),
                "Ожидаемое время": safe_text(row, "div.c-flight-board__elem:nth-child(5) .c-flight-board__value"),
                "Статус":          safe_text(row, "div.c-flight-board__elem:nth-child(6) .c-flight-board__value"),
            }

            for det in row.query_selector_all(
                ".c-flight-board__item-dropdown .c-flight-board__details-item"
            ):
                title = safe_text(det, ".c-flight-board__details-title")
                value = safe_text(det, ".c-flight-board__details-text")
                if title:
                    flight[title] = value

            flights.append(flight)

        browser.close()
    return flights

# test (zaebalsya)
if __name__ == "__main__":
    print("=== DEPARTURES ===")
    print(json.dumps(scrape_board("departures"), ensure_ascii=False, indent=2))

    print("\n=== ARRIVALS ===")
    print(json.dumps(scrape_board("arrivals"), ensure_ascii=False, indent=2))
