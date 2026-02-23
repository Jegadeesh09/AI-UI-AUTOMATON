import pytest
import os
from datetime import datetime

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    pytest_html = item.config.pluginmanager.getplugin('html')
    outcome = yield
    report = outcome.get_result()
    extra = getattr(report, 'extra', [])

    if report.when == 'call':
        # Always check for screenshots
        # We look for screenshots taken during the test
        # In Playwright, we can get the page from the fixture
        if 'page' in item.funcargs:
            page = item.funcargs['page']
            story_id = item.nodeid.split("::")[0].split("/")[-1].replace("test_", "").replace(".py", "")
            # Try to get suite from environment
            suite = os.environ.get("CURRENT_SUITE", "Default")
            
            timestamp = datetime.now().strftime('%H%M%S')
            screenshot_dir = f"backend/storage/suites/{suite}/reports/{story_id}/screenshots"
            os.makedirs(screenshot_dir, exist_ok=True)
            screenshot_path = os.path.join(screenshot_dir, f"scenario_{timestamp}.png")
            
            page.screenshot(path=screenshot_path)
            
            # Attach to HTML report
            # The path in the HTML should be relative to the report file
            # Report is at backend/storage/suites/{suite}/reports/{story_id}/extent-report.html
            # Screenshot is at backend/storage/suites/{suite}/reports/{story_id}/screenshots/scenario_{timestamp}.png
            # So relative path is 'screenshots/scenario_{timestamp}.png'
            rel_path = f"screenshots/scenario_{timestamp}.png"
            if pytest_html:
                extra.append(pytest_html.extras.image(rel_path))
    
    report.extra = extra

