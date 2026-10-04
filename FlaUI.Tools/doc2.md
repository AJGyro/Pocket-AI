# GhostHand / Pocket AI

# Core Automation Specification

## Phase 2 — FlaUI + Windows UI Automation Capability Map

**Status:** Architecture / capability mapping
**Automation stack:** GhostHand → FlaUI CLI → FlaUI → Windows UI Automation
**Primary framework:** FlaUI UIA3
**Current CLI:** `E:\FlaUI.Tools\flaui.exe`

---

# 1. Architecture

The complete stack is:

```text
Qwen Agent
    │
    ▼
GhostHand Semantic Tools
    │
    ▼
GhostHand Executor
    │
    ▼
FlaUI CLI
    │
    ▼
FlaUI
    │
    ▼
Windows UI Automation
    │
    ▼
Windows Application
```

The important distinction is:

```text
UIA capability
      ≠
FlaUI capability
      ≠
CLI capability
      ≠
Application capability
      ≠
Qwen tool
```

A capability becomes a production GhostHand tool only after it passes through the required layers.

---

# 2. UI Automation Control Patterns

Microsoft defines control patterns as interfaces that expose a particular aspect of a control's functionality. A control can expose multiple patterns, and pattern support can change dynamically depending on the control's current state.

The major patterns relevant to GhostHand are:

| Pattern           | Main purpose                       | Current CLI            |
| ----------------- | ---------------------------------- | ---------------------- |
| Invoke            | Activate a control                 | Indirect / `click`     |
| Value             | Read/write a value                 | Yes                    |
| Selection         | Selection container                | Yes                    |
| SelectionItem     | Select individual item             | Yes / through `select` |
| ExpandCollapse    | Expand/collapse                    | Yes                    |
| Scroll            | Scroll container                   | Yes                    |
| ScrollItem        | Bring item into view               | Yes                    |
| RangeValue        | Numeric/range value                | Yes                    |
| Grid              | Table/grid navigation              | Yes                    |
| GridItem          | Individual grid cell               | Yes                    |
| Table             | Grid + headers                     | Yes                    |
| TableItem         | Table cell/header information      | Yes                    |
| Text              | Retrieve text/document information | Yes                    |
| Toggle            | Toggle state                       | Indirectly via state   |
| Transform         | Move/resize/rotate                 | Yes                    |
| Dock              | Docking                            | Yes                    |
| MultipleView      | Change view                        | Yes                    |
| Window            | Window operations                  | Partially              |
| VirtualizedItem   | Virtualized controls               | Not exposed            |
| ItemContainer     | Search virtualized/container items | Not exposed            |
| Drag              | Drag source                        | Not exposed            |
| DropTarget        | Drop target                        | Not exposed            |
| LegacyIAccessible | Legacy accessibility               | Not exposed            |
| ObjectModel       | Underlying object model            | Not exposed            |
| Spreadsheet       | Spreadsheet semantics              | Not exposed            |
| TextEdit          | Advanced text editing              | Not exposed            |
| Text2             | Extended text functionality        | Not exposed            |
| Styles            | UI style information               | Not exposed            |
| Annotation        | Document annotations               | Not exposed            |
| SynchronizedInput | Synchronized input                 | Not exposed            |

Microsoft documents these patterns and their provider/client interfaces.

FlaUI's UIA3 implementation exposes a corresponding pattern library, including both patterns already surfaced by our CLI and several that are currently unavailable through our CLI.

---

# 3. Pattern Availability Is Dynamic

GhostHand must never assume:

```text
ControlType = X
        ↓
Pattern Y definitely exists
```

That is not guaranteed.

Microsoft explicitly documents dynamic control-pattern support. For example, a multiline edit control may expose Scroll only when its content requires scrolling.

Therefore:

```text
find element
    ↓
inspect element
    ↓
determine available capability
    ↓
perform action
```

is the correct architecture.

---

# 4. FlaUI Pattern Architecture

FlaUI provides a common abstraction over UI Automation patterns.

The UIA3 pattern library currently exposes pattern identifiers for:

