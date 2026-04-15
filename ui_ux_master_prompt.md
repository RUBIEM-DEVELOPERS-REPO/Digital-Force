# DIGITAL FORCE: THE $50 MILLION ENTERPRISE UI/UX MASTER PROMPT

**Role Definition:**
You are to assume the persona of an elite, Silicon Valley Lead Product Designer and Frontend Architect. Your sole mission is to execute a relentless, uncompromising overhaul of the current application. It must evolve from a functional prototype into **Digital Force**—a breathtaking, $50 million tier enterprise SAAS platform. The final product must evoke feelings of bleeding-edge technological supremacy, unwavering trust, and awe-inspiring aesthetic precision.

**The Golden Rule:** 
*If it looks "free", default, or even merely "good", it is a failure.* Every single element—down to the scrollbars, the focus rings, and the micro-delays on hover—must be architected to feel ultra-premium.

---

## 1. BRANDING, NAMING & IMMERSIVE AESTHETIC

### 1.1 Brand Identity Migration
- **Name Scrubbing:** Annihilate the acronym "ASMIA" from the entire codebase. The entity is exclusively **"Digital Force"**.
- **The Tagline:** Implement the tagline: *"Autonomous Digital Media Intelligent Agency"*.
- **Logo Execution:** Integrate the attached primary logo icon. The logotype (the text "Digital Force") must be custom-styled using a premium geometric font, featuring a very subtle polished-metal or holographic gradient sheen. It should command respect.

