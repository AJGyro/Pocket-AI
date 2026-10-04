# GhostHand for Pocket AI

## Windows UI Automation Core Specification

**Project:** Pocket AI
**Automation Engine:** FlaUI + Microsoft UI Automation
**CLI:** `E:\FlaUI.Tools\flaui.exe`
**Primary Agent Brain:** Local Qwen model
**Target Platform:** Windows
**Automation Philosophy:** Semantic UI automation; no coordinate-based physical mouse control.

---

# 1. Purpose

This document defines the technical foundation for building the **GhostHand automation system** inside Pocket AI.

GhostHand is intended to allow an AI agent to understand and manipulate Windows applications through their exposed UI Automation interfaces.

The system must prioritize:

1. Semantic UI identification.
2. UI Automation control patterns.
3. Application-independent automation where possible.
4. Verification after actions.
5. Recovery when an action fails.
6. Minimal dependence on screen coordinates.
7. No physical mouse movement for normal UI operations.
8. No `SetCursorPos()`.
9. No PyAutoGUI.
10. No AutoHotkey.
11. No coordinate-driven clicking as the primary automation mechanism.

## The current CLI already exposes a substantial subset of Windows UI Automation functionality, including element discovery, properties, clicking, typing, values, selection, keyboard input, menus, scrolling, expansion, ranges, grids, tables, views, transforms, sessions, windows, recording, and batching.

# 2. The Four-Layer Architecture

GhostHand will be documented and implemented as four distinct layers.

```text
┌───────────────────────────────────────────────┐
│              QWEN AGENT / PLANNER             │
│                                               │
│ Understand task → choose action → verify      │
└───────────────────────┬───────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────┐
│             GHOSTHAND TOOL LAYER              │
│                                               │
│ find • inspect • click • type • select        │
│ scroll • expand • window • keyboard • verify  │
└───────────────────────┬───────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────┐
│              FLAUI / UI AUTOMATION            │
│                                               │
│ Elements • Properties • Patterns • Tree       │
│ Events • Windows • Controls                   │
└───────────────────────┬───────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────┐
│                WINDOWS APPLICATION            │
│                                               │
│ Notepad • Explorer • Chrome • VS Code • etc.  │
└───────────────────────────────────────────────┘
```

These layers must remain separate.

A capability existing in one layer does **not** automatically mean it is available in another.

For example:

```text
UIA supports ValuePattern
        ↓
FlaUI can access ValuePattern
        ↓
Our CLI exposes elem set-value
        ↓
The current application exposes ValuePattern
        ↓
GhostHand can safely use set_value
```

If any layer fails, GhostHand needs another strategy.

---

# 3. Microsoft UI Automation Foundation

Microsoft UI Automation exposes Windows UI as **automation elements arranged in a tree**. Each element exposes properties and may expose one or more control patterns. Control patterns represent particular capabilities of a UI element.

Conceptually:

```text
Desktop
│
├── Application Window
│   │
│   ├── Menu
│   ├── Toolbar
│   ├── Button
│   ├── TextBox
│   ├── List
│   │   ├── ListItem
│   │   └── ListItem
│   └── StatusBar
│
└── Other Application
```

This tree is fundamental to GhostHand.

The agent should reason about:

```text
WHAT element is this?
WHERE is it in the UI tree?
WHAT properties does it have?
WHAT control type is it?
WHAT patterns does it support?
WHAT actions are available?
WHAT changed after the action?
```

UI Automation deliberately separates **control type** from **control patterns**. There is not a one-to-one relationship between them: one control can expose multiple patterns, and the same pattern can be used by multiple control types.

Therefore:

```text
Button ≠ "click only"

Button
 ├── Invoke
 ├── Toggle       (if supported)
 ├── etc.
```

and:

```text
ComboBox
 ├── ExpandCollapse
 ├── Selection
 ├── Value
 └── Scroll       (depending on implementation/state)
```

---

# 4. Automation Elements

An AutomationElement is the basic object GhostHand interacts with.

Important concepts:

* Name
* AutomationId
* ControlType
* ClassName
* Bounding rectangle
* Enabled state
* Visibility/offscreen state
* Parent
* Children
* Supported control patterns

