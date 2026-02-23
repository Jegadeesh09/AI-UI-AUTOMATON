import pytest
import pandas as pd
import os
import allure
from playwright.sync_api import Page, expect

# Define a path for screenshots
SCREENSHOT_DIR = "backend/storage/suites/Viking Pump Curve/screenshots/RecordedSession"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

class PupilLeaderPage:
    """
    Page Object Model for the PupilLeader website.
    All selectors and page interactions are defined here.
    """

    # --- Selectors ---
    # NOTE: Selectors for steps after GOTO are inferred based on the BDD story,
    # as the provided TRACE LOG only contained the GOTO step and its failure.

    # Selector for the text "A leading communication platform to connect school"
    # Assuming this text is contained within a clickable element or a visible block.
    # Using a generic XPath to find any element containing this normalized text.
    TEXT_PLATFORM_DESCRIPTION = "xpath=//*[contains(normalize-space(.), 'A leading communication platform to connect school')]"

    # Selector for the main heading with text "A leading communication platform to connect school, Teachers and parents"
    # Assuming it's a prominent heading element (h1, h2, etc.)
    HEADING_PLATFORM_FULL_TEXT = "xpath=//*[normalize-space(text())='A leading communication platform to connect school, Teachers and parents' and (self::h1 or self::h2 or self::h3 or self::h4 or self::h5 or self::h6)]"

    # Selector for the "About Us" link
    LINK_ABOUT_US = "xpath=//a[normalize-space(.)='About Us']"

    # Selector for the heading on the About Us page
    HEADING_ABOUT_US_PAGE = "xpath=//*[normalize-space(text())='Best School Management Software with Communication Platform across Schools' and (self::h1 or self::h2 or self::h3 or self::h4 or self::h5 or self::h6)]"


    def __init__(self, page: Page):
        self.page = page

    @allure.step("Navigate to {url}")
    def navigate_to_url(self, url: str):
        """Navigates to the specified URL and waits for the network to be idle."""
        self.page.goto(url, wait_until="networkidle")
        self.page.wait_for_load_state("networkidle") # Redundant due to wait_until, but safe.

    @allure.step("Click on element: {selector}")
    def click_element(self, selector: str):
        """Clicks an element after waiting for it to be visible."""
        self.page.wait_for_selector(selector, state="visible", timeout=30000)
        self.page.click(selector)
        # Assuming a click might trigger an animation or minor state change,
        # but not necessarily a full page load unless explicitly navigating.
        # Adding a small timeout for stability if needed, or wait for next element.
        # self.page.wait_for_timeout(500)

    @allure.step("Verify heading text: {expected_text}")
    def verify_heading_text(self, selector: str, expected_text: str):
        """Verifies that an element contains the expected text."""
        self.page.wait_for_selector(selector, state="visible", timeout=30000)
        expect(self.page.locator(selector)).to_have_text(expected_text)

    @allure.step("Verify current page URL: {expected_url}")
    def verify_current_url(self, expected_url: str):
        """Verifies that the current page URL matches the expected URL."""
        expect(self.page).to_have_url(expected_url)


@allure.parent_suite("Viking Pump Curve")
@allure.suite("RecordedSession")
@allure.title("User explores the PupilLeader website and verifies key content")
def test_RecordedSession(page: Page):
    """
    Test scenario: User explores the PupilLeader website and verifies key content.
    """
    pupil_leader_page = PupilLeaderPage(page)
    step_counter = 0

    def take_allure_screenshot(step_name: str):
        """Helper function to take and attach screenshots to Allure."""
        nonlocal step_counter
        step_counter += 1
        screenshot_path = os.path.join(SCREENSHOT_DIR, f"step_{step_counter}_{step_name.replace(' ', '_').replace('/', '_')}.png")
        page.screenshot(path=screenshot_path)
        allure.attach.file(screenshot_path, name=f"Step {step_counter}: {step_name}", attachment_type=allure.attachment_type.PNG)

    allure.dynamic.story("User explores the PupilLeader website and verifies key content")

    # Given Navigate to "https://pupilleader.com/"
    with allure.step('Given Navigate to "https://pupilleader.com/"'):
        pupil_leader_page.navigate_to_url("https://pupilleader.com/")
        take_allure_screenshot("Navigate to PupilLeader Home")

    # When Click on the element containing the text "A leading communication platform to connect school"
    with allure.step('When Click on the element containing the text "A leading communication platform to connect school"'):
        pupil_leader_page.click_element(PupilLeaderPage.TEXT_PLATFORM_DESCRIPTION)
        # After clicking, wait for any potential network activity or state change if it's an internal link/action
        page.wait_for_load_state("networkidle")
        take_allure_screenshot("Click on platform description")

    # Then I should see the heading with text "A leading communication platform to connect school, Teachers and parents"
    with allure.step('Then I should see the heading with text "A leading communication platform to connect school, Teachers and parents"'):
        expected_heading_text = "A leading communication platform to connect school, Teachers and parents"
        pupil_leader_page.verify_heading_text(PupilLeaderPage.HEADING_PLATFORM_FULL_TEXT, expected_heading_text)
        take_allure_screenshot("Verify home page heading")

    # When Click on the "About Us" link
    with allure.step('When Click on the "About Us" link'):
        pupil_leader_page.click_element(PupilLeaderPage.LINK_ABOUT_US)
        page.wait_for_load_state("networkidle")
        take_allure_screenshot("Click About Us link")

    # Then I should be on the "https://pupilleader.com/about.html" page
    with allure.step('Then I should be on the "https://pupilleader.com/about.html" page'):
        expected_url = "https://pupilleader.com/about.html"
        pupil_leader_page.verify_current_url(expected_url)
        take_allure_screenshot("Verify About Us URL")

    # And I should see the heading with text "Best School Management Software with Communication Platform across Schools"
    with allure.step('And I should see the heading with text "Best School Management Software with Communication Platform across Schools"'):
        expected_heading_text = "Best School Management Software with Communication Platform across Schools"
        pupil_leader_page.verify_heading_text(PupilLeaderPage.HEADING_ABOUT_US_PAGE, expected_heading_text)
        take_allure_screenshot("Verify About Us page heading")