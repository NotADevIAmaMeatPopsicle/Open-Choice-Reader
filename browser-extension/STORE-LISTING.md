# Chrome Web Store listing pack

Everything the submission form asks for, written out so it can be pasted rather than
composed at the keyboard. The developer account and the upload itself are the only
parts left.

Build the upload package with:

    node scripts/package-extension.mjs

It writes `dist/extension/open-choice-reader-extension-<version>-chrome.zip` with
`manifest.json` at the root of the archive, which is the most common reason a first
upload is rejected. Tests and this file are excluded from the package.

## Listing fields

**Name.** Open Choice Reader

**Short description** (132 character limit, this one is 120):

    Send the page you are reading, or just the text you highlighted, to your own Open Choice Reader server to be read aloud.

**Category.** Accessibility. It is also defensible under Productivity, but the people
who need a read-aloud tool most are the ones browsing Accessibility.

**Language.** English (United States)

**Detailed description:**

    Open Choice Reader is a reading library that runs on your own machine. This
    extension is the part that lives in your browser, so anything you find on the
    web can go into it.

    Right-click a page to read it aloud immediately, or to save it into your library
    for later. Highlight a passage first and it starts from there instead. You can
    pick which local voice reads it and how fast before the reader opens.

    The extension talks to one address: the Open Choice Reader server you enter in
    its settings, which is normally your own computer at http://127.0.0.1:8000. It
    does not phone home, because there is nowhere for it to phone. Speech is
    generated on your hardware by Piper, with optional Kokoro and Qwen runtimes if
    you want better voices.

    You need a running Open Choice Reader server to use this. It is free and open
    source, Apache 2.0, and the install instructions are here:
    https://github.com/NotADevIAmaMeatPopsicle/Open-Choice-Reader

**Single purpose** (the form asks for one sentence):

    Sending the current web page or the user's text selection to a self-hosted Open
    Choice Reader server so it can be read aloud or saved to the user's library.

**Privacy policy URL:**

    https://github.com/NotADevIAmaMeatPopsicle/Open-Choice-Reader/blob/main/browser-extension/PRIVACY.md

## Permission justifications

The form asks for one per permission and rejects vague answers. These are written to be
specific about when the permission is exercised, which is what reviewers look for.

- **activeTab**: Reads the text of the page the user is currently viewing, at the moment
  they click a button in the popup or choose a right-click entry. It is never used in
  the background.
- **scripting**: Runs a single extraction function in the active tab to collect the
  page text or the current selection. No script is injected until the user asks for a
  read or an import.
- **contextMenus**: Adds the right-click entries for reading or importing a page or a
  selection, which is the extension's main workflow.
- **storage**: Stores one value, the server address the user typed in, so they do not
  have to re-enter it.
- **tabs**: Reads the title and URL of the active tab so the imported item is labelled
  correctly, and opens the reader in a new tab when the user asks.
- **Host permission for 127.0.0.1 and localhost**: The default address of the user's own
  Open Choice Reader server. This is the only destination the extension ever contacts.
- **Optional host permission for all http and https origins**: Requested at runtime, and
  only if the user points the extension at a server that is not on localhost, for
  example one elsewhere on their own network. It is not requested at install time.

**Remote code:** No. Every script in the package is in the package. No eval, no remote
script tags, no hosted modules.

**Data usage disclosures.** Answer no to every collection category. The extension sends
page text only to the address the user configured, which is their own server, and
stores only that address locally. Tick all three certifications: no selling or
transferring user data to third parties, no use or transfer unrelated to the single
purpose, and no use or transfer to determine creditworthiness or for lending.

## Screenshots

The store needs at least one at 1280x800 or 640x400. Three are prepared at 1280x800:

1. The popup, with a page selected and a local voice chosen.
2. The reader, showing where an imported page lands.
3. The library shelf.

Store icon is the 128px icon from the package, also exported at 512px.

## Not done here

- Firefox. The extension is written for Chromium and the README says so. Firefox MV3
  needs `background.scripts` instead of `background.service_worker`, so an AMO build
  means a second manifest and a round of testing in Firefox, which has not happened.
  Worth doing later, since AMO is free and this is the kind of tool its users look for.
- Edge Add-ons. The same package uploads as-is, and the account is separate from
  Chrome's.
