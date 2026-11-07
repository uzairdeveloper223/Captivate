---
name: Captivate
description: A conventional Linux utility with locally hosted, offline visitor pages.
colors:
  primary: "#235daf"
  primary-hover: "#194b90"
  portal-primary-active: "#153d75"
  rail: "#243b58"
  rail-selected: "#365575"
  rail-hover: "#304d6c"
  rail-focus: "#a8c9f0"
  rail-text: "#dce7f5"
  rail-detail: "#c5d4e8"
  ink: "#24364b"
  muted: "#526276"
  surface: "#fff"
  workspace: "#edf2f8"
  portal-ground: "#eaf0f7"
  border: "#ccd7e3"
  desktop-field-border: "#aebed1"
  portal-field-border: "#a7b8cb"
  placeholder: "#647386"
  selection-background: "#ccdef6"
  selection-ink: "#152f54"
  secondary-hover: "#e8eff8"
  secondary-hover-border: "#8099b8"
  secondary-pressed: "#d9e5f4"
  disabled-surface: "#edf1f5"
  disabled-text: "#65758a"
  desktop-primary-disabled: "#8192a9"
  portal-primary-disabled: "#697d97"
  idle-surface: "#e0e8f2"
  idle-border: "#c1cedf"
  running-surface: "#e0f2e9"
  running-ink: "#236846"
  pending-surface: "#fff1d8"
  pending-ink: "#7d570e"
  error-surface: "#fff0f0"
  error-ink: "#942e2e"
  portal-error-border: "#e5b5b5"
  notice-surface: "#e2ebf7"
  notice-border: "#bfd0e5"
  notice-ink: "#324d70"
  terms-surface: "#f2f5f9"
  table-header: "#e4ecf6"
  table-grid: "#e4ebf3"
  preview-note: "#3d5370"
typography:
  desktop-body:
    fontFamily: "Noto Sans"
    fontSize: "14px"
  desktop-title:
    fontFamily: "Noto Sans"
    fontSize: "26px"
    fontWeight: 700
  desktop-brand:
    fontFamily: "Noto Sans"
    fontSize: "23px"
    fontWeight: 700
  desktop-preview-title:
    fontFamily: "Noto Sans"
    fontSize: "24px"
    fontWeight: 700
  desktop-section:
    fontFamily: "Noto Sans"
    fontSize: "16px"
    fontWeight: 650
  desktop-label:
    fontFamily: "Noto Sans"
    fontSize: "14px"
    fontWeight: 600
  desktop-small:
    fontFamily: "Noto Sans"
    fontSize: "12px"
  portal-body:
    fontFamily: "system-ui, sans-serif"
    fontSize: "16px"
    lineHeight: 1.55
  portal-title:
    fontFamily: "system-ui, sans-serif"
    fontSize: "30px"
    lineHeight: 1.2
    letterSpacing: "-.025em"
  portal-title-small:
    fontSize: "27px"
  portal-brand:
    fontFamily: "system-ui, sans-serif"
    fontSize: "18px"
    fontWeight: 650
  portal-label:
    fontFamily: "system-ui, sans-serif"
    fontSize: "16px"
    fontWeight: 600
  portal-action:
    fontFamily: "system-ui, sans-serif"
    fontSize: "16px"
    fontWeight: 650
  portal-footer:
    fontFamily: "system-ui, sans-serif"
    fontSize: "13px"
  portal-preview:
    fontFamily: "system-ui, sans-serif"
    fontSize: "14px"
rounded:
  desktop-field: "5px"
  control: "6px"
  desktop-panel: "8px"
  portal-panel: "12px"
spacing:
  field: "8px"
  compact: "10px"
  row: "12px"
  portal-gap: "14px"
  group: "16px"
  control-wide: "18px"
  rail-gap: "20px"
  column-gap: "22px"
  panel: "24px"
  mobile-block: "26px"
  section: "28px"
  brand-section: "32px"
  portal-panel: "36px"
  portal-page: "56px"