Microsoft describes automation elements as the objects through which UI Automation clients access the Windows UI.

GhostHand should therefore maintain an internal representation similar to:

```json
{
  "id": "ec86bb98",
  "name": "Submit",
  "automationId": "SubmitButton",
  "controlType": "Button",
  "className": "...",
  "enabled": true,
  "offscreen": false,
  "bounds": {
    "x": 100,
    "y": 200,
    "width": 120,
    "height": 40
  }
}
```

The exact fields available must always be determined from the actual CLI/FlaUI output.

---

# 5. Element Identification Strategy

The current CLI exposes four primary selectors:

| Selector     | CLI option | Current documented quality |
| ------------ | ---------- | -------------------------- |
| AutomationId | `--aid`    | Preferred / stable         |
| Name         | `--name`   | Acceptable                 |
| ControlType  | `--type`   | Useful semantic filter     |
| ClassName    | `--class`  | Fragile                    |

The CLI explicitly describes AutomationId as the preferred stable selector, Name as acceptable, and ClassName as fragile.

## GhostHand selector priority

The initial selector strategy should therefore be:

```text
1. AutomationId
2. Name + ControlType
3. AutomationId + ControlType
4. Name
5. ClassName
6. Tree relationship / structural search
```

However, GhostHand must not blindly assume that an AutomationId exists.

Real applications differ.

---

# 6. Element Discovery

## CLI

```text
elem find
```

Current documented parameters:

```text
--aid
--name
--type
--class
--timeout
--window
--session
```

The command searches for elements by properties.

Example:

```bat
E:\FlaUI.Tools\flaui.exe elem find ^
  --aid "SubmitButton" ^
  --session "E:\notepad.session.json"
```

Or:

```bat
E:\FlaUI.Tools\flaui.exe elem find ^
  --name "Save" ^
  --type "Button" ^
  --session "E:\notepad.session.json"
```

## Agent abstraction

Eventually this should become:

```text
find_element(
    automation_id?,
    name?,
    control_type?,
    class_name?,
    timeout?
)
```

The Qwen model should not need to know CLI syntax.

---

# 7. Element Inspection

## CLI

```text
elem props
```

The command requires an element ID and returns UI Automation properties including bounds, enabled state, and offscreen state.

This is important because GhostHand should use inspection before destructive or uncertain actions.

Recommended reasoning:

```text
find
 ↓
inspect
 ↓
check enabled/offscreen/type
 ↓
perform action
 ↓
verify
```

Not:

```text
find
 ↓
blindly click
```

---

# 8. Current CLI Capability Inventory

The current CLI can be divided into these capability groups.

## 8.1 Discovery and inspection

```text
elem find
elem props
elem get-state
elem get-value
elem get-text
```

---

## 8.2 Direct interaction

```text
elem click
elem type
elem set-value
elem select
elem clear
elem keys
elem menu
```

---

## 8.3 Navigation / visibility

```text
elem scroll-into-view
elem expand
elem collapse
elem get-scroll
elem scroll
```

---

## 8.4 Numeric controls

```text
elem get-range
elem set-range
```

---

## 8.5 Grid/table controls

```text
elem grid-info
elem get-cell
elem grid-item-info
elem table-item-info
```

---

## 8.6 Docking / view management

```text
elem get-dock
elem set-dock
elem get-views
elem set-view
```

---

## 8.7 Transform operations

```text
elem transform
```

---

## 8.8 Application sessions

```text
session new
session attach
session status
session end
```

---

## 8.9 Windows

```text
window list
window focus
window close
window get-state
window minimize
window maximize
```

---

## 8.10 Recording

```text
record start
record stop
record drop
record keep
record list
record export
```

---

## 8.11 Batch execution

```text
batch
```

## The CLI's help output documents these command families and their options.

# 9. Interaction Capability: Click

## CLI

```text
elem click
```

Supported operations:

```text
single click
double click
right click
```

Parameters:

```text
--id
--double
--right
--window
--session
```

The current CLI documents all three click modes.

## GhostHand policy

A click should preferably be semantic.

