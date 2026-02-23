import os
import json
from datetime import datetime

def generate_extent_report(json_report_path, output_path, story_id, suite="Default"):
    try:
        with open(json_report_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error loading JSON report: {e}")
        return

    summary = data.get("summary", {})
    passed = summary.get("passed", 0)
    failed = summary.get("failed", 0) + summary.get("error", 0)
    skipped = summary.get("skipped", 0)
    total = passed + failed + skipped
    duration = round(summary.get("duration", 0), 2)
    
    timestamp = datetime.now().strftime("%b %d, %Y %I:%M:%S %p")
    
    tests = data.get("tests", [])
    scenarios = []
    for t in tests:
        name = t.get("nodeid", "").split("::")[-1].replace("test_", "").replace("_", " ")
        status = t.get("outcome", "unknown")
        duration_test = round(t.get("setup", {}).get("duration", 0) + t.get("call", {}).get("duration", 0) + t.get("teardown", {}).get("duration", 0), 2)
        
        # Look for screenshots in metadata or filesystem
        # In pytest-json-report, extras might be under metadata or within stages
        screenshots = []
        # Check call stage for extras
        call_stage = t.get("call", {})
        extras = call_stage.get("extra", [])
        for extra in extras:
            if isinstance(extra, dict) and extra.get("content_type", "").startswith("image"):
                screenshots.append(extra.get("content"))
            elif isinstance(extra, str) and (extra.endswith(".png") or extra.endswith(".jpg")):
                screenshots.append(extra)

        # If no screenshots in JSON, check the directory
        if not screenshots:
            screenshot_dir = os.path.join(os.path.dirname(json_report_path), "screenshots")
            if os.path.exists(screenshot_dir):
                files = sorted([f for f in os.listdir(screenshot_dir) if f.endswith(".png")])
                # This is a bit of a guess which screenshot belongs to which scenario if there are many
                # But usually there's one per scenario in this setup
                if files:
                    # Try to match by timestamp or just take the latest if one scenario
                    screenshots.append(f"screenshots/{files[-1]}")

        scenarios.append({
            "name": name,
            "status": status,
            "duration": duration_test,
            "screenshots": screenshots
        })

    scenario_html = ""
    for s in scenarios:
        status_class = "badge-pass" if s['status'] == 'passed' else "badge-fail"
        icon = "✅" if s['status'] == 'passed' else "❌"
        
        screenshot_html = ""
        for img in s['screenshots']:
            screenshot_html += f"""
            <div style="margin-top: 15px;">
                <p style="font-size: 12px; color: #888; margin-bottom: 5px;">Scenario Screenshot:</p>
                <img src="{img}" style="max-width: 100%; border: 1px solid #444; border-radius: 4px; cursor: pointer;" onclick="window.open(this.src)">
            </div>
            """

        scenario_html += f"""
                <div class="scenario-item" style="flex-direction: column; align-items: flex-start;">
                    <div style="display: flex; justify-content: space-between; width: 100%; align-items: center; margin-bottom: 10px;">
                        <div>
                            <span class="scenario-name">{icon} {s['name']}</span>
                            <div style="font-size: 11px; color: #777; margin-top: 4px;">Duration: {s['duration']}s</div>
                        </div>
                        <span class="badge {status_class}">{s['status'].upper()}</span>
                    </div>
                    {screenshot_html}
                </div>
        """

    story_status = "PASS" if failed == 0 else "FAIL"
    status_color_class = "status-pass" if failed == 0 else "status-fail"

    # HTML Template
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
    <title>Extent Report - {story_id}</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/extent-framework/extent-github-cdn@d6562a79075e061305ccfdb82f01e5e195e2d307/py/skin/default-style.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ background-color: #1a1a1a; color: #e0e0e0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }}
        .card {{ background-color: #252525; border: 1px solid #333; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }}
        .card-header {{ background-color: #2d2d2d; border-bottom: 1px solid #333; padding: 10px 20px; font-weight: bold; }}
        .status-pass {{ color: #2ecc71; }}
        .status-fail {{ color: #e74c3c; }}
        .status-skip {{ color: #3498db; }}
        .header {{ background-color: #000; padding: 15px 30px; display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #444; }}
        .metrics-container {{ display: flex; gap: 20px; padding: 20px; flex-wrap: wrap; }}
        .metric-card {{ flex: 1; min-width: 250px; text-align: center; padding: 20px; }}
        .chart-container {{ width: 150px; height: 150px; margin: 0 auto 15px; }}
        .scenario-list {{ padding: 20px; }}
        .scenario-item {{ background-color: #2d2d2d; border: 1px solid #444; border-radius: 4px; padding: 15px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; }}
        .scenario-name {{ font-weight: 500; font-size: 16px; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
        .badge {{ padding: 5px 10px; border-radius: 20px; font-size: 12px; font-weight: bold; }}
        .badge-pass {{ background-color: rgba(46, 204, 113, 0.2); color: #2ecc71; border: 1px solid #2ecc71; }}
        .badge-fail {{ background-color: rgba(231, 76, 60, 0.2); color: #e74c3c; border: 1px solid #e74c3c; }}
    </style>
</head>
<body>
    <div class="header">
        <div style="font-size: 20px; font-weight: bold;">AI UI Automation Test Report</div>
        <div style="font-size: 14px; color: #aaa;">{timestamp}</div>
    </div>

    <div style="padding: 20px;">
        <div class="card">
            <div class="card-header">Dashboard</div>
            <div class="metrics-container">
                <div class="metric-card">
                    <div class="chart-container"><canvas id="scenariosChart"></canvas></div>
                    <div style="font-size: 14px;"><b>Scenarios</b></div>
                    <div style="font-size: 12px; margin-top: 5px;">
                        <span class="status-pass">{passed} passed</span>, 
                        <span class="status-fail">{failed} failed</span>
                    </div>
                </div>
                <div class="metric-card">
                    <div style="font-size: 48px; font-weight: bold; margin-bottom: 10px;" class="{status_color_class}">
                        {story_status}
                    </div>
                    <div style="font-size: 14px;"><b>Story Status</b></div>
                    <div style="font-size: 12px; margin-top: 5px; color: #888;">{story_id}</div>
                </div>
                <div class="metric-card">
                    <div style="font-size: 36px; font-weight: bold; margin-bottom: 10px; color: #3498db;">{duration}s</div>
                    <div style="font-size: 14px;"><b>Total Duration</b></div>
                    <div style="font-size: 12px; margin-top: 5px; color: #888;">Suite: {suite}</div>
                </div>
            </div>
        </div>

        <div class="card">
            <div class="card-header">Scenarios</div>
            <div class="scenario-list">
                {scenario_html}
            </div>
        </div>
    </div>

    <div class="footer">
        Generated by AI UI Automation Agent
    </div>

    <script>
        const ctxScenarios = document.getElementById('scenariosChart').getContext('2d');
        new Chart(ctxScenarios, {{
            type: 'doughnut',
            data: {{
                labels: ['Passed', 'Failed', 'Skipped'],
                datasets: [{{
                    data: [{passed}, {failed}, {skipped}],
                    backgroundColor: ['#2ecc71', '#e74c3c', '#3498db'],
                    borderWidth: 0
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{ legend: {{ display: false }} }},
                cutout: '70%'
            }}
        }});
    </script>
</body>
</html>
    """
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"Extent report generated at {output_path}")