components:
  desktop-button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.surface}"
    typography: "{typography.desktop-label}"
    rounded: "{rounded.control}"
    padding: "10px 15px"
  desktop-button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
  desktop-button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    typography: "{typography.desktop-label}"
    rounded: "{rounded.control}"
    padding: "10px 15px"
  desktop-field:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    typography: "{typography.desktop-body}"
    rounded: "{rounded.desktop-field}"
    padding: "8px"
  desktop-navigation-item:
    textColor: "{colors.rail-text}"
    typography: "{typography.desktop-body}"
    rounded: "{rounded.control}"
    padding: "14px 10px"
  desktop-navigation-selected:
    backgroundColor: "{colors.rail-selected}"
    textColor: "{colors.surface}"
  desktop-state:
    backgroundColor: "{colors.idle-surface}"
    textColor: "{colors.ink}"
    typography: "{typography.desktop-label}"
    rounded: "{rounded.control}"
    padding: "7px 12px"
  desktop-panel:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.desktop-panel}"
    padding: "18px 14px 14px"
  portal-button:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.surface}"
    typography: "{typography.portal-action}"
    rounded: "{rounded.control}"
    padding: "12px 18px"
  portal-field:
    typography: "{typography.portal-body}"
    rounded: "{rounded.control}"
    padding: "10px 12px"
    width: "100%"
  portal-card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    typography: "{typography.portal-body}"
    rounded: "{rounded.portal-panel}"
    padding: "36px"
  portal-terms:
    backgroundColor: "{colors.terms-surface}"
    textColor: "{colors.ink}"
    typography: "{typography.portal-body}"
    rounded: "{rounded.control}"
    padding: "16px"
---

# Design System: Captivate

## Overview

**Creative North Star: "The Conventional Linux Utility"**

Captivate follows the user-approved Operate direction: familiar Qt Widgets, readable form groups, restrained blue actions, and explicit operational state. The desktop uses a slate-blue navigation rail against cool white work areas; visitor pages carry the same palette into a compact, single-column form.

The interface is functional and orderly. Native controls and keyboard navigation take priority; locally bundled SVG assets and system fonts support offline use. Maintained by Uzair; documentation uses formal project voice.

**Key Characteristics:**
- Conventional Qt controls and grouped forms.
- Cool surfaces, restrained blue emphasis, and text-labelled operational states.
- Locally bundled vector icons and system sans-serif typography.
- Persistent desktop actions and compact, mobile-friendly visitor pages.

Evidence: `captivate/ui.py`, `captivate/assets/portal.css`, visitor markup in `captivate/portal.py`, all bundled SVGs, and `examples/custom-portal`. Checked renders: `.impeccable/review/desktop.png`, `desktop-small.png`, `desktop-portal.png`, `portal-welcome-mobile.png`, and `portal-terms-mobile.png`. The finish verdict records FF-01–FF-03 as resolved and disposition **ship**. Runtime state styling below is source-backed; those live states were not captured in this documentation pass.

## Colors

The palette combines slate navigation, cool neutral surfaces, and a single blue action accent. Frontmatter is the normative token inventory; desktop values originate in Qt styles, while visitor aliases are `--ink`, `--muted`, `--blue`, `--line`, and `--ground`.

### Primary
- **Utility Blue:** `primary`, `primary-hover`, and `portal-primary-active` identify actions, links, selection affordances, and focus.
- **Slate Rail:** `rail`, `rail-selected`, and `rail-hover` distinguish navigation from the workspace. `rail-text`, `rail-detail`, and `rail-focus` supply readable labels, vector strokes, and keyboard focus.

### Secondary
- **Operational Green, Amber, and Red:** `running-*`, `pending-*`, and `error-*` pair text with pale backgrounds. These communicate running, starting/stopping, and attention/error states; they are not decorative accents.