```text
find button
 ↓
verify button
 ↓
invoke/click
 ↓
verify resulting state
```

The exact underlying implementation must be verified against the FlaUI source/API before we classify the action as an `InvokePattern` operation.

---

# 10. Text Input

## CLI

```text
elem type
```

Parameters:

```text
--id
--text
```

The current implementation describes this as typing through keyboard simulation.

This creates an important distinction:

### `type`

```text
UI element
   ↓
keyboard simulation
   ↓
text entered
```

### `set-value`

```text
UI element
   ↓
Value pattern
   ↓
value changed directly
```

Therefore GhostHand should eventually have both:

```text
type_text
set_value
```

and select between them based on the target's capabilities.

---

# 11. Value Pattern

## CLI

```text
elem set-value
elem get-value
```

`set-value` directly uses the UIA Value pattern and is documented as faster than `type`, although not every control supports it.

Microsoft defines ValuePattern as a pattern for controls that expose a value that does not represent a specified range.

Therefore:

```text
set_value
```

must not be treated as universally available.

Agent rule:

```text
if ValuePattern available:
    set_value
else:
    fallback to type
```

provided the fallback is appropriate for the application.

---

# 12. Reading Values

```text
elem get-value
```

The command can optionally save the retrieved value into the session under a variable name.

This gives us the beginning of a stateful automation model:

```text
UI
 ↓
read value
 ↓
store variable
 ↓
later operation
```

This capability will be important for agent verification.

Example conceptual workflow:

```text
username = get_value(username_field)

type password

click login

verify username still exists
```

---

# 13. Element State

```text
elem get-state
```

The current command returns:

* Toggle state
* Enabled/disabled state
* Visibility

according to the CLI documentation.

This should become a standard verification primitive.

Example:

```text
before:
button.enabled = true

click

after:
button.enabled = false
```

The agent can reason from the observed state instead of assuming the action succeeded.

---

# 14. Keyboard Automation

```text
elem keys
```

The current CLI supports combinations such as:

```text
ctrl+shift+s
tab
alt+f4
```

and optionally accepts an element ID to focus before sending keys.

This should eventually become:

```text
send_keys(
    keys,
    target?
)
```

Keyboard automation is particularly important for cases where a control exposes poor UIA semantics.

However, keyboard shortcuts should be considered a **fallback/navigation mechanism**, not automatically the first strategy.

---

# 15. Menu Automation

```text
elem menu
```

The CLI supports menu paths such as:

```text
File > Save As
```

using `>` separators.

This gives GhostHand a high-level semantic operation:

```text
navigate_menu("File > Save As")
```

This is significantly more useful to an agent than requiring Qwen to reason about menu coordinates.

---

# 16. Clearing Text

```text
elem clear
```

Clears an element's text content.

Agent abstraction:

```text
clear_text(element)
```

Potential fallback:

```text
clear
 ↓
if unsupported
 ↓
select all
 ↓
backspace
```

The fallback should only be implemented after actual behavior is tested.

---

# 17. Scroll Item Into View

```text
elem scroll-into-view
```

Uses the ScrollItem pattern to bring an element into view.

This is important because GhostHand should prefer:

```text
find element
 ↓
scroll into view
 ↓
interact
```

instead of:

```text
guess scroll amount
 ↓
guess location
 ↓
click coordinates
```

---

# 18. Expand / Collapse

```text
elem expand
elem collapse
```

The CLI documents support for controls such as:

* Expander
* TreeViewItem
* ComboBox

through expand/collapse behavior.

These operations are essential for navigating hierarchical UIs.

Example:

```text
Explorer
 └── Documents
      └── Projects
           └── Pocket-AI
```

GhostHand can conceptually perform:

```text
expand Documents
expand Projects
expand Pocket-AI
```

rather than relying on coordinates.

---

# 19. Range Controls

The CLI provides:

```text
elem get-range
elem set-range
```

The range functionality exposes:

* Current value
* Minimum
* Maximum
* Step size

and allows setting the value.

Typical targets may include:

```text
slider
volume
brightness
numeric control
progress-like controls
```

Actual application support must be tested.

---

# 20. Grid Automation

The CLI provides:

