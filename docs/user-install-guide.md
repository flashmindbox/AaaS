# AaaS Companion — User Installation Guide

An easy-to-follow guide for installing and using AaaS Companion on your
computer. No technical knowledge required.

---

## What is AaaS Companion?

AaaS Companion is a browser add-on. Once you install it, a small floating
**ଅ** button appears on **every** website you visit. Click it and a panel
opens with five features:

| Feature | What it does |
|---|---|
| **🔊 Read this page** | Reads the page aloud in Odia, Hindi, or English |
| **🌐 Translate this page** | Translates the page to Odia in place (Google Translate) |
| **🎙️ Speak to fill forms** | Speak into your microphone, text appears in the form field |
| **Dyslexia mode** | Wider letter spacing and softer contrast — easier to read |
| **Hover to speak** | Move your mouse over anything on the page; it's read aloud |

This guide walks you through installing the extension and using it for
the first time.

---

## Before you start

You will need:

- **Google Chrome** (version 111 or newer) — or —
  **Microsoft Edge** (version 111 or newer, already on all Windows 10/11)
- **~300 MB of free disk space** for the unzipped extension folder
- **A few minutes** for the one-time install

You should have received a file named:

```
AaaS-Companion-Extension-v0.2.1.zip
```

If you don't have this file yet, ask the person who shared the extension
with you (email, WhatsApp, Drive, USB stick — anywhere they sent it).

---

## Step 1 — Unzip the file

1. Find the `.zip` file wherever it was saved (usually your
   **Downloads** folder).
2. **Move it out of Downloads first.** Put it somewhere permanent like
   your **Desktop** or **Documents** folder. The browser will read from
   this folder every time you use the extension — if you delete the
   folder, the extension stops working.
3. Right-click the zip → **Extract All…** → click **Extract**.
4. You'll now have a folder named `AaaS-Companion` with files inside
   (`manifest.json`, `widget.js`, an `icons` folder, and more).

**Keep this folder where it is.** Don't rename or move it after installing.

---

## Step 2 — Open the Extensions page

### If you're using Google Chrome:

1. Open Chrome.
2. Click the address bar at the top.
3. Type this exactly and press **Enter**:
   ```
   chrome://extensions
   ```

### If you're using Microsoft Edge:

1. Open Edge.
2. Click the address bar at the top.
3. Type this exactly and press **Enter**:
   ```
   edge://extensions
   ```

Either way, you'll land on a page titled **"Extensions"** that shows
any add-ons you already have.

---

## Step 3 — Turn on Developer mode

Look at the **top-right corner** of the Extensions page. You'll see a
toggle switch labelled **"Developer mode"**.

**Click the toggle** so it turns **blue / on**.

Three new buttons appear: **Load unpacked**, **Pack extension**,
**Update**. You only need the first one.

> **Don't worry about the warning that says "Developer mode extensions"
> at the top.** That's normal when you install from a folder instead of
> the Chrome Web Store. You can ignore it.

---

## Step 4 — Load the extension

1. Click **Load unpacked**.
2. A file picker opens. Navigate to wherever you unzipped the extension
   in Step 1. For example:
   ```
   C:\Users\<your name>\Desktop\AaaS-Companion
   ```
3. **Click the `AaaS-Companion` folder ONCE to highlight it** — do not
   double-click into it.
4. Click **Select Folder** (bottom-right of the dialog).

A new card should appear on the Extensions page:

```
┌──────────────────────────────────────────────┐
│ ଅ  AaaS Accessibility Companion (Odisha)     │
│    An Odia-first accessibility assistant…    │
│    ID: <long random string>                  │
│    [Details]  [Remove]              ◯ ON/OFF │
└──────────────────────────────────────────────┘
```

If instead you see a red "**Failed to load extension**" error, you
probably picked the wrong folder. Go back to step 4 and make sure you
selected the folder that contains `manifest.json` (the `AaaS-Companion`
folder directly, not a subfolder like `icons/`).

---

## Step 5 — Pin the toolbar icon

Look for the **ଅ** icon in your browser's toolbar (top of the window).
If you don't see it:

1. Click the **puzzle-piece icon** (🧩) next to the address bar.
2. A list of installed extensions drops down.
3. Find **AaaS Companion** and click the **pin icon** (📌) next to it.

The **ଅ** icon should now live permanently in your toolbar.

---

## Step 6 — Test it

1. Open any website — try `https://www.odisha.gov.in` or any news site.
2. Look at the **bottom-right corner** of the page. You should see a
   small floating **ଅ** button.
3. Click it → the accessibility panel slides up.
4. Click **🔊 Read this page** → the page starts reading aloud in Odia.

**That's it — you're installed.**

---

## Configuring the extension

Click the **ଅ** icon in the **browser toolbar** (not the floating one on
the page) to open the settings popup.

### Enable on all pages

Keep this **on**. Turn off to silence the extension on every site
without uninstalling it.

