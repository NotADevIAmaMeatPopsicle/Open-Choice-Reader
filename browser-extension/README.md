# Open Choice Reader Browser Extension

This browser extension targets Chrome, Edge, Brave, Arc, and other Chromium-based browsers. It sends the current page or highlighted text to an Open Choice Reader server you configure.

## What it does

- Right-click any normal webpage to read or import it immediately
- Right-click highlighted text to start from that selection
- Read the full current page immediately
- Read only the highlighted selection immediately
- Import the full page into the library without starting playback
- Import only the highlighted selection into the library
- Choose a live voice before opening the reader
- Override playback speed in `0.05x` increments for the handoff session

Selecting text on the page is the current "start reading here" workflow.

## Load it in a Chromium-based browser

1. Open your browser's extension management page, for example `chrome://extensions` or `edge://extensions`
2. Turn on `Developer mode`
3. Click `Load unpacked`
4. Choose the repository's `browser-extension` folder.

## First-run setup

1. Open the extension popup
2. Enter the server URL, such as `http://127.0.0.1:8000` for a local installation.
3. Click `Save host`
4. Navigate to any readable webpage, then reopen the popup

## Fastest workflow

1. Highlight the sentence or paragraph where you want reading to begin
2. Right-click
3. Choose one of:
   - `Read selection in Open Choice Reader`
   - `Import selection to Open Choice Reader`

If you want the whole article instead, right-click the page without selecting text and use the page actions.

## Notes

- The extension talks directly to the server URL you configure
- The extension reuses your signed-in Open Choice Reader browser session when it can
- If you are signed out, the extension will send you back to the login shell on the saved host so you can sign in first
- Remote servers should use HTTPS and must explicitly allow this extension's origin through the server CORS configuration
- The selected-text flow imports a stable snapshot of the highlighted text into the library, then opens the reader on that imported document
- The full-page flow uses the existing URL/article import pipeline already built into Open Choice Reader
- The popup still gives you live narrator choice and a one-off playback-speed override before opening the reader
- Firefox and Safari do not currently have a packaged extension build for this workflow