```text
elem grid-info
elem get-cell
elem grid-item-info
```

`grid-info` retrieves row count, column count, and column headers, while `get-cell` accesses a cell using zero-based row and column indexes.

This creates a potentially powerful agent capability:

```text
inspect table
 ↓
understand headers
 ↓
locate row
 ↓
locate column
 ↓
read cell
```

Instead of making Qwen interpret screenshots of tables.

---

# 21. Text Retrieval

```text
elem get-text
```

The CLI documents this as retrieving full text through the Text pattern for controls such as RichTextBox and Document.

This is one of the most important capabilities for a text-oriented agent.

Potential GhostHand operation:

```text
read_text(element)
```

This could allow Qwen to inspect application content without OCR when the application exposes the text through UIA.

---

# 22. Scrolling

The CLI provides:

```text
elem get-scroll
elem scroll
```

`get-scroll` retrieves scroll position/state, while `scroll` accepts horizontal and vertical percentages from 0–100, with `-1` meaning no change for that axis.

Conceptual API:

```text
scroll(
    element,
    horizontal?,
    vertical?
)
```

Example:

```text
scroll(
    element="main_panel",
    vertical=100
)
```

---

# 23. Dock Pattern

The CLI exposes:

```text
elem get-dock
elem set-dock
```

Supported positions documented by the CLI:

```text
top
bottom
left
right
fill
none
```

This is a specialized capability and should not initially be prioritized for general Qwen automation.

---

# 24. Grid Item / Table Item Information

The CLI exposes:

```text
elem grid-item-info
elem table-item-info
```

Grid item information provides:

```text
row
column
row span
column span
```

Table item information provides row/column header information.

These operations should eventually help GhostHand understand structured application interfaces.

---

# 25. Multiple Views

The CLI exposes:

```text
elem get-views
elem set-view
```

`get-views` retrieves supported views and the current view; `set-view` changes the view using an ID obtained from `get-views`.

Example conceptual workflow:

```text
get_views
 ↓
choose supported view
 ↓
set_view
 ↓
verify
```

---

# 26. Transform

The CLI exposes:

```text
elem transform
```

Documented operations include:

```text
move
resize
rotate
```

using:

```text
--x
--y
--width
--height
--rotate
```

This is **not the same thing as moving the physical mouse**.

It is a UI Automation Transform operation against an element that supports that capability.

It should therefore remain distinct from GhostHand's prohibited physical-coordinate mouse layer.

---

# 27. Sessions

GhostHand uses a session concept to maintain context around an application.

## Create

```text
session new
```

Can:

* Launch an executable.
* Pass arguments.
* Wait for a title.
* Wait for a main window.
* Store/use a session file.

## Attach

```text
session attach
```

Can attach by:

```text
PID
process name
window title
```

This is especially useful for applications where launching through `session new` is unreliable.

Current practical example:

```bat
start "" "C:\Windows\System32\notepad.exe"

E:\FlaUI.Tools\flaui.exe session attach ^
    --name notepad
```

---

# 28. Session Lifecycle

```text
session status
session end
```

`session end` can optionally close the application, with a force option for an unresponsive process.

GhostHand should treat sessions as resources:

```text
create/attach
 ↓
use
 ↓
verify
 ↓
release
```

---

# 29. Window Management

The current CLI exposes:

```text
window list
window focus
window close
window get-state
window minimize
window maximize
```

The documented functionality includes:

* Listing top-level windows.
* Focusing a window.
* Closing a window.
* Reading visual/modal/topmost state.
* Minimizing.
* Maximizing.

This forms the first layer of GhostHand's **window manager**.

---

# 30. Recording

The CLI contains a recording subsystem:

```text
record start
record stop
record drop
record keep
record list
record export
```

It supports starting a recording with a human-readable description, excluding steps, restoring dropped steps, listing steps, and exporting the recording to JSON.

This is potentially extremely valuable for GhostHand.

Long-term use:

```text
Human performs workflow
        ↓
GhostHand records UI actions
        ↓
recording.json
        ↓
analyze selectors/actions
        ↓
convert into reusable automation skill
```

This could eventually become the foundation of **skill learning from demonstrations**.

