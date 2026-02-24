from playwright.sync_api import sync_playwright, expect
import time

def verify_dashboard(page):
    print("Verifying Dashboard...")
    page.goto("http://localhost:5173")
    # Click on Dashboard tab
    page.get_by_role("button", name="Dashboard").click()
    time.sleep(2) # Wait for animations
    page.screenshot(path="verification/dashboard.png", full_page=True)
    print("Dashboard screenshot saved.")

def verify_delete_modal(page):
    print("Verifying Delete Modal...")
    page.goto("http://localhost:5173")
    # Try Upload tab delete - it's usually easier to trigger
    page.get_by_role("button", name="Story Upload").click()
    time.sleep(1)

    # Create a dummy suite to show delete buttons
    page.get_by_title("New Suite").click()
    page.get_by_placeholder("New suite name").fill("Test Verification Suite")
    page.get_by_role("button", name="Create").click()
    time.sleep(1)

    # Click delete suite to trigger ConfirmationModal
    page.get_by_title("Delete Suite").click()
    time.sleep(1)

    # Take screenshot of the modal
    page.screenshot(path="verification/delete_modal.png")
    print("Delete Modal screenshot saved.")

if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Set viewport to a standard desktop size
        page = browser.new_page(viewport={'width': 1280, 'height': 800})
        try:
            verify_dashboard(page)
            verify_delete_modal(page)
        except Exception as e:
            print(f"Error: {e}")
            # Take error screenshot
            page.screenshot(path="verification/error.png")
        finally:
            browser.close()