### Neutral
- **Cool Work Areas:** `workspace` and `portal-ground` surround white `surface` panels. `border` delineates groups, previews, visitor cards, and dividers.
- **Slate Text:** `ink` is primary copy; `muted` is supporting copy. `placeholder` remains opaque on white fields.
- **Control Feedback:** field borders, selection pairs, secondary button states, disabled tokens, and the idle badge express interaction without changing the palette.
- **Supporting Surfaces:** `notice-*`, `terms-surface`, `table-header`, `table-grid`, and `preview-note` distinguish information, scrollable terms, tables, and browser-preview context.

**The State Label Rule.** Operational color accompanies an explicit text label; it never replaces the state description.

## Typography

**Desktop Font:** Noto Sans, requested through Qt with its platform fallback. The application sets a base font (10 pt); the widget stylesheet establishes the visible body size through `desktop-body`. Line height and letter spacing remain native Qt defaults.

**Visitor Font:** `system-ui, sans-serif`; no downloaded font assets. Body text uses `portal-body`. Semantic headings retain browser bold weight; only size, line height, and tracking are explicitly customized.

### Hierarchy
- **Desktop title / brand / preview:** `desktop-title`, `desktop-brand`, and `desktop-preview-title` establish page, product, and visitor-summary hierarchy.
- **Desktop section / label / small:** `desktop-section` names preview sections; `desktop-label` covers buttons, group titles, badge, and table headers. `desktop-small` covers rail and preview footnotes.
- **Visitor title / brand:** `portal-title` is the main heading; `portal-title-small` changes only its size at the mobile breakpoint. `portal-brand` identifies the network beside the mark.
- **Visitor body / label / action / footer / preview:** corresponding tokens separate content, field labels, the confirmation action, mode information, and preview status. Agreement copy uses regular body weight.

## Layout

**Desktop:** initial window (1160×800), supported minimum (900×660). A fixed rail (198 px) sits beside a growing workspace. Rail margins are (16/26/16/22 px); workspace margins are (28/24/28/20 px), with a group gap from `spacing.group`. The header, state strip, and footer remain outside scrolling page content. The Start/Stop button has a minimum width (145 px).

The hotspot page retains adjacent form and preview columns at both checked sizes, using stretch proportions (3:2) and `spacing.column-gap`. Both columns scroll vertically. Hotspot and internet form rows wrap when long, fields grow, and adapter/uplink combos bound their minimum content length (12 characters). At the supported minimum, controls fit without horizontal form scrolling; narrow native field text may elide. Other pages use the same shell with grouped editors, a device table, or diagnostics/log panes. Multiline portal editors range from (100–140 px) high.

**Visitors:** one centered card, maximum border-box width (480 px), with body padding (56 px 20 px), card padding from `spacing.portal-panel`, and a form gap from `spacing.portal-gap`. At viewport widths up to (420 px), body padding becomes (24 px 14 px), card padding (26 px 22 px), and the title uses `portal-title-small`. The document scrolls naturally; header, title, message, terms, and button labels wrap long content anywhere. No web-style rail collapse or desktop stacking breakpoint is implemented.

## Elevation & Depth

The desktop is flat: white panels, fine borders, and tonal state surfaces create separation without shadows. Visitor cards alone use a subtle ambient shadow (`0 8px 28px #24364b12`). Hover and focus change color or outline directly; no custom transition, animation, or motion token is defined.

## Shapes

Controls use `rounded.control`; desktop fields use `rounded.desktop-field`, group boxes and preview frames use `rounded.desktop-panel`, and visitor cards use `rounded.portal-panel`. These implemented exceptions supersede the provisional brief's uniform-corner suggestion. Borders are normally (1 px), with thicker focus treatment described below.

The bundled mark is a rounded blue square: SVG view box (64×64), rect radius (14 units), and white round-ended strokes (3.5 units). It displays at (34 px) in the rail, (44 px) in the desktop preview, and (48 px) on visitor pages. Navigation SVGs use (24×24) view boxes, rounded strokes (1.8 units), and display at (20 px). Combo arrows display at (12 px); spin arrows at (10 px). Use the actual assets rather than emoji or icon-font substitutes.

## Components