```text
Annotation
Dock
Drag
DropTarget
ExpandCollapse
GridItem
Grid
Invoke
ItemContainer
LegacyIAccessible
MultipleView
ObjectModel
RangeValue
ScrollItem
Scroll
SelectionItem
Selection
SpreadsheetItem
Spreadsheet
Styles
SynchronizedInput
TableItem
Table
TextChild
TextEdit
Text2
Text
Toggle
Transform2
Transform
Value
VirtualizedItem
Window
```

This is directly visible in FlaUI's current `UIA3PatternLibrary`.

This gives us an important future direction:

```text
Current CLI
    ↓
small exposed subset

Future GhostHand native engine
    ↓
potentially much larger FlaUI capability set
```

We should therefore avoid designing the architecture around only today's CLI commands.

---

# 5. UIA3 vs UIA2

FlaUI contains separate UIA2 and UIA3 implementations.

The current FlaUI source shows the UIA2 framework implementation mapping many patterns to the corresponding Windows UI Automation classes, including:

```text
InvokePattern
ValuePattern
SelectionPattern
SelectionItemPattern
ExpandCollapsePattern
ScrollPattern
ScrollItemPattern
GridPattern
GridItemPattern
TablePattern
TableItemPattern
RangeValuePattern
TextPattern
TogglePattern
TransformPattern
DockPattern
MultipleViewPattern
WindowPattern
```

and other patterns where supported by that framework.

For GhostHand, we should standardize on **UIA3** unless testing reveals a concrete application compatibility reason to use UIA2.

---

# 6. INVOKE

## UIA

```text
InvokePattern
```

Provider:

```text
IInvokeProvider
```

Client:

```text
IUIAutomationInvokePattern
```

Microsoft describes Invoke as the pattern for controls that perform a single, unambiguous action, such as a button.

Typical controls:

```text
Button
MenuItem
Hyperlink
```

depending on application implementation.

## FlaUI

FlaUI exposes:

```text
IInvokePattern
```

through its pattern library.

## Current CLI

```text
elem click
```

Current CLI supports:

```text
click
double-click
right-click
```

but the CLI documentation does not by itself prove which underlying FlaUI pattern is used for each operation.

Therefore:

```text
CLICK → UIA mapping = implementation verification required
```

## GhostHand

Recommended abstraction:

```text
ui_invoke
```

Potential semantic API:

```json
{
  "target": "...",
  "action": "invoke"
}
```

---

# 7. VALUE

## UIA

```text
ValuePattern
```

Provider:

```text
IValueProvider
```

Client:

```text
IUIAutomationValuePattern
```

Used for controls whose value does not represent a numeric range.

## FlaUI

FlaUI exposes:

```text
IValuePattern
```

and the UIA3 pattern library contains `ValuePattern`.

## Current CLI

```text
elem set-value
elem get-value
```

The supplied CLI documentation explicitly says `set-value` uses the Value pattern and may be faster than typing, but only controls supporting the pattern can use it.

## GhostHand

```text
ui_get_value
ui_set_value
```

Recommended behavior:

```text
if ValuePattern supported:
    set value directly
else:
    fallback to text input
```

---

# 8. TEXT INPUT

This requires special treatment.

Current CLI:

```text
elem type
```

is documented as typing through keyboard simulation.

That is different from:

```text
ValuePattern.SetValue()
```

Therefore GhostHand should maintain two separate operations:

```text
ui_type
ui_set_value
```

Do not collapse them into one implementation.

---

# 9. SELECTION

## UIA

Two related concepts exist:

```text
SelectionPattern
SelectionItemPattern
```

Selection is associated with the container, while SelectionItem is associated with individual selectable items. Microsoft lists both separately.

Typical structures:

```text
ComboBox
    └── ListItem

List
    ├── ListItem
    ├── ListItem
    └── ListItem
```

## Current CLI

```text
elem select
```

is documented for combo/list selection.

## GhostHand

```text
ui_select
```

should conceptually:

```text
find container/item
        ↓
inspect selection capability
        ↓
select
        ↓
verify selected state
```

---

# 10. TOGGLE

## UIA

```text
TogglePattern
```

Provider:

```text
IToggleProvider
```

Client:

```text
IUIAutomationTogglePattern
```

Used for controls whose state can be toggled, such as check boxes.

## FlaUI

FlaUI UIA3 exposes `TogglePattern`.

## Current CLI

There is no dedicated:

```text
elem toggle
```

