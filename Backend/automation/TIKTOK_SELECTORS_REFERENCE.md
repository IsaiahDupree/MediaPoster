# TikTok DOM Selector Reference Guide

> Source: ChatGPT conversation on selecting elements for TikTok/Instagram automation

---

## Overview

TikTok uses auto-generated class names like `css-XXXX-7937d88b--DivSomething`. The hash changes, but the component name (`DivSomething`) is usually stable.

**Pattern:**
```css
/* Brittle (avoid) */
.css-11fh2ar-7937d88b--SectionActionBarContainer.e12arnib0

/* Stable (use this) */
[class*="SectionActionBarContainer"]
```

---

## Text Input Fields

TikTok uses `contenteditable="true"` divs instead of `<input>` or `<textarea>`.

### Get Active Text Field
```javascript
function getActiveTextField() {
  const el = document.activeElement;
  if (!el) return null;

  const tag = el.tagName;
  const type = (el.type || '').toLowerCase();

  const isTextInput =
    tag === 'TEXTAREA' ||
    (tag === 'INPUT' && ['text', 'search', 'email', 'url', 'tel', 'password'].includes(type));

  const isEditableDiv = el.isContentEditable === true;

  if (isTextInput || isEditableDiv) {
    return el;
  }
  return null;
}

// Usage:
const field = getActiveTextField();
const value = field?.value !== undefined ? field.value : field?.innerText ?? '';
```

### Get Selected Text
```javascript
function getSelectedText() {
  const selection = window.getSelection();
  return selection ? selection.toString() : '';
}
```

---

## Comment Section Selectors

### Comment Footer (Input + Post Button)
```javascript
// Stable selector for comment footer
const commentFooter = document.querySelector(
  '#main-content-homepage_hot [class*="DivCommentFooter"]'
);

// Comment input field
const input = commentFooter?.querySelector('[contenteditable="true"]');

// Post button
const postBtn = commentFooter?.querySelector('[class*="DivPostButton"]');
```

### Get Comment Text & Post
```javascript
function getCommentContext() {
  const footer = document.querySelector(
    '#main-content-homepage_hot [class*="DivCommentFooter"]'
  );
  if (!footer) return { text: '', canPost: false };

  const input = footer.querySelector('[contenteditable="true"]');
  const postBtn = footer.querySelector('[class*="DivPostButton"]');

  const text = input?.innerText.trim() ?? '';
  const canPost = !!postBtn && text.length > 0;

  return { text, canPost };
}

function postCurrentComment() {
  const footer = document.querySelector(
    '#main-content-homepage_hot [class*="DivCommentFooter"]'
  );
  if (!footer) return false;

  const postBtn = footer.querySelector('[class*="DivPostButton"]');
  if (!postBtn) return false;

  postBtn.click();
  return true;
}
```

### Extract All Comments
```javascript
// All comment text spans
const commentNodes = document.querySelectorAll(
  '#main-content-homepage_hot [class*="DivCommentContentWrapper"] > span'
);

const comments = [...commentNodes].map(el => el.innerText.trim());
```

### First Comment Only
```javascript
const firstComment = document.querySelector(
  '#main-content-homepage_hot [class*="DivCommentContentWrapper"] > span'
)?.innerText.trim() ?? '';
```

---

## DM (Direct Messages) Selectors

### DM Input Bar
```javascript
// The whole input + send bar
const bar = document.querySelector(
  '#main-content-messages [class*="DivMessageInputAndSendButton"]'
);

// Message input field
const input = bar?.querySelector('[contenteditable="true"], textarea, input[type="text"]');

// Get current text
const currentText = input?.innerText !== undefined
  ? input.innerText.trim()
  : input?.value?.trim() ?? '';
```

### DM Helper Functions
```javascript
function getTikTokDMText() {
  const bar = document.querySelector(
    '#main-content-messages [class*="DivMessageInputAndSendButton"]'
  );
  if (!bar) return '';

  const input = bar.querySelector('[contenteditable="true"], textarea, input[type="text"]');
  if (!input) return '';

  return input.innerText !== undefined
    ? input.innerText.trim()
    : (input.value ?? '').trim();
}

function clickTikTokDMSend() {
  const bar = document.querySelector(
    '#main-content-messages [class*="DivMessageInputAndSendButton"]'
  );
  if (!bar) return false;

  const btn = bar.querySelector('button, [role="button"], [class*="Send"]');
  if (!btn) return false;

  btn.click();
  return true;
}
```