### On-device mode (experimental · offline)

- **Off** (default): The extension sends text to an AaaS gateway server
  for speech work. Requires that server to be running.
- **On**: Everything runs inside your browser. No server needed. Works
  even when your laptop has no internet connection.

The **first** time you read aloud in each language after turning
on-device mode on, there's a 3–5 second warm-up while the speech model
loads into memory. After that, reading is nearly instant.

Turn this **on** if you're using the extension without the AaaS server
running. Turn it **off** if you're connected to an AaaS demo server and
want the "original" voices.

### Gateway URL

The address where your AaaS server is running. The default is the
bundled USB demo (`http://127.0.0.1:8000`). Ignore this unless you're
running an AaaS server. The "Translate" button uses Google and doesn't
need this.

### Default language

- **Auto** (recommended): detects the page's language from its `<html
  lang="…">` attribute.
- Pick a specific language to override auto-detection on pages with
  wrong or missing language tags.

Click **Save** after changing anything, then reload any open tabs for
the change to take effect.

---

## Using the extension day-to-day

### Read a page aloud

1. Open any website.
2. Click the floating **ଅ** → **Read this page**.
3. The whole page is read aloud in the language you picked.
4. Press **Space** to pause / resume, **→** to skip forward, **←** to
   replay, **Esc** to stop.

### Translate a page to Odia

1. Click the floating **ଅ** → **Translate this page → Odia**.
2. Watch as each block of text changes from English/Hindi to Odia
   in place. Takes about 20–60 seconds for a full page.
3. **To revert**: just reload the page (Ctrl+R or F5).

### Speak instead of type

1. Click inside any form field (e.g. a search box).
2. Click the floating **ଅ** → **Speak (fill by voice)**.
3. When your browser asks for microphone permission, click **Allow**.
4. Speak clearly — your words appear in the form field when you stop.

### Dyslexia mode

Click **Dyslexia mode** in the panel. Letters widen and colours
soften. Click again to revert.

### Hover to speak

Turn this on in the panel. Now move your mouse over any heading, link,
paragraph, or button — it's read aloud as your mouse arrives. Useful
for quickly scanning a long page with your ears.

---

## Common problems

### "The ଅ button doesn't show up on this page"

- Reload the page once (**Ctrl+R** or **F5**).
- A small number of sites (some banks, some government portals) block
  all injected scripts through a strict security policy. Nothing the
  extension can do about those.
- If it's missing on every page: go back to `chrome://extensions` and
  make sure the toggle on the AaaS Companion card is **on**.

### "Nothing speaks when I click Read this page"

- Check your system volume and that your laptop isn't muted.
- Try a different page to rule out a site-specific issue.
- If you have **On-device mode off**: you need the AaaS gateway server
  running. Either start it, or turn **On-device mode on** in the popup
  and reload the page.

### "The microphone button gives an error"

- Your browser needs microphone permission for the site. Look for a
  microphone icon in the address bar and click **Allow**.
- Microphone only works on sites that use **HTTPS** (the little padlock
  in the address bar). Rare HTTP-only pages won't work.

### "Translate button doesn't work / shows zero change"

- Needs internet connection — Google Translate is a cloud service.
- If you hit Google's rate limit after many translations in a row, wait
  a minute and try again.
- Some pages re-render their text (shopping sites, social media
  feeds) — translated text gets overwritten by the site's own JavaScript
  when new content loads.

### "I got an error after loading unpacked"

Read the red error box on the extension card — it usually says exactly
what's wrong:

- **"Default locale was specified, but _locales subtree is missing"**
  → you have an older version. Update to v0.2.1 or later.
- **"Manifest file is missing or unreadable"**
  → you picked a subfolder instead of the `AaaS-Companion` folder
  itself. Redo Step 4.
- **"Could not load extension from …"**
  → the folder you selected was moved or deleted since install. Pick
  its new location via **Remove** → **Load unpacked** again.

---

## Updating to a new version

When you receive a new zip:

1. **Unzip it over the old folder** (or to a fresh folder — both work).
2. Go to `chrome://extensions`.
3. Click the **↻ reload** icon on the AaaS Companion card.

The new version takes effect on your next page reload. No need to
remove and re-add.

---

## Uninstalling

1. Go to `chrome://extensions` (or `edge://extensions`).
2. Find the AaaS Companion card.
3. Click **Remove** → confirm.
4. Delete the unzipped folder from your computer if you no longer need
   it.

---

## Getting help

If something doesn't work and this guide didn't cover it:

- Press **F12** on any page to open Developer Tools.
- Click the **Console** tab.
- Look for lines starting with `[AaaS]` — those are messages from the
  extension.
- Take a screenshot and share it with the AaaS Companion team.

---

*AaaS Companion is a project by **Team SUBARNAREKHA**, built for the
Smart Odisha Hackathon '25. It is free and open-source under the
Apache 2.0 licence. See `LICENSE` in the project repository for
details.*