command in the current CLI.

However:

```text
elem get-state
```

documents retrieval of toggle state.

Therefore:

```text
READ toggle = CLI supported
CHANGE toggle = not currently documented as dedicated CLI operation
```

This is a major candidate for future CLI expansion.

## Future GhostHand

```text
ui_toggle
```

This should be implemented only after adding and testing the underlying FlaUI capability.

---

# 11. EXPAND / COLLAPSE

## UIA

```text
ExpandCollapsePattern
```

Provider:

```text
IExpandCollapseProvider
```

Client:

```text
IUIAutomationExpandCollapsePattern
```

Used for controls that expose expandable/collapsible content. Microsoft gives menu items as one example.

## Current CLI

```text
elem expand
elem collapse
```

The supplied CLI documentation specifically mentions controls such as TreeViewItem, Expander and ComboBox.

## GhostHand

```text
ui_expand
ui_collapse
```

Verification:

```text
expand
 ↓
get state
 ↓
verify expanded
```

---

# 12. SCROLL

Two distinct patterns matter.

```text
ScrollPattern
ScrollItemPattern
```

Microsoft defines Scroll for containers and ScrollItem for individual items inside scrollable lists/containers.

## Container

```text
ui_scroll
```

Current CLI:

```text
elem get-scroll
elem scroll
```

## Individual item

```text
ui_scroll_into_view
```

Current CLI:

```text
elem scroll-into-view
```

This distinction is important:

```text
scroll container
        ≠
scroll item into view
```

---

# 13. RANGE VALUE

## UIA

```text
RangeValuePattern
```

Provider:

```text
IRangeValueProvider
```

Used for controls with values inside a defined numerical range.

## Current CLI

```text
elem get-range
elem set-range
```

The CLI documents current value, minimum, maximum and step.

## GhostHand

```text
ui_get_range
ui_set_range
```

Potential targets:

```text
Slider
Spinner
NumericUpDown
```

Actual application support must be tested.

---

# 14. GRID

## UIA

```text
GridPattern
```

Provider:

```text
IGridProvider
```

Used for grid-like interfaces.

Microsoft gives Windows Explorer large-icon views and simple tables as examples.

## Current CLI

```text
elem grid-info
elem get-cell
```

## GhostHand

```text
ui_grid_info
ui_grid_get_cell
```

Conceptual workflow:

```text
grid_info
    ↓
rows / columns
    ↓
identify target
    ↓
get_cell(row, column)
```

---

# 15. GRID ITEM

## UIA

```text
GridItemPattern
```

Provider:

```text
IGridItemProvider
```

Used by individual cells/items inside grids.

## Current CLI

```text
elem grid-item-info
```

provides row, column and span information.

## GhostHand

```text
ui_grid_item_info
```

This will become important when Qwen needs to reason about structured tables.

---

# 16. TABLE

## UIA

```text
TablePattern
TableItemPattern
```

Table extends grid-style semantics with header information.

Microsoft identifies Excel worksheets as an example of TablePattern.

## Current CLI

```text
elem table-item-info
```

is available for table-item header information.

## GhostHand

Potential future tools:

```text
ui_table_info
ui_table_item_info
ui_get_row_headers
ui_get_column_headers
```

---

# 17. TEXT

## UIA

```text
TextPattern
```

and newer text-related patterns exist in UIA3.

Microsoft describes Text-related UI Automation functionality as providing access to textual content, attributes and ranges.

## FlaUI

The current FlaUI UIA3 pattern library exposes:

```text
TextPattern
TextChildPattern
TextEditPattern
Text2Pattern
```

## Current CLI

```text
elem get-text
```

is documented as using Text pattern functionality for controls such as RichTextBox and Document.

## GhostHand

```text
ui_get_text
```

Future possibilities:

```text
ui_get_text_range
ui_get_text_selection
ui_edit_text_range
```

but these require CLI implementation and application testing first.

---

# 18. MULTIPLE VIEW

## UIA

```text
MultipleViewPattern
```

Used when the same information can be represented in multiple views.

Microsoft gives list views with thumbnail/tile/icon/list/detail representations as an example.

## Current CLI

```text
elem get-views
elem set-view
```

## GhostHand

```text
ui_get_views
ui_set_view
```