---

# 31. Batch Execution

The CLI supports:

```text
batch
```

with:

```text
--file
--steps
--continue-on-error
--session
```

This is important for agent execution because Qwen may produce a sequence such as:

```text
find
inspect
click
type
click
verify
```

A batch layer could eventually reduce process-launch overhead.

However, we should not expose unrestricted batches to Qwen initially.

---

# 32. Underlying UI Automation Model

Microsoft UI Automation provides five fundamental concepts relevant to GhostHand:

```text
1. UI Automation tree
2. Automation elements
3. Automation properties
4. Control patterns
5. Automation events
```

Microsoft explicitly identifies these as the major components used for automated UI interaction.

GhostHand should therefore eventually model:

```text
Element
 ├── Properties
 ├── ControlType
 ├── Patterns
 ├── Parent
 ├── Children
 └── Events
```

---

# 33. Control Patterns

Microsoft UI Automation defines a collection of control patterns representing specific capabilities.

Important patterns relevant to GhostHand include:

```text
Invoke
Value
Selection
ExpandCollapse
Scroll
ScrollItem
RangeValue
Grid
GridItem
Table
TableItem
Toggle
Transform
Dock
MultipleView
Window
Text
TextRange
```

Microsoft's current UI Automation documentation describes control patterns as interfaces exposing properties, methods, events, and relationships for specific control functionality.

The Windows UI Automation specification currently describes **22 predefined control patterns**, while custom patterns are also possible.

Important:

> The existence of a UIA pattern does not mean every Windows control supports it.

Pattern availability can even change dynamically with control state. Microsoft gives scrolling in a multiline edit control as an example.

Therefore GhostHand must use **capability detection**, not assumptions.

---

# 34. Capability Detection

The fundamental agent rule should be:

```text
NEVER ASSUME CAPABILITY.
DETECT → EXECUTE → VERIFY.
```

Example:

```text
Target: textbox

Detect:
    ValuePattern?

YES
    ↓
set value

NO
    ↓
type text
```

Another:

```text
Target: tree item

Detect:
    ExpandCollapse?

YES
    ↓
expand

NO
    ↓
inspect children / alternative strategy
```

---

# 35. Action Reliability Model

Every GhostHand action should eventually return structured information.

Recommended conceptual schema:

```json
{
  "success": true,
  "action": "click",
  "target": {
    "id": "abc123",
    "name": "Save",
    "controlType": "Button"
  },
  "method": "semantic",
  "verification": {
    "performed": true,
    "result": "observed"
  }
}
```

Failure:

```json
{
  "success": false,
  "action": "set_value",
  "reason": "ValuePatternNotSupported",
  "fallback": "type"
}
```

This is more useful to Qwen than raw console output.

---

# 36. Verification-First Automation

GhostHand should follow:

```text
OBSERVE
   ↓
PLAN
   ↓
ACT
   ↓
VERIFY
   ↓
RECOVER
```

Example:

```text
User:
"Open Save As"

Qwen:
1. Inspect current window
2. Locate File menu
3. Navigate File > Save As
4. Verify Save As dialog exists
5. Continue
```

Not:

```text
click File
click Save As
assume success
```

---

# 37. Failure Categories

GhostHand should classify failures.

## Selector failure

```text
Element not found
```

Possible recovery:

```text
AutomationId
→ Name + Type
→ Name
→ tree search
```

---

## Capability failure

```text
ValuePattern unavailable
```

Possible recovery:

```text
set_value
→ type
```

---

## Visibility failure

```text
Element offscreen
```

Possible recovery:

```text
scroll_into_view
→ inspect
→ act
```

---

## State failure

```text
Element disabled
```

Possible recovery:

```text
inspect parent
inspect dialog state
wait
re-query
```

---

## Timing failure

```text
Application still loading
```

Possible recovery:

```text
wait
→ re-query
→ verify
```

---

## Stale element

A previously found element may no longer represent the current UI state.

Recovery:

```text
discard old ID
→ re-find
→ inspect
→ retry
```

This is especially important for dynamic applications.

---

# 38. Application Independence

GhostHand should have three levels of knowledge.

