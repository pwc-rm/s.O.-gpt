---
name: sO Agent Cockpit Narrative
colors:
  surface: '#f8f9fa'
  surface-dim: '#d9dadb'
  surface-bright: '#f8f9fa'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f3f4f5'
  surface-container: '#edeeef'
  surface-container-high: '#e7e8e9'
  surface-container-highest: '#e1e3e4'
  on-surface: '#191c1d'
  on-surface-variant: '#5b403f'
  inverse-surface: '#2e3132'
  inverse-on-surface: '#f0f1f2'
  outline: '#906f6e'
  outline-variant: '#e4bdbb'
  surface-tint: '#bc1029'
  primary: '#b50625'
  on-primary: '#ffffff'
  primary-container: '#d92b3a'
  on-primary-container: '#fff6f5'
  inverse-primary: '#ffb3b0'
  secondary: '#5f5e61'
  on-secondary: '#ffffff'
  secondary-container: '#e4e1e6'
  on-secondary-container: '#656467'
  tertiary: '#00646a'
  on-tertiary: '#ffffff'
  tertiary-container: '#007f86'
  on-tertiary-container: '#e6fdff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#ffdad8'
  primary-fixed-dim: '#ffb3b0'
  on-primary-fixed: '#410006'
  on-primary-fixed-variant: '#93001b'
  secondary-fixed: '#e4e1e6'
  secondary-fixed-dim: '#c8c5ca'
  on-secondary-fixed: '#1b1b1e'
  on-secondary-fixed-variant: '#47464a'
  tertiary-fixed: '#94f1f9'
  tertiary-fixed-dim: '#77d5dc'
  on-tertiary-fixed: '#002022'
  on-tertiary-fixed-variant: '#004f54'
  background: '#f8f9fa'
  on-background: '#191c1d'
  surface-variant: '#e1e3e4'
  sidebar-bg: '#18181b'
  sidebar-text: '#ffffff'
  text-main: '#1f2937'
  text-muted: '#6b7280'
  border-subtle: '#e5e7eb'
  success-green: '#10b981'
  warning-amber: '#f59e0b'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: '1.2'
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.3'
  headline-sm:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: '1.4'
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.5'
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.5'
  label-bold:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: 0.05em
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: '1.2'
  display-lg-mobile:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '700'
    lineHeight: '1.2'
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  sidebar-width: 260px
  gutter: 24px
  margin-page: 32px
  stack-sm: 8px
  stack-md: 16px
  stack-lg: 24px
---

## Brand & Style

This design system is built for an enterprise-grade AI governance and marketplace environment. The aesthetic is **Corporate Modern with a Minimalist focus**, prioritizing clarity, high information density, and functional precision. 

The interface reflects the reliability of s.Oliver’s heritage while embracing a forward-looking, technical capability. We utilize a flat design language characterized by crisp edges, purposeful whitespace, and a limited but impactful color palette. The goal is to evoke a sense of controlled power—allowing administrators and users to navigate complex AI metadata and governance tools without cognitive overload.

Visual emphasis is placed on the **s.Oliver Red** as a primary driver of action and status, contrasted against a deep, industrial zinc sidebar to establish a strong structural hierarchy.

## Colors

The palette is anchored by the signature **s.Oliver Red (#d92b3a)**. This is the primary "action" color, reserved for buttons, active navigation states, and critical interaction points. 

The sidebar uses **Zinc-900 (#18181b)** to create a distinct workspace anchor, separating global navigation from the content area. Backgrounds are kept light—primarily **White (#ffffff)** for cards and surface areas, with **Gray-50 (#f9fafb)** used for the global page background to provide subtle contrast for the white cards.

Text hierarchy is maintained using **Gray-800 (#1f2937)** for primary body copy to ensure high legibility and a softer appearance than pure black, while semantic colors (green/amber) are introduced specifically for KPI trend indicators and AI agent status badges.

## Typography

We use **Inter** exclusively to achieve a systematic, utilitarian aesthetic that excels in data-heavy environments. 

The type scale is designed for legibility in complex layouts. Headlines use a tighter letter-spacing and heavier weights to stand out against UI chrome. Body text is optimized at 14px (body-md) for the majority of data-grid and agent card content to maximize information density without sacrificing readability. Labels use a slightly heavier weight (Medium or Semi-Bold) and, in some cases, small-caps or increased tracking for metadata tags to distinguish them from interactive body text.

## Layout & Spacing

The design system utilizes a **12-column fluid grid** for the main content area, with a **fixed sidebar** width of 260px. 

Margins and gutters are generous (24px to 32px) to provide "breathing room" for dense AI performance data. We follow an 8px spacing system (`stack-sm`, `stack-md`, etc.) to ensure vertical rhythm. 

On mobile and tablet devices, the sidebar collapses into a hamburger menu or a slim icon bar. Content cards reflow from multi-column grids to a single-stack layout, and page margins reduce to 16px to conserve horizontal real estate.

## Elevation & Depth

To maintain a "Minimalist Professional" style, we avoid heavy drop shadows. Instead, we use **Tonal Layers** and **Subtle Shadows**:

1.  **Level 0 (Background):** Gray-50.
2.  **Level 1 (Cards/Tables):** White surface with a `shadow-sm` (0 1px 2px 0 rgba(0, 0, 0, 0.05)) and a subtle 1px border (#e5e7eb).
3.  **Level 2 (Hover States/Popovers):** White surface with `shadow-md` (0 4px 6px -1px rgba(0, 0, 0, 0.1)) to indicate interactivity.

This creates a flat, "sheet-based" architecture where depth is communicated through stacking and extremely soft outlines rather than dramatic lighting effects.

## Shapes

The design system uses a **Soft (0.25rem)** roundedness approach. 

This subtle rounding keeps the UI feeling modern and approachable without losing the "serious" enterprise character of sharp corners. Standard components like buttons and input fields use the 4px base radius. Larger containers, such as Agent Cards, may use the `rounded-lg` (8px) setting to create a softer visual grouping for metadata. Status badges (e.g., "Active", "Beta") are the only exception, utilizing a fully rounded pill-shape to distinguish them from functional buttons.

## Components

### Sidebar Navigation
The sidebar is the primary navigation hub. It uses the dark Zinc-900 background. Active links are indicated by a 4px vertical s.Oliver Red bar on the left edge and white text. Icons should be line-based and minimalist.

### Agent Cards
Cards must contain the Agent name (Headline-sm), a brief German description (Body-md), and a footer area for metadata badges (e.g., "KI-Modell", "Abteilung"). The entire card should have a subtle hover transition that increases the shadow slightly.

### KPI Cards
Key Performance Indicators use large display typography for the primary metric. To the right or below the metric, a "Trend Indicator" is required: a small colored arrow (Up-Green/Down-Red) accompanied by a percentage.

### Buttons
*   **Primary:** Solid s.Oliver Red with White text.
*   **Secondary:** White background with s.Oliver Red border and text.
*   **Tertiary:** Transparent background with Gray-800 text.

### Data Tables
Tables are used for governance logs. They feature a clean header with Gray-50 background and 1px bottom borders. Rows have a subtle hover highlight.

### Input Fields & Search
Search bars are prominent in the marketplace. Use a light gray border (#e5e7eb) that turns s.Oliver Red on focus. Include a "Search" placeholder in German (*Suchen...*).