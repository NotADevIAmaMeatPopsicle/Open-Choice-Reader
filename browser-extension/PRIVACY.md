# Open Choice Reader browser extension, privacy policy

Last updated: 2026-09-11

## The short version

The extension collects nothing, sends nothing to us, and has no servers of ours to
send anything to. The only machine it talks to is the Open Choice Reader server whose
address you type into it yourself.

## What it stores

One value, in your browser's local extension storage: the server address you entered.
It stays on your machine and is used to know where to send pages. Clearing the
extension's data or removing the extension removes it.

## What it sends, and where

When you ask it to read or import something, it sends the text of the current page, or
the text you highlighted, along with the page title and URL, to the server address you
configured. That is normally `http://127.0.0.1:8000`, which is your own computer.

Nothing is sent anywhere else. There is no analytics, no telemetry, no crash reporting
and no third-party service of any kind in the extension.

## Permissions and why each one exists

- `activeTab` and `scripting`: to read the text of the page you are currently on, only
  at the moment you click a button or use the right-click menu.
- `contextMenus`: to add the right-click entries for reading and importing.
- `storage`: to remember your server address.
- `tabs`: to know the title and URL of the page you are sending, and to open the reader
  when you ask it to.
- `http://127.0.0.1/*` and `http://localhost/*`: the default local server addresses.
- Optional `http://*/*` and `https://*/*`: requested only if you point the extension at
  a server on another address, and only when you do.

## Who to contact

Open an issue at https://github.com/NotADevIAmaMeatPopsicle/Open-Choice-Reader/issues
