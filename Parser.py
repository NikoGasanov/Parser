from playwright.sync_api import sync_playwright
import json

URL = "https://mcx.aero/board/"

def scrape_board(board_type: str = "departures") -> list[dict]:
    assert board_type in ("departures", "arrivals")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL, timeout=60000)

        if board_type == "arrivals":
            page.locator("li#arrival button.flight-tabs__tab").click()

        page.wait_for_selector(".c-flight-board__item[data-id]", timeout=15000)

        flights = []
        rows = page.query_selector_all(".c-flight-board__item[data-id]")

        for row in rows:
            flight = {
                "Рейс": row.query_selector("a.c-board-info__link").inner_text().strip(),
                "Авиакомпания": row.query_selector(
                    "div.c-flight-board__elem:nth-child(2) span:last-child"
                ).inner_text().strip(),
                "Направление": row.query_selector(
                    "div.c-flight-board__elem:nth-child(3) .c-flight-board__value"
                ).inner_text().strip(),
                "Время вылета": row.query_selector(
                    "div.c-flight-board__elem:nth-child(4) .c-flight-board__value"
                ).inner_text().strip(),
                "Ожидаемое время": row.query_selector(
                    "div.c-flight-board__elem:nth-child(5) .c-flight-board__value"
                ).inner_text().strip(),
                "Статус": row.query_selector(
                    "div.c-flight-board__elem:nth-child(6) .c-flight-board__value"
                ).inner_text().strip(),
            }

            for det in row.query_selector_all(
                ".c-flight-board__item-dropdown .c-flight-board__details-item"
            ):
                title = det.query_selector(".c-flight-board__details-title").inner_text().strip()
                value = (
                    det.query_selector(".c-flight-board__details-text")
                    .inner_text()              # ← исправлено
                    .replace("\n", " ")
                    .strip()
                )
                flight[title] = value

            flights.append(flight)

        browser.close()
        return flights


if __name__ == "__main__":
    print(json.dumps(scrape_board("departures"), ensure_ascii=False, indent=2))
