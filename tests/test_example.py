import re
from playwright.sync_api import Page, expect

def test_has_title(page: Page):
    page.goto("https://www.kleinanzeigen.de")

    # Expect a title "to contain" a substring.
    expect(page).to_have_title(re.compile("Kleinanzeigen – früher eBay Kleinanzeigen."))

def test_get_started_link(page: Page):  
    page.goto("https://www.kleinanzeigen.de")

    # Click the get started link.
    page.get_by_alt_text(text="Logo Kleinanzeigen").click()

    # Expects page to have a heading with the name of Installation.
    expect(page.get_by_placeholder(text="Was suchst du?", exact=True))
    