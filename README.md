# Claude
Trade
https://www.tradingview.com/

---

## Sip — Daily Hydration (Apple-style app concept)

Open `index.html` in any browser to view the interactive prototype, rendered inside an iPhone-shaped frame.

### Concept
A single-purpose hydration tracker that feels native to iOS — addresses a universal daily need with a UI that rewards repeated taps throughout the day.

### Features
- **Today ring** — animated progress ring with a blue gradient, live ml + percentage readout.
- **One-tap logging** — quick-add tiles for Glass (200 ml), Bottle (350 ml), Large (500 ml), and Custom.
- **Undo toast** — every log surfaces an instant undo; tap freely without punishment.
- **Weekly bars** — today highlighted in amber, under-goal days greyed, bars animate in on load.
- **Streak + average** — gentle motivation, no gamification noise.
- **Reminders** — morning kickstart, midday top-up, evening wind-down, with iOS toggle switches.
- **Tab bar** — Today · Trends · History · Settings, with a frosted blur background.

### Design language
- SF Pro system stack via `-apple-system`.
- iOS spacing: 18 px corner radius for cards, 24 px for the hero, 100 px pill for the toast.
- Light + dark mode via `prefers-color-scheme`.
- Real device chrome: notch, status bar (signal / wi‑fi / battery), home indicator.
- Layered soft shadow on every elevated card.
- Springy `cubic-bezier(.2,.8,.2,1)` motion on the ring, toast, and bars.
- Haptic-feeling micro-interactions: scale-down on press, ring pop on log, `navigator.vibrate` where supported.