```text
Level 1 — Universal UIA
```

Capabilities defined by Windows UI Automation.

```text
Level 2 — FlaUI
```

How FlaUI accesses those capabilities.

```text
Level 3 — Application profile
```

What a specific application actually exposes.

For example:

```text
Universal:
ValuePattern exists

FlaUI:
can access ValuePattern

Notepad:
textbox may expose it

Chrome:
specific field may expose different patterns

VS Code:
some UI may be represented differently

Custom application:
support may be incomplete
```

This distinction is essential.

---

# 39. Real Application Capability Matrix

This will become **Inventory #3**.

Initial target applications:

| Application         | Test priority |
| ------------------- | ------------: |
| Notepad             |            P0 |
| File Explorer       |            P0 |
| Windows Settings    |            P0 |
| Chrome              |            P0 |
| VS Code             |            P0 |
| Edge                |            P1 |
| Calculator          |            P1 |
| Terminal            |            P1 |
| Task Manager        |            P1 |
| Microsoft Office    |            P2 |
| Discord             |            P2 |
| Custom WinForms app |            P2 |
| Custom WPF app      |            P2 |
| WinUI application   |            P2 |

For every application we will record:

```text
Application
Version
Framework
Session attach method
Window structure
Control types
AutomationIds
Supported patterns
Selectors that work
Actions that work
Actions that fail
Timing behavior
Dynamic UI behavior
Known fallbacks
```

---

# 40. GhostHand Tool Layer

Only after the underlying capabilities are verified should we expose tools to Qwen.

Initial conceptual tool set:

```text
app_attach
app_launch
app_status

window_list
window_focus
window_close
window_minimize
window_maximize
window_state

ui_find
ui_inspect
ui_state

ui_click
ui_double_click
ui_right_click

ui_type
ui_set_value
ui_get_value
ui_clear

ui_select
ui_expand
ui_collapse

ui_get_text

ui_scroll
ui_scroll_into_view
ui_get_scroll

ui_get_range
ui_set_range

ui_grid_info
ui_get_cell
ui_grid_item_info
ui_table_item_info

ui_menu

ui_send_keys

ui_get_views
ui_set_view

ui_transform

workflow_batch
workflow_record
```

These are **proposed agent abstractions**, not claims that the current Qwen layer already implements them.

---

# 41. Tools Qwen Should NOT Directly Control

Initially Qwen should not receive arbitrary:

```text
cmd.exe
PowerShell
raw DLL calls
arbitrary C#
arbitrary FlaUI API calls
arbitrary process termination
arbitrary window handles
arbitrary batch JSON
```

Instead:

```text
Qwen
 ↓
validated GhostHand tool
 ↓
FlaUI CLI
 ↓
Windows UI
```

This gives us a safety and debugging boundary.

---

# 42. Semantic vs Coordinate Automation

GhostHand's preferred hierarchy:

```text
1. UI Automation semantic action
2. UI Automation keyboard action
3. UI Automation tree navigation
4. Application-specific semantic fallback
5. Perception/OCR
6. Coordinate interaction — last resort / separate subsystem
```

The normal GhostHand implementation should remain UIA-first.

For example:

```text
BAD:

click(x=843, y=512)
```

Preferred:

```text
click(
    target={
        "automationId": "SaveButton"
    }
)
```

Even better:

```text
find(
    name="Save",
    controlType="Button"
)
→ inspect
→ click
→ verify
```

---

# 43. Why This Architecture Matters

The AI should not need to know that:

```text
FlaUI
→ UIA3
→ COM
→ AutomationElement
→ InvokePattern
```

The AI should reason in terms of:

```text
Find Save button
Inspect it
Click it
Verify save dialog
```

The implementation layer handles the technical translation.

Therefore:

```text
Qwen reasoning language
        ↓
GhostHand semantic tool
        ↓
FlaUI implementation
        ↓
Windows UI Automation
        ↓
Application
```

---

# 44. Inventory Status

## Inventory #1 — CLI

**Status: Documented v0.1**

Current CLI capabilities identified from the supplied help output:

