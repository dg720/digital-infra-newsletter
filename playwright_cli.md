# Playwright CLI Guide for AI Agents

This document provides instructions for AI agents (Claude, Gemini, etc.) on how to utilize the Playwright CLI to debug, test, and verify web applications within this project.

**Assumption:** The `playwright` command is available in the system PATH.

## 🔍 Core Capabilities for AI Workflows

### 1. Visual Verification (Screenshots)
Use screenshots to verify UI states, layout fixes, or error messages without needing a full test suite.

```bash
# Basic screenshot
playwright screenshot <url> <output_filename.png>

# Full page screenshot (useful for long content)
playwright screenshot <url> <output_filename.png> --full-page

# Wait for network idle (useful for SPAs)
playwright screenshot <url> <output_filename.png> --wait-for-timeout 3000
```

**AI Workflow:**
1.  Start the web server (e.g., `npm run dev` or `python main.py`).
2.  Capture a screenshot: `playwright screenshot http://localhost:3000 verification.png`.
3.  Analyze the image artifact to confirm the "Happy Path" or identify visual bugs.

### 2. Ad-hoc Page Inspection
To inspect a page's HTML or check for console errors via CLI output (if supported) or simply to check connectivity and title.

```bash
# Print the page HTML to stdout
playwright open <url> --print-content
```

### 3. Generating Test Scaffolding (Codegen)
If you need to write a strictly typed test but don't know the selectors, use `codegen`. 
*Note: This opens a GUI window, so it may be less useful for non-interactive agents, but useful to recommend to the USER.*

```bash
playwright codegen <url>
```

### 4. Running Tests
Run end-to-end tests using the configured test runner (pytest-playwright).

```bash
# Run all tests
pytest

# Run a specific test file
pytest tests/test_e2e.py

# Run in headed mode (visible browser) - useful if User is watching
pytest --headed

# Run with Slow Motion (easier to follow)
pytest --slowmo 1000
```

## 🐛 Debugging Strategies

### "It works locally but not in the test"
1.  **Trace Viewer**: Run tests with tracing on.
    ```bash
    pytest --tracing=on
    ```
2.  **View Trace**:
    ```bash
    playwright show-trace test-results/trace.zip
    ```

### "I need to see what's happening"
Ask the user to run the specific test command with `--headed` so they can see the browser automation in action.

## 📋 Example: Verifying a Local Deployment

1.  **Ensure Server is Running**:
    ```bash
    # (In a separate terminal)
    npm run dev
    ```

2.  **Snapshot the Home Page**:
    ```bash
    playwright screenshot http://localhost:3000 home_page.png
    ```

3.  **Snapshot a specific route**:
    ```bash
    playwright screenshot http://localhost:3000/dashboard dashboard.png --full-page
    ```

For more details, refer to the [official Playwright CLI documentation](https://playwright.dev/docs/test-cli).
