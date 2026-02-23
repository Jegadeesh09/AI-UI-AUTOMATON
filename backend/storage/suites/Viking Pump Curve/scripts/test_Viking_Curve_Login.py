import pandas as pd
import os
import allure
from playwright.sync_api import Page, expect

# Global counter for screenshots to ensure unique filenames per step within a test
_screenshot_counter = 1

def _read_data_from_path(data_path: str):
    """
    Reads a specific cell from a data file based on the format <FileName.ColumnName_RowNumber>.
    Row 2 in the file corresponds to pd.iloc[0] (the first data row).
    Supported file types: CSV, XLSX, XLS, JSON.
    """
    if not data_path.startswith("<") or not data_path.endswith(">"):
        # If the string is not in the expected format, return it as is.
        # This allows direct values like "jraja@idexcorp.com" to pass through.
        return data_path

    # Extract FileName, ColumnName, RowNumber from the format <FileName.ColumnName_RowNumber>
    parts = data_path.strip("<>").split(".")
    if len(parts) != 2:
        raise ValueError(f"Invalid data path format: {data_path}. Expected <FileName.ColumnName_RowNumber>")

    file_name = parts[0]
    column_info = parts[1].split("_")
    if len(column_info) != 2:
        raise ValueError(f"Invalid data path format: {data_path}. Expected <FileName.ColumnName_RowNumber>")
    
    column_name = column_info[0]
    row_number_str = column_info[1]

    try:
        row_number = int(row_number_str)
    except ValueError:
        raise ValueError(f"Invalid row number in data path: {data_path}. Row number must be an integer.")

    # Construct the full file path by checking common extensions
    base_dir = "backend/data"
    
    # Prioritize CSV, then XLSX, then XLS, then JSON
    possible_file_paths = [
        os.path.join(base_dir, f"{file_name}.csv"),
        os.path.join(base_dir, f"{file_name}.xlsx"),
        os.path.join(base_dir, f"{file_name}.xls"),
        os.path.join(base_dir, f"{file_name}.json")
    ]

    actual_file_path = None
    for path in possible_file_paths:
        if os.path.exists(path):
            actual_file_path = path
            break
    
    if actual_file_path is None:
        raise FileNotFoundError(f"Data file not found for '{file_name}' in '{base_dir}'. Looked for .csv, .xlsx, .xls, .json.")

    # Read the data file using pandas based on its extension
    file_extension = os.path.splitext(actual_file_path)[1].lower()
    df = None
    if file_extension == '.csv':
        df = pd.read_csv(actual_file_path)
    elif file_extension in ('.xlsx', '.xls'):
        df = pd.read_excel(actual_file_path)
    elif file_extension == '.json':
        df = pd.read_json(actual_file_path)
    else:
        # This case should ideally not be reached if actual_file_path was found
        raise ValueError(f"Unsupported file type: {file_extension}")

    # Row 2 in the file is pd.iloc[0], so row_number - 2 corresponds to the 0-indexed row
    data_row_index = row_number - 2
    if data_row_index < 0 or data_row_index >= len(df):
        raise IndexError(f"Row {row_number} (0-indexed: {data_row_index}) out of bounds for file {actual_file_path}. File has {len(df)} data rows.")

    if column_name not in df.columns:
        raise KeyError(f"Column '{column_name}' not found in file {actual_file_path}. Available columns: {df.columns.tolist()}")

    return df.iloc[data_row_index][column_name]

def _attach_screenshot(page: Page, step_description: str):
    """
    Takes a screenshot, saves it to a predefined path, and attaches it to the Allure report.
    """
    global _screenshot_counter
    screenshot_dir = "backend/storage/suites/Viking Pump Curve/screenshots/viking_curve_login"
    os.makedirs(screenshot_dir, exist_ok=True) # Ensure directory exists
    screenshot_path = os.path.join(screenshot_dir, f"step_{_screenshot_counter}.png")
    page.screenshot(path=screenshot_path)
    allure.attach.file(screenshot_path, name=f"Step {_screenshot_counter}: {step_description}", attachment_type=allure.attachment_type.PNG)
    _screenshot_counter += 1