---

# 19. TRANSFORM

## UIA

```text
TransformPattern
```

Provider:

```text
ITransformProvider
```

Used for controls that can be moved, resized, or rotated.

## Current CLI

```text
elem transform
```

supports:

```text
move
resize
rotate
```

## Important

This is **not physical mouse movement**.

It is semantic manipulation of a UI Automation element.

---

# 20. DOCK

## UIA

```text
DockPattern
```

Provider:

```text
IDockProvider
```

Used for dockable controls such as toolbars/tool palettes.

## Current CLI

```text
elem get-dock
elem set-dock
```

Supported documented positions:

```text
top
bottom
left
right
fill
none
```

## GhostHand

```text
ui_get_dock
ui_set_dock
```

This is a specialized tool and should have low initial priority.

---

# 21. WINDOW

## UIA

```text
WindowPattern
```

Provider:

```text
IWindowProvider
```

Used for windows and dialogs.

## FlaUI

FlaUI UIA3 exposes WindowPattern.

## Current CLI

Window management is currently split between:

```text
window list
window focus
window close
window get-state
window minimize
window maximize
```

This means our CLI's window layer is broader than simply exposing one UIA pattern.

---

# 22. VIRTUALIZED ITEM

## UIA

```text
VirtualizedItemPattern
```

This is important for modern applications containing large or virtualized lists.

FlaUI UIA3 exposes `VirtualizedItemPattern`.

Current CLI:

```text
NOT EXPOSED
```

Potential future GhostHand capability:

```text
ui_realize_item
```

This could become extremely important for:

```text
large lists
Explorer
browser interfaces
modern WinUI applications
data-heavy applications
```

But it must be tested before implementation.

---

# 23. ITEM CONTAINER

UIA exposes:

```text
ItemContainerPattern
```

FlaUI UIA3 exposes it.

This pattern can be particularly valuable when an application virtualizes its children.

Current CLI:

```text
NOT EXPOSED
```

Potential future operation:

```text
ui_find_item
```

Instead of:

```text
load every descendant
→ search everything
```

This may eventually provide a more scalable discovery strategy.

---

# 24. DRAG AND DROP

FlaUI UIA3 exposes:

```text
DragPattern
DropTargetPattern
```

Microsoft UI Automation also defines these patterns.

Current CLI:

```text
NOT EXPOSED
```

This is a major future area because drag-and-drop is common in:

```text
Explorer
browser
IDE
design tools
file managers
creative applications
```

However, we must not assume UIA drag/drop works universally.

Therefore:

```text
Drag capability
    ↓
UIA pattern?
    ↓
application support?
    ↓
fallback?
```

must be experimentally established.

---

# 25. LEGACY IAACCESSIBLE

FlaUI UIA3 exposes:

```text
LegacyIAccessiblePattern
```

This is potentially useful for older applications that do not expose modern UIA semantics well.

Current CLI:

```text
NOT EXPOSED
```

Potential GhostHand architecture:

```text
Modern UIA
      ↓
if unavailable
      ↓
LegacyIAccessible
```

This should be considered a **compatibility layer**, not the default strategy.

---

# 26. OBJECT MODEL

FlaUI UIA3 exposes:

```text
ObjectModelPattern
```

Microsoft describes ObjectModel as a mechanism for exposing a pointer into an underlying object model.

Current CLI:

```text
NOT EXPOSED
```

This is a specialized advanced capability.

---

# 27. SPREADSHEET

FlaUI UIA3 exposes:

```text
SpreadsheetPattern
SpreadsheetItemPattern
```

Current CLI:

```text
NOT EXPOSED
```

This could become useful for:

```text
Excel
spreadsheet editors
data grids
```

but should come after the generic Grid/Table subsystem.

---

# 28. TEXT EDIT

FlaUI UIA3 exposes:

```text
TextEditPattern
Text2Pattern
TextChildPattern
```

Current CLI:

```text
NOT EXPOSED
```

These are candidates for future advanced text automation.

The existing:

```text
get-text
type
set-value
```

should remain the initial text subsystem.

---

# 29. ANNOTATION

FlaUI UIA3 exposes:

```text
AnnotationPattern
```

Current CLI:

```text
NOT EXPOSED
```

Likely use cases:

