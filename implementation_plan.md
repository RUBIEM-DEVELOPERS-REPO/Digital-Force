# $50 Million Enterprise UI/UX Implementation Plan

This plan details the technical execution of the Digital Force UI/UX Master Prompt.

## User Review Required

> [!CAUTION]
> **Dependency Addition:** We will install `framer-motion` to handle the complex, premium animations (page transitions, micro-hover states, neural processing animations). Please approve this addition.
> **Route Deletion:** The `/app/media` and `/app/training` routes will be completely removed and consolidated into a single `/app/knowledge` route.

## Proposed Changes

### 1. Global Setup & Design Tokens
#### [MODIFY] package.json
- Add `framer-motion` for enterprise-grade animations.

#### [MODIFY] globals.css
- Refine existing CSS variables to exact match the "Obsidian & Neon" palette.
- Replace generic `animate-pulse` with custom `framer-motion` integrated classes.
- Ban default scrollbars completely; implement the sleek, 1px translucent purple scrollbar.

### 2. Branding & Navigation 
#### [MODIFY] Sidebar.tsx
- **Name scrubbing:** Change all "ASMIA" text to "Digital Force".
- **Iconography:** Audit and switch all emoji-based icons to `lucide-react`.
- **Navigation Links:**
  - Rename "Mission Control" -> "Command Center"
  - Rename "Chat" -> "Neural Link"
  - Merge "Media" & "Training" links into a single "Knowledge" link.
- **Visuals:** Apply the `glass-panel` aesthetic strictly. The active state will use a glowing subtle left border.

### 3. The Central Feature Overhaul
#### [NEW] app/knowledge/page.tsx
- Create the unified "Knowledge Core".
- Add an inline renaming component for media/notes.
- Implement a split-pane or dual-tab internal view to handle both raw text ingestion and media uploads seamlessly in one UI space.
- Add visual indicators for "Semantic Search" readiness.

#### [DELETE] app/media/page.tsx
#### [DELETE] app/training/page.tsx
- Both sub-apps are eradicated to favor the unified Knowledge hub.

### 4. Component Refinements
#### [MODIFY] app/page.tsx (Landing Page)
- Completely strip the current page.tsx. 
- Implement a dark, cinematic hero section with an animated mesh background.
- Emphasize the "Deploy Agency" / Sign In authentication gateways.

#### [MODIFY] app/chat/page.tsx
- Replace standard chat styling with the "Neural Link" aesthetic.
- Add the Framer Motion "Processing Hex" or waveform animation block for when the agent is waiting.
- Style the Web Search / Tool Execution blocks as high-end glowing cards rather than text snippets.

#### [MODIFY] app/analytics/page.tsx
- Apply the data-visualization updates. Tooltips will be converted to glassmorphic panels. Gradients will fade to exactly zero opacity at the baseline.

#### [MODIFY] app/goals/page.tsx & app/skills/page.tsx
- Rebuild the grid cards to feature subtle 3D hover tilts and thin glowing progress bars.
- Replace all text that sounds "basic" (like "Goal is running") to "Execution Protocol Active".

## Open Questions

> [!IMPORTANT]
> 1. Do you have a specific color preference for the "Neon" accents, or should I proceed with the deep Purple (`#7C3AED`) and Cyan (`#06B6D4`) already mapped out in your globals?
> 2. For the Landing Page, should the "Sign In" simply link to `/login` or would you prefer a modal overlay?

## Verification Plan

### Automated Tests
- Run Next.js build validation (`npm run build`) to ensure no broken links after deleting `/media` and `/training`.

### Manual Verification
- Compile development server and inspect the UI visually.
- Verify Framer Motion animations trigger properly on mount.
- Validate the inline-renaming capability in the new **Knowledge** hub.