### Buttons
Desktop actions are compact and conventional. Primary and secondary tokens define their resting surfaces; secondary hover changes background and border, and pressed changes background. Qt focus thickens the blue border (2 px) and reduces padding to (9 px 14 px) to retain size. Primary hover darkens blue; unavailable actions use the implemented disabled tokens. Start becomes Stop while a session is busy and is actionable during the running state; configuration groups are disabled while busy.

Visitor confirmation buttons fill their grid column with a minimum height (48 px), shared blue, and distinct hover/active/disabled backgrounds. Keyboard focus uses an outline (3 px) with offset (3 px). Links remain underlined, with underline offset (3 px); the return link adds vertical padding (12 px). The custom example initially disables confirmation while preparing its form, then enables it or displays a reload instruction.

### Inputs / Fields
Qt line edits, combos, spin boxes, and plain-text editors share white surfaces, fine field borders, and selection colors. Focus uses a blue border (2 px) with padding reduced from (8 px) to (7 px). Editable placeholders use opaque `placeholder`; disabled line edits/combos/spins use the disabled surface and placeholder-colored text. Checkboxes retain native Qt behavior.

Visitor text fields are full width and at least (48 px) high; the caret is blue and placeholders are opaque. Browser-visible focus uses the same offset outline as buttons. The terms checkbox is (19×19 px), has blue accent, and aligns to the first line of wrapped agreement text. Required fields and acceptance retain native browser validation.

### Navigation
The Qt list contains Hotspot, Portal page, Devices, Diagnostics, and About, with labels and SVG icons. Items use padding (14 px 10 px), bottom margin (5 px), and list spacing (2 px). Selected items use `rail-selected` with white text; hover uses `rail-hover`; focus adds the pale-blue border (1 px). The rail stays fixed at the supported desktop minimum.

### Cards / Containers
Desktop group boxes have a fine border, title inset (14 px), top margin (13 px), and `desktop-panel` padding. The visitor-summary frame instead has padding (24 px 28 px 24 px 24 px) and a group gap (16 px). It is a textual summary, including at most (400 characters) of message content; browser preview presents the complete page.

Visitor cards use `portal-card`; their header gap is (14 px) and bottom margin (32 px). Message bottom spacing is (28 px). The footer has a top divider, top padding (20 px), and top margin (28 px). The custom example reuses this stylesheet and mark; arbitrary operator-supplied websites retain their own styling.

### State, Notices, and Terms
The session badge keeps its `desktop-state` border, padding, and shape while changing background/text for Stopped, Starting…, Running, Stopping…, or Needs attention. The adjacent strip separately states hotspot, portal, and sharing status. Notices use pale blue with a fine border and padding (12 px). Devices use a read-only, row-selectable table with stretch columns and clear empty-session copy; diagnostics retain plain-text panes.

Visitor errors use the error pair, a red-tinted border, padding (12 px), and `role="alert"`, followed by the form for correction. Success replaces the form with a return link and explicit offline or timed-internet copy. Terms use `portal-terms`, a maximum height (240 px), vertical overflow, and preserved line breaks. Browser preview adds a centered note above the card. Offline footers explicitly state that no internet connection is provided.

## Do's and Don'ts

### Do:
- **Do** preserve native Qt controls, keyboard focus, and conventional form grouping.
- **Do** retain the persistent session state, stage strip, and footer actions across desktop pages.
- **Do** keep hotspot controls within the 900×660 minimum viewport, with vertical scrolling and the adjacent preview.
- **Do** use bundled SVGs and system fonts so the interface works offline.
- **Do** label operational states and distinguish local content from internet access.
- **Do** retain Uzair attribution and formal project voice.

### Don't:
- **Don't** replace the approved utility layout with a decorative or browser-style operator interface.
- **Don't** use emojis or icon fonts in place of vector assets.
- **Don't** unify the implemented field, control, desktop-panel, and visitor-card corner sizes.
- **Don't** remove opaque placeholders or visible keyboard-focus treatments.
- **Don't** require disabled built-in title/button fields when the custom website template is selected.