```text
documents
PDF readers
office applications
developer/documentation tools
```

Low initial priority.

---

# 30. STYLES

FlaUI UIA3 exposes:

```text
StylesPattern
```

Current CLI:

```text
NOT EXPOSED
```

This is mainly an inspection capability rather than an immediate interaction capability.

---

# 31. SYNCHRONIZED INPUT

FlaUI UIA3 exposes:

```text
SynchronizedInputPattern
```

Current CLI:

```text
NOT EXPOSED
```

Potential relevance:

```text
input synchronization
automation timing
complex UI workflows
```

Needs deeper investigation before inclusion.

---

# 32. Pattern Coverage Matrix

The current architecture can therefore be summarized as:

```text
                    UIA     FlaUI UIA3     CLI
---------------------------------------------------
Invoke               YES        YES        indirect
Value                YES        YES        YES
Selection            YES        YES        YES
SelectionItem        YES        YES        YES
ExpandCollapse       YES        YES        YES
Scroll               YES        YES        YES
ScrollItem           YES        YES        YES
RangeValue           YES        YES        YES
Grid                 YES        YES        YES
GridItem             YES        YES        YES
Table                YES        YES        YES
TableItem            YES        YES        YES
Text                 YES        YES        YES
Toggle                YES        YES        partial
Transform             YES        YES        YES
Dock                  YES        YES        YES
MultipleView          YES        YES        YES
Window                YES        YES        partial
VirtualizedItem       YES        YES        NO
ItemContainer         YES        YES        NO
Drag                  YES        YES        NO
DropTarget            YES        YES        NO
LegacyIAccessible     YES        YES        NO
ObjectModel           YES        YES        NO
Spreadsheet           YES        YES        NO
TextEdit              YES        YES        NO
Text2                 YES        YES        NO
Annotation             YES        YES        NO
Styles                 YES        YES        NO
SynchronizedInput      YES        YES        NO
```

FlaUI's UIA3 source is the basis for the FlaUI column; Microsoft's UI Automation documentation is the basis for the UIA column.

The CLI column is based on the supplied CLI help output and is deliberately conservative.

---

# 33. Current CLI Is Not the Final Automation Engine

This is one of the most important architectural conclusions.

Currently:

```text
Qwen
 ↓
CLI
 ↓
FlaUI
```

But eventually we may want:

```text
Qwen
 ↓
GhostHand Tool API
 ↓
GhostHand Native Executor
 ↓
FlaUI
 ↓
UIA3
```

Why?

Because the CLI currently exposes only a subset of the FlaUI UIA3 pattern library.

If we eventually need:

```text
VirtualizedItem
ItemContainer
Drag
DropTarget
LegacyIAccessible
Spreadsheet
TextEdit
Text2
Toggle
```

we should not force everything through command-line parsing.

---

# 34. Proposed GhostHand Capability Tiers

## Tier 0 — Observation

```text
find
inspect
properties
state
text
value
window list
```

No destructive actions.

---

## Tier 1 — Basic interaction

```text
invoke
click
type
set value
clear
select
keys
```

---

## Tier 2 — Navigation

```text
expand
collapse
scroll
scroll into view
menus
window focus
```

---

## Tier 3 — Structured UI

```text
grid
grid item
table
table item
range
multiple view
```

---

## Tier 4 — Window/layout manipulation

```text
window operations
dock
transform
```

---

## Tier 5 — Advanced UIA

```text
virtualized item
item container
drag
drop
legacy accessibility
spreadsheet
text edit
text2
object model
annotation
styles
```

---

# 35. Recommended Agent Execution Policy

Qwen should generally follow:

```text
OBSERVE
  ↓
IDENTIFY
  ↓
CHECK CAPABILITIES
  ↓
SELECT METHOD
  ↓
ACT
  ↓
VERIFY
  ↓
RECOVER
```

Example:

```text
Task:
"Click Save"

OBSERVE
 ↓
find name="Save"

IDENTIFY
 ↓
control type = Button

CHECK
 ↓
Invoke available?

YES
 ↓
Invoke

VERIFY
 ↓
dialog/window state changed?
```

Microsoft specifically describes Invoke as the semantic action for controls that perform a single unambiguous action.

---

# 36. Selector + Pattern Model