### 1.2 "The Obsidian & Neon" Design Language
- **Depth & Dimension (Glassmorphism & Neumorphism):** Discard flat, lifeless backgrounds. Implement multi-layered translucency (backdrop-blur) combined with deep, rich, dark mode tones (e.g., #0B0E14 to #151A23). Cards should look like polished obsidian resting on a subtly pulsing background.
- **Lighting & Glows:** Instead of hard borders, use 1px inner borders (`box-shadow: inset 0 1px 0 rgba(255,255,255,0.05)`) and soft external glows to indicate active states or AI processing.
- **Typography of Power:** Replace default fonts with high-end, highly legible typography (e.g., `Inter`, `Outfit`, `Geist`, or `Plus Jakarta Sans`). Enforce a rigorous hierarchy:
  - Mega-Headers for impact.
  - Subdued, low-contrast text (`text-gray-400`) for secondary information to avoid overwhelming the user.
  - Generous letter-spacing (tracking) on uppercase labels.

### 1.3 The Absolute Eradication of Emojis
- **Zero Emojis Policy:** Emojis are banned. They break the $50M illusion immediately.
- **Iconography System:** Replace all emojis or default icons with a unified, clean SVGs library (like Lucide, Phosphor, or custom Framer Motion icons). All icons must have the exact same stroke width (e.g., `1.5px`) and corner radius.
- **Animated Assets:** For key actions (loading, processing, saving), custom-design and animate icons smoothly instead of relying on static glyphs.

---

## 2. STRUCTURAL & LAYOUT PARADIGM SHIFT

### 2.1 Navigation & The Command Center
- **Sidebar Overhaul (`/components/Sidebar.tsx`):**
  - Transform the clunky sidebar into a sleek, floating glass panel with hover-expand dynamics.
  - **No More "Mission Control":** Rename basic tabs to high-end equivalents: "Command Center", "Operations", "Neural Nexus", "Grid", or "Overview". Never use basic functional text.
  - Use smooth active-state indicators (e.g., a glowing vertical line that animates to the active tab via Framer Motion's `layoutId`).
- **Global Context Header:** The top bar must be a frosted glass navbar that fades perfectly into the background, housing a minimal, high-end user profile dropout and a pulsing global search bar (keyboard shortcut driven: `Cmd+K`).

### 2.2 The Great "Knowledge" Consolidation
- **Merge `/media` and `/training`:** Destroy the archaic division. Combine the Knowledge Base and Media Library into a single, omnipotent module called **"Knowledge"**.
  - This is the central brain. Both raw training ingestion (text, PDFs) and media assets (images, videos) flow into this single intelligence pool.
  - **CRUD Operations:** Allow renaming of any uploaded media and notes inline, without opening disruptive modal windows (use click-to-edit with beautiful focus states).
  - **Semantic AI Search:** Design the interface so users clearly understand that agents are accessing this data via semantic search. Show visual "cortex connections" or search relevance scores next to injected knowledge.

### 2.3 The Ultimate Enterprise Landing Page (`/app/page.tsx` & `/app/login`)
- **The Hook:** Create a completely new, dedicated out-of-the-app Landing Page for Digital Force. It must stop users in their tracks.
- **Hero Section:** A dark, cinematic hero section with a dynamic, reactive background (e.g., a slow-moving, dark fluid mesh gradient, or a 3D particle constellation).
- **Onboarding Pipeline:** Drive users towards elegantly styled "Sign In" / "Deploy Agency" gates. Authentication must feel secure and elite, utilizing biometric-style glowing fingerprint or facial recognition UI motifs (even if just for aesthetic loading).

---

## 3. COMPONENT-LEVEL MASSIVE TRANSFORMATIONS

### 3.1 The Autonomous AI Chat (`/app/chat`)
- Transform the basic chat log into a **"Neural Link Interface"**.
- User messages should be clean, solid, and constrained down. AI responses must stream in smoothly with a very subtle typing caret.
- **"Agent Thinking" States:** Do not use three dot spinners. Create an animated "processing" block that visually implies massive computational power (e.g., cycling through terminal-style hex codes or a smooth waveform) while waiting for the LLM.
- **Action Blocks:** When the AI executes a command (e.g., posts to social media, scrapes a page), it should render as an interactive, compact "Execution Card" with live status lights (Red/Yellow/Green), not just a block of text.

### 3.2 Immersive Analytics (`/app/analytics`)
- **Data as Art:** Standard Bar/Line charts are forbidden. Implement heavily customized visualizations (using tools like Recharts customized to the extreme).
- Gradients under line charts should fade to 0% opacity at the bottom.
- Hovering over data points should trigger a magnetic tool-tip that snaps to the point, with a glassmorphic background.
- Big number KPIs must "count up" quickly upon mounting, rather than just appearing.

### 3.3 Skill & Goal Management (`/app/skills`, `/app/goals`)
- **Card Grids:** Represent Skills and Goals as premium "Modules" or "Directives". Each card should have a very subtle 3D tilt effect on hover.
- Progress bars should no longer be chunky blocks—use razor-thin, brilliantly glowing lines along the bottom edge of the cards.
- Add an "Activation Protocol" animation when a new goal/skill is assigned, making the user feel like they are literally programming a digital brain.

---

## 4. THE $50M INVISIBLE DETAILS (ANIMATION & UX)

- **Framer Motion Everywhere:** Content must never simply appear. Lists should stagger-fade in `[0.1s overlap]`. Pages must slide in gracefully.
- **Skeleton Shimmers:** Implement highly stylized skeleton loaders for every asynchronous request. The shimmer should be a slanted (`45deg`) gradient passing over a base color that perfectly matches the final content background.
- **Haptic-Feedback Visuals:** When a user clicks a primary button, it should physically depress slightly (scale: `0.98`) and emit an instantaneous, soft outer glow.
- **Toast/Notification Physics:** Error, warning, and success alerts must slide in from the bottom-right completely detached from edges, floating with a heavy drop-shadow and a smooth spring physics curve.

---

## 5. THE MASTER EXECUTION CHECKLIST FOR THE AI ENGINEER

- [ ] **Eradication & Baptism:** Sweep entire codebase (Next.js `/app` & `/components`), deleting "ASMIA", replacing with "Digital Force". Add the new tagline everywhere necessary.
- [ ] **Design Token Injection:** Overhaul `tailwind.config.ts` entirely. Inject complex dark-mode color scales, box-shadow presets (glass, neon, deep), and typography variables.
- [ ] **Emoji Genocide:** Identify and delete every emoji, replacing them with consistent Lucide/Hero SVG icons.
- [ ] **Sidebar Overhaul:** Rebuild `/components/Sidebar.tsx` into a collapsing/expanding glassmorphic command deck. Update all navigation nomenclature to tier-1 enterprise standards. 
- [ ] **Knowledge Convergence:** Delete the `/app/media` and `/app/training` silos. Architect a single `/app/knowledge` universal intelligence hub with inline editing and semantic search previews.
- [ ] **The Breathtaking Gateway:** Completely rewrite `/app/page.tsx` and the Login flow into a cinematic, fluid Landing Page.
- [ ] **Component Polish Pipeline:** Iteratively inject Framer Motion page transitions, micro-hover states, skeleton loaders, and interactive "Thinking" states into the Chat, Analytics, Skills, and Goals views.
- [ ] **Final QA Audit:** The AI must explicitly verify that NO stock browser default scrollbars, heavy borders, or instant-snap content mounts remain anywhere in the app.