### Get Last DM Message
```javascript
function getLastTikTokDM() {
  const chatMain = document.querySelector(
    '#main-content-messages [class*="DivChatMain"]'
  );
  if (!chatMain) return '';

  const rows = chatMain.querySelectorAll(':scope > div > div');
  if (!rows.length) return '';

  const lastRow = rows[rows.length - 1];
  const textNode = lastRow.querySelector('[data-e2e*="message"], [class*="Text"], div div div div') ?? lastRow;

  return textNode.innerText?.trim?.() ?? '';
}
```

---

## Navigation Selectors

### Side Nav Buttons
```javascript
// All nav buttons in the left sidebar
const navButtons = document.querySelectorAll(
  '#app [class*="DivMainNavContainer"] a button'
);

// Click 7th nav item (index 6)
const targetButton = navButtons[6];
targetButton?.click();

// All nav icons
const navIcons = document.querySelectorAll(
  '#app [class*="DivMainNavContainer"] .TUXButton-iconContainer svg'
);
```

---

## AppleScript Integration

### Run JavaScript in Safari
```applescript
set js to "document.querySelector('#main-content-homepage_hot [class*=\"DivCommentFooter\"]')?.innerText"

tell application "Safari"
    do JavaScript js in front document
end tell
```

### Click Element via AppleScript
```applescript
set js to "
  const footer = document.querySelector('#main-content-homepage_hot [class*=\"DivCommentFooter\"]');
  const postBtn = footer?.querySelector('[class*=\"DivPostButton\"]');
  if (postBtn) postBtn.click();
"

tell application "Safari"
    do JavaScript js in front document
end tell
```

---

## Playwright Integration

### Comments
```javascript
// Get all comment texts
const allComments = await page.locator(
  '#main-content-homepage_hot [class*="DivCommentContentWrapper"] > span'
).allInnerTexts();

// Click post button
await page.evaluate(() => {
  const footer = document.querySelector('#main-content-homepage_hot [class*="DivCommentFooter"]');
  const postBtn = footer?.querySelector('[class*="DivPostButton"]');
  postBtn?.click();
});
```

### DMs
```javascript
// Get DM text
const dmText = await page.evaluate(() => {
  const bar = document.querySelector('#main-content-messages [class*="DivMessageInputAndSendButton"]');
  const input = bar?.querySelector('[contenteditable="true"]');
  return input?.innerText?.trim() ?? '';
});
```

---

## Selector Simplification Pattern

1. **Copy** the long DevTools selector
2. **Identify** stable pieces:
   - Root: `#main-content-homepage_hot`, `#main-content-messages`, `#app`
   - Container: `[class*="DivCommentFooter"]`, `[class*="DivMainNavContainer"]`
3. **Replace**:
   - `css-XXXX-hash--DivSomething` → `[class*="DivSomething"]`
   - `nth-child(N)` → `querySelectorAll(...)[N-1]` or `rows[rows.length - 1]`
4. **For clicks**: Use `.closest('button, [role="button"]')` before clicking

---

## Known Stable Selectors (TikTok)

| Element | Selector |
|---------|----------|
| Comment Input | `[data-e2e="comment-input"]`, `[data-e2e="comment-text"]` |
| Comment Post Button | `[data-e2e="comment-post"]` |
| Comment Text | `[data-e2e="comment-level-1"]` |
| Comment Username | `[data-e2e="comment-username-1"]` |
| Comment Icon | `[data-e2e="comment-icon"]` |
| Like Button | `[data-e2e="like-icon"]` |
| Share Button | `[data-e2e="share-icon"]` |
| Comment Footer | `[class*="DivCommentFooter"]` |
| Comment List | `[class*="DivCommentListContainer"]` |
| DM Input Bar | `[class*="DivMessageInputAndSendButton"]` |
| DM Chat Area | `[class*="DivChatMain"]` |
| Main Nav | `[class*="DivMainNavContainer"]` |