A GhostHand element should eventually be represented conceptually as:

```json
{
  "element_id": "3a60ca98",
  "name": "Text editor",
  "automation_id": "",
  "control_type": "Document",
  "class_name": "RichEditD2DPT",
  "enabled": true,
  "offscreen": false,
  "patterns": [
    "Text",
    "Value"
  ]
}
```

The important new field is:

```text
patterns
```

This allows Qwen/tooling to reason about **capabilities rather than control names**.

---

# 37. Capability-Based Action Selection

Example:

```text
Target:
Text editor
```

Available capabilities:

```text
Text
Value
```

Then:

```text
"replace document contents"
```

could choose:

```text
Value.SetValue
```

if supported.

While:

```text
"read document"
```

could choose:

```text
TextPattern
```

This is much more robust than:

```text
if control_type == Document:
    do X
```

---

# 38. Verification Is Part of Every Tool

Every future GhostHand tool should define:

```text
Action
Expected effect
Verification method
Fallback
Failure class
```

Example:

```text
ui_set_value

ACTION:
    set ValuePattern

EXPECTED:
    target value == requested value

VERIFY:
    get_value

FALLBACK:
    ui_type

FAILURE:
    ValuePatternUnsupported
```

---

# 39. Tool Contract Concept

Eventually each Qwen-facing tool should have a contract similar to:

```json
{
  "name": "ui_set_value",
  "description": "Set the semantic value of a UI element.",
  "requires": [
    "element"
  ],
  "capability": "ValuePattern",
  "fallback": "ui_type",
  "verification": "ui_get_value"
}
```

Qwen should reason using this semantic contract.

It should not need to know:

```text
FlaUI
UIA3
COM
PatternId
AutomationElement
```

unless we intentionally expose technical diagnostics.

---

# 40. What We Have Proven So Far

### Proven from Microsoft's UIA documentation

UI Automation has:

```text
elements
properties
control types
patterns
dynamic pattern support
```

and patterns represent specific control capabilities.

### Proven from FlaUI source

FlaUI's UIA3 layer exposes a substantially larger pattern library than our current CLI.

### Proven from our CLI documentation

Our current CLI exposes:

```text
discovery
inspection
click
type
value
selection
state
keyboard
menus
clear
scroll
expand/collapse
range
grid
text
dock
views
transform
sessions
windows
recording
batch
```

### Not yet proven

We have **not yet experimentally established**:

```text
exact FlaUI method used by every CLI command
exact pattern exposed by every target application
behavior across Notepad / Explorer / Chrome / VS Code
performance
failure behavior
dynamic pattern changes
virtualized controls
drag/drop
```

Those belong to the next testing phase.

---

# 41. Phase 2 Result

The core architecture is now:

```text
                    GHOSTHAND

                         QWEN
                          │
                          ▼
                 Semantic Tool Layer
                          │
                          ▼
                Capability Detection
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
          UIA Pattern            UIA Property
              │                       │
              ▼                       ▼
            FlaUI                  FlaUI
              │                       │
              └───────────┬───────────┘
                          ▼
                     UIA3 Client
                          │
                          ▼
                  Windows Application
```

The critical principle is:

```text
Qwen chooses INTENT.

GhostHand chooses METHOD.

FlaUI executes METHOD.

UIA provides CAPABILITY.

GhostHand verifies RESULT.
```

That separation is the foundation we should keep when building the actual agent.

---

# 42. Next Phase

The next phase is **Inventory #3 — Real Windows Application Capability Matrix**.

We should now stop theorizing and test the real system.

Initial test suite:

```text
TEST-01  Notepad
TEST-02  File Explorer
TEST-03  Windows Settings
TEST-04  Chrome
TEST-05  VS Code
```

For every application we will test:

```text
Session attach
Window discovery
Element tree
Element properties
AutomationId
Name
ControlType
Click
Type
Value
Get Value
Get Text
Keyboard
Menu
Selection
Expand/Collapse
Scroll
Scroll Into View
Range
Grid/Table
Window state
```

Then record:

```text
SUPPORTED
UNSUPPORTED
PARTIAL
DYNAMIC
FALLBACK REQUIRED
```

That test matrix will tell us what GhostHand can **actually do**, rather than what UI Automation theoretically supports.