```text
Discovery
Inspection
Click
Typing
Value
Selection
State
Keyboard
Menus
Clear
ScrollIntoView
Expand/Collapse
Range
Grid
Text
Scroll
Dock
GridItem
TableItem
MultipleView
Transform

Sessions
Windows
Recording
Batch
```

## Source: supplied FlaUI CLI help output.

## Inventory #2 — UI Automation / FlaUI

**Status: Started**

Confirmed foundational concepts:

```text
Automation Elements
UIA Tree
Properties
Control Types
Control Patterns
Events
Client/Provider model
Dynamic pattern availability
```

Microsoft documents UI Automation as a programmatic interface to Windows UI elements, with elements organized in a tree and functionality exposed through properties and control patterns.

**Next work:** map every CLI command to its exact FlaUI API and underlying UIA pattern/interface.

---

## Inventory #3 — Real Applications

**Status: Not yet completed**

We will experimentally test:

```text
Notepad
Explorer
Settings
Chrome
VS Code
Edge
Calculator
Terminal
Task Manager
```

The results will be recorded rather than assumed.

---

## Inventory #4 — Qwen/GhostHand Tools

**Status: Architecture defined**

The final tool layer will only expose capabilities that have passed:

```text
CLI verification
        ↓
FlaUI/UIA verification
        ↓
real application verification
        ↓
failure/recovery testing
        ↓
agent-tool approval
```

---

# 45. Core Design Principle

The most important rule for GhostHand is:

```text
CAPABILITY ≠ COMMAND ≠ APPLICATION SUPPORT ≠ AGENT TOOL
```

These are four different things.

Example:

```text
UIA:
    ValuePattern exists

FlaUI:
    ValuePattern can be accessed

CLI:
    elem set-value exists

Application:
    target control may or may not expose ValuePattern

GhostHand:
    set_value should only be offered when capability detection succeeds
```

This distinction will prevent a large amount of fragile automation later.

---

# 46. Next Documentation Phase

The next section of the specification should be:

## Inventory #2 — Complete FlaUI/UIA Capability Map

For every supported capability we will document:

```text
Capability
    ↓
Microsoft UIA Pattern
    ↓
UIA interface
    ↓
FlaUI class/API
    ↓
Current CLI command
    ↓
Required parameters
    ↓
Expected output
    ↓
Supported control types
    ↓
Known limitations
    ↓
Fallback strategy
    ↓
Verification strategy
    ↓
Potential GhostHand tool
```

Example:

```text
SET VALUE
│
├── UIA Pattern
│   └── ValuePattern
│
├── UIA Interface
│   └── IValueProvider
│
├── FlaUI
│   └── ValuePattern wrapper
│
├── CLI
│   └── elem set-value
│
├── Input
│   ├── element ID
│   └── value
│
├── Limitation
│   └── target must support ValuePattern
│
├── Fallback
│   └── keyboard typing
│
└── GhostHand
    └── ui_set_value
```

That mapping will become the **actual technical core from which the automation agent tools are implemented**.

---

# 47. Source Classification

This specification uses three evidence levels.

### `[CLI]`

Directly documented by the supplied `FlaUI.Cli --help` output.

### `[UIA]`

Supported by Microsoft's UI Automation documentation.

### `[TEST]`

Observed experimentally against a real application.

The final GhostHand tool registry should prefer:

```text
[CLI] + [UIA] + [TEST]
```

over assumptions.

A capability that only exists as `[UIA]` should not automatically be treated as available in the current CLI.

---

# 48. Current Ground Truth

At this stage, the strongest confirmed fact is:

> The current `FlaUI.Tools\flaui.exe` already exposes a broad semantic automation surface.

It includes far more than basic clicking and typing: structured element discovery, UI state inspection, values, selection, keyboard input, menus, scrolling, hierarchical controls, numeric ranges, tables/grids, view management, transforms, session lifecycle, window management, recording, and batch execution.
The next engineering task is therefore **not to immediately add more random tools**.

It is to determine:

```text
What exactly is behind every command?
What UIA pattern does it use?
What FlaUI API implements it?
What controls support it?
What applications expose it?
What happens when it fails?
What is the safest Qwen-facing abstraction?
```

That investigation becomes the foundation of GhostHand.
