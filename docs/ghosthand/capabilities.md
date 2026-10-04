# GhostHand Capabilities & Patterns

## UIA Pattern Support
GhostHand inspects and uses official Microsoft UI Automation control patterns:

| Pattern | Supported Controls | GhostHand Action |
|---------|-------------------|------------------|
| `Invoke` | Button, MenuItem, Hyperlink | `click` |
| `Toggle` | CheckBox, ToggleButton | `click`, `set_state` |
| `Value` | TextBox, Edit, Document | `type`, `set_value`, `get_value` |
| `RangeValue` | Slider, ScrollBar, ProgressBar | `set_range`, `get_range` |
| `SelectionItem` | RadioButton, ListBoxItem, TabItem | `select` |
| `ExpandCollapse` | ComboBox, TreeViewItem | `expand`, `collapse` |
| `ScrollItem` | Any scrollable list item | `scroll_into_view` |
| `Text` | RichTextBox, Document | `get_text` |
| `Window` | Top-level windows | `minimize`, `maximize`, `close` |
| `Transform` | Floating or resizable panels | `move`, `resize` |

## Modern Windows & Packaged App Nuances
Modern Windows applications (Windows 11 Notepad, Calculator, Terminal) differ significantly from legacy Win32 apps:
- **Redirection & Launcher Stubs**: Launching `notepad.exe` often executes a stub that exits immediately and redirects to a packaged container process. `app_launch` handles this automatically by launching and polling for window attachment by process name.
- **Document vs Edit Controls**: The primary text editor in Windows 11 Notepad is exposed as `control_type: "Document"` (name: `"Text editor"` or automation_id: `"ContentTextBox"`), rather than an `"Edit"` or `"TextBox"` control. GhostHand provides automatic fallback aliasing between `Edit` and `Document` in `ui_find`.

## Selector Precedence
1. **AutomationId** (`stable` quality): Developer-assigned unique ID. Always preferred.
2. **Name + ControlType** (`acceptable` quality): Human-readable name constrained by element type.
3. **Name** (`acceptable` quality): Text label alone.
4. **ControlType + ClassName** (`fragile` quality): Fallback when name is dynamic or missing.
5. **ClassName** (`fragile` quality): Lowest preference; prone to breaking across OS/app versions.

## Error Recovery & Anti-Thrashing
Every GhostHand error includes:
- `code`: Machine-readable enum (e.g. `ELEMENT_STALE`, `ELEMENT_NOT_FOUND`).
- `recoverable`: Boolean indicating if the agent should retry or adapt.
- `message`: Context explaining the failure.

The agent runner enforces anti-thrashing rules preventing duplicate tool calls with identical parameters and directing the agent to inspect `ui_observe` whenever a selector query fails.
