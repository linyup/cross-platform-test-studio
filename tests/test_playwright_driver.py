import unittest

from test_studio.drivers.playwright import PlaywrightDriver


class _Body:
    def __init__(self, page):
        self.page = page

    def inner_text(self, timeout=0):
        return self.page.body


class _Page:
    url = "https://example.test/docs"
    body = "My documents"

    def locator(self, selector):
        assert selector == "body"
        return _Body(self)

    def title(self):
        return "Documents"


class PlaywrightSnapshotTests(unittest.TestCase):
    def test_visible_body_change_updates_fingerprint_without_exposing_body(self):
        driver = PlaywrightDriver.__new__(PlaywrightDriver)
        page = _Page()
        driver._active_page = lambda: page
        driver.inspect = lambda goal="": {"driver": "playwright", "elements": []}

        before = driver.snapshot()
        page.body = "My documents New blank document"
        after = driver.snapshot()

        self.assertNotEqual(before["page_fingerprint"], after["page_fingerprint"])
        self.assertNotIn("visible_text", after)


if __name__ == "__main__":
    unittest.main()
