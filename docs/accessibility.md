# Accessibility Notes

This document collects implementation notes, manual testing guidance, and known platform-specific behavior for TimePoll accessibility.

It is intentionally practical. The focus is not only on WCAG-style mechanics, but also on whether the main workflows are realistic for keyboard and screen-reader users.

## Scope

TimePoll is designed around these keyboard-first expectations:

- The main views can be reached and used without a mouse.
- Focus should move to the start of the newly opened view.
- Dialogs should trap focus and return it when they close.
- Forms should move focus to the first invalid field when validation fails.
- Poll navigation should preserve the user's place when returning to a previous view.

## Current Coverage

The browser test suite includes:

- axe accessibility smoke tests for the main views and several error states
- keyboard workflow tests for login, poll creation, poll editing, timezone listboxes, bulk menus, vote controls, profile controls, and focus restoration

The current Playwright browser suite runs on Chromium, not Safari. Safari-specific behavior must therefore be verified manually.

Relevant automated coverage lives primarily in [polls/tests_browser.py](../polls/tests_browser.py) and [polls/tests_browser_storyboard.py](../polls/tests_browser_storyboard.py).

## Keyboard Workflow Summary

### Home / poll list

The home view is keyboard-usable in browsers where `Tab` reaches links and buttons normally.

Expected behavior:

- The top bar contains the `TimePoll` home link, language selector, and authentication controls.
- The poll list view contains a `Create new poll` button and one large button per poll row.
- Opening a poll moves focus to the poll details heading.
- Returning to the list moves focus back to the poll button that opened the poll.

Important limitation:

- The poll list is linear. It is navigated with `Tab` / `Shift-Tab`, not with arrow-key list navigation.
- This is workable for short and medium-sized lists, but becomes slower as the number of polls grows.

### Create poll

The create form is built mostly from native controls:

- text input
- textarea
- text input with validation
- timezone combobox with suggestion listbox
- date inputs
- hour selects
- weekday checkboxes
- submit and cancel buttons

Expected behavior:

- Opening the create view moves focus to the title field.
- The timezone field supports `ArrowDown`, `ArrowUp`, `Home`, `End`, `Enter`, `Escape`, and `Tab`.
- Validation errors are announced visually and focus returns to the first invalid field on submit.

### Edit poll

The edit form follows the same structure as create, with additional schedule-conflict rules and timezone change confirmation.

Expected behavior:

- Opening edit mode moves focus to the edit title field.
- The timezone field supports the same keyboard interaction as the create form.
- If changing timezone would auto-adjust the schedule, a confirmation dialog opens.
- The confirmation dialog traps focus and restores focus to the timezone field when cancelled.

### Dialogs

Authentication and timezone confirmation dialogs are expected to:

- move focus to the first interactive control when opened
- cycle focus with `Tab` and `Shift-Tab`
- close on `Escape`
- restore focus to the triggering control when closed without completing the action

## Safari and macOS Behavior

This section matters because Safari and macOS can change whether `Tab` reaches TimePoll's controls at all.

### Why TimePoll can seem "stuck" on the language selector in Safari

On the home page, most primary actions are links or buttons:

- `TimePoll` is a link
- `Login`, `Logout`, `Create new poll`, and poll rows are buttons
- the language control is a native `select`

In Safari's default keyboard behavior, `Tab` may only move to the next text field or pop-up menu on a web page. In practice, this means the language selector can receive focus while nearby buttons and links do not.

This can make the page appear to "loop" between:

- the language selector
- no obvious web-page control

For a keyboard-only user, that means the page may appear unusable even though the HTML itself uses semantic links and buttons.

### Safari-specific workaround

Safari has a setting named `Press Tab to highlight each item on a webpage`.

When that setting is off:

- `Tab` highlights the next field or pop-up menu
- `Option-Tab` highlights the next field, pop-up menu, or clickable item

When that setting is on:

- plain `Tab` highlights each item on the page
- Safari swaps the default `Tab` / `Option-Tab` behavior accordingly

For TimePoll, enabling this Safari setting is strongly recommended.

### macOS-wide keyboard settings

macOS also has system-level keyboard navigation settings that affect focus movement:

- `Keyboard navigation` in Keyboard settings enables moving focus between controls with `Tab` and `Shift-Tab`
- `Full Keyboard Access` in Accessibility > Keyboard provides broader keyboard navigation across macOS

These settings help, but Safari's own webpage tabbing behavior is still important for TimePoll because the home page relies heavily on buttons and links rather than only text inputs.

### VoiceOver note

On macOS, `Tab` is not the only navigation model used by assistive technology users. Apple documents that VoiceOver users often navigate with VoiceOver commands rather than relying on `Tab` alone.

This means:

- TimePoll still needs correct semantics, headings, labels, and focus handling
- but a manual "Tab only" check in Safari is not a complete proxy for VoiceOver usability

## Manual Test Guidance

When testing keyboard access manually, test at least these combinations:

- Chromium-based browser with normal `Tab` navigation
- Safari with default settings
- Safari with `Press Tab to highlight each item on a webpage` enabled
- macOS with and without broader keyboard navigation enabled

For Safari, explicitly verify these workflows:

- Can `Tab` reach `Login`?
- Can `Tab` reach `Create new poll`?
- Can `Tab` reach the first poll row?
- After opening a poll, does focus move to the details heading?
- After returning from a poll, does focus return to the same list item?

If the answer is "no" in Safari default settings but "yes" after enabling webpage tab highlighting, the issue is platform behavior rather than a broken DOM focus order inside TimePoll itself.

## Known Practical Risk

The most important current accessibility caveat is:

- TimePoll is keyboard-workable in browsers that tab to links and buttons normally.
- On Safari/macOS default settings, the home page may appear non-functional with plain `Tab` because focus can skip most primary actions.

This should be treated as a documented platform caveat and checked in manual QA.

## References

- [Apple Support: Keyboard shortcuts and gestures in Safari on Mac](https://support.apple.com/en-euro/guide/safari/cpsh003/mac)
- [Apple Support: Change Advanced settings in Safari on Mac](https://support.apple.com/guide/safari/advanced-ibrw1075/mac)
- [Apple Support: Keyboard settings on Mac](https://support.apple.com/en-asia/guide/mac-help/-kbdm162/mac)
- [Apple Support: Navigate your Mac using Full Keyboard Access](https://support.apple.com/guide/mac-help/mchlc06d1059/mac)
- [Apple Support: Use VoiceOver and the Tab key to navigate on Mac](https://support.apple.com/en-afri/guide/voiceover/vo2753/mac)