class VikingPumpCurveLoginPage:
    """
    Page object for the Viking Pump Curve Login page, encapsulating selectors and interactions.
    """
    # --- Selectors ---
    BASE_URL = "https://www.vikingpumpcurve.com/"
    USERNAME_INPUT = "#edit-name"
    PASSWORD_INPUT = "#edit-pass"
    # The trace log provided "ERROR_SELECTOR" for the login button.
    # Based on common web form patterns for a "Log In" action,
    # "input[value='Log In']" is a robust CSS selector for a submit button.
    LOGIN_BUTTON = "input[value='Log In']"
    EXPECTED_LOGIN_URL = "https://www.vikingpumpcurve.com/?check_logged_in=1"
    # Provided XPath for the success message
    SUCCESS_MESSAGE = "//*[@id='main']/div[1]/section[1]/div[1]/div[1]/p[1]"

    def __init__(self, page: Page):
        self.page = page

    @allure.step("Navigate to the Viking Pump Curve login page")
    def navigate(self):
        """Navigates to the base URL and waits for the network to be idle."""
        _attach_screenshot(self.page, "Before navigating to URL")
        self.page.goto(self.BASE_URL, wait_until="networkidle")
        _attach_screenshot(self.page, f"Navigated to {self.BASE_URL}")

    @allure.step("Type username: {username}")
    def type_username(self, username: str):
        """Types the given username into the username field."""
        self.page.wait_for_selector(self.USERNAME_INPUT, state="visible", timeout=30000)
        _attach_screenshot(self.page, f"Before typing username '{username}'")
        self.page.fill(self.USERNAME_INPUT, username)
        _attach_screenshot(self.page, f"Typed username '{username}'")

    @allure.step("Type password: <sensitive_data>")
    def type_password(self, password: str):
        """Types the given password into the password field."""
        self.page.wait_for_selector(self.PASSWORD_INPUT, state="visible", timeout=30000)
        _attach_screenshot(self.page, "Before typing password")
        # For sensitive data, avoid logging the actual value directly in the step description
        self.page.fill(self.PASSWORD_INPUT, password)
        _attach_screenshot(self.page, "Typed password")

    @allure.step("Click 'Log In' button")
    def click_login(self):
        """Clicks the 'Log In' button and waits for network idle, indicating navigation."""
        self.page.wait_for_selector(self.LOGIN_BUTTON, state="visible", timeout=30000)
        _attach_screenshot(self.page, "Before clicking Log In button")
        self.page.click(self.LOGIN_BUTTON)
        # Wait for the page to load after the login click, common for post-login redirects
        self.page.wait_for_load_state("networkidle")
        _attach_screenshot(self.page, "Clicked Log In button")

    @allure.step("Verify current URL is: {expected_url}")
    def verify_current_url(self, expected_url: str):
        """Verifies that the current page URL matches the expected URL."""
        _attach_screenshot(self.page, f"Before verifying URL to be '{expected_url}'")
        expect(self.page).to_have_url(expected_url)
        _attach_screenshot(self.page, f"Verified current URL is '{expected_url}'")

    @allure.step("Verify message: '{expected_message}' is visible")
    def verify_success_message(self, expected_message: str):
        """Verifies that the success message element is visible and contains the expected text."""
        self.page.wait_for_selector(self.SUCCESS_MESSAGE, state="visible", timeout=30000)
        _attach_screenshot(self.page, f"Before verifying message content: '{expected_message}'")
        # Use expect to assert that the element contains the text
        expect(self.page.locator(self.SUCCESS_MESSAGE)).to_contain_text(expected_message)
        _attach_screenshot(self.page, f"Verified message: '{expected_message}' is visible")


@allure.feature("viking_curve_login")
@allure.suite("Viking Pump Curve")
@allure.title("User logs in and verifies content")
def test_viking_curve_login(page: Page):
    """
    Scenario: User logs in and verifies content
    Given I navigate to "https://www.vikingpumpcurve.com/"
    When I log in with username "jraja@idexcorp.com" and password "<data.Password_2>"
    Then I should be on the "https://www.vikingpumpcurve.com/?check_logged_in=1" page
    And I should see the message "Please select operating conditions."
    """
    global _screenshot_counter
    _screenshot_counter = 1 # Reset the screenshot counter for this specific test function

    login_page = VikingPumpCurveLoginPage(page)

    # Given I navigate to "https://www.vikingpumpcurve.com/"
    login_page.navigate()

    # When I log in with username "jraja@idexcorp.com" and password "<data.Password_2>"
    username = "jraja@idexcorp.com"
    # Read sensitive password from the data file
    password = _read_data_from_path("<data.Password_2>")

    login_page.type_username(username)
    login_page.type_password(password)
    login_page.click_login()

    # Then I should be on the "https://www.vikingpumpcurve.com/?check_logged_in=1" page
    login_page.verify_current_url(VikingPumpCurveLoginPage.EXPECTED_LOGIN_URL)

    # And I should see the message "Please select operating conditions."
    expected_message = "Please select operating conditions."
    login_page.verify_success_message(expected_message)