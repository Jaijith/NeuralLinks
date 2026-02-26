# Visual Testing Guide for NeuralLinks Application

## Overview
This document provides a comprehensive testing checklist for the Maya/Sense world modes and Classic/Immersive view modes in the NeuralLinks application.

## Prerequisites
1. Navigate to http://localhost:3000
2. **Log in to the application** (required for testing)
3. Ensure you can see the home feed with the header

## Testing Methodology

### Mode Combinations to Test
The application has 3 main mode combinations:
1. **Sense World** (default) - Light mode only
2. **Maya World + Classic** - Light mode with subtle atmospheric effects
3. **Maya World + Immersive** - Dark cosmic mode with full ambient effects

### Toggle Locations
- **World Mode Toggle**: Top-right header area
  - Shows "Sense" (blue with Globe icon) or "Maya" (purple with Sparkles icon)
- **View Mode Toggle**: Only visible in Maya World, next to World toggle
  - Shows "Classic" (Sun icon) or "Immersive" (Sparkles icon)

---

## STEP 1: Initial State Check

### What to Look For:
- [ ] Can you see the application header at the top?
- [ ] Can you see the "Sense" or "Maya" toggle button in the top-right?
- [ ] What is the current world mode? (Note: Sense or Maya)
- [ ] If in Maya world, what is the current view mode? (Classic or Immersive)

### Take Screenshot: `01-initial-state.png`

---

## STEP 2: Sense World (Default Light Mode)

### If you're in Maya world, click the "Maya" button to switch to "Sense"

### Visual Checklist:
- [ ] **Background**: Light gradient (blue-50 → white → slate-50)
- [ ] **Header**: Light background with subtle transparency
- [ ] **Cards/Posts**: White or light glass with subtle shadows
- [ ] **Text**: Dark/black color, easily readable
- [ ] **Icons**: Gray/dark colored
- [ ] **Buttons**: Normal light theme styling
- [ ] **No View Mode Toggle**: Should NOT see Classic/Immersive toggle

### Issues to Report:
- Text readability problems
- Color inconsistencies
- Broken layouts
- Any dark mode elements appearing

### Take Screenshot: `02-sense-world.png`

---

## STEP 3: Maya World - Classic Mode

### Click the "Sense" button to switch to "Maya" world

### Visual Checklist:
- [ ] **Background**: Still light gradient, similar to Sense
- [ ] **Atmospheric Effects**: Subtle glowing edges or particles (very subtle)
- [ ] **View Mode Toggle**: NOW VISIBLE next to World toggle
- [ ] **View Toggle Shows**: "Classic" with Sun icon
- [ ] **Overall Appearance**: Should look very similar to Sense world
- [ ] **Cards/Posts**: Still light colored
- [ ] **Text**: Still dark/readable

### Issues to Report:
- Missing view mode toggle
- Overly bright or distracting atmospheric effects
- Any visual glitches or artifacts
- Layout shifts from Sense mode

### Take Screenshot: `03-maya-classic.png`

---

## STEP 4: Maya World - Immersive Mode

### Click the "Classic" button to switch to "Immersive" mode

### Visual Checklist:

#### Background & Atmosphere:
- [ ] **Background**: Dark cosmic/space theme (deep blue/purple/black gradients)
- [ ] **Animated Elements**: Moving stars, particles, or cosmic effects
- [ ] **Overall Vibe**: Mystical, space-like, immersive

#### Header:
- [ ] **Background**: Dark with glassmorphism (semi-transparent dark)
- [ ] **Border**: Subtle blue/purple glow
- [ ] **Text/Icons**: Light blue or white colored
- [ ] **Toggle Buttons**: Dark backgrounds with colored borders

#### Cards & Content:
- [ ] **Post Cards**: Dark semi-transparent (rgba 12,15,25 with ~70% opacity)
- [ ] **Card Borders**: Subtle white/blue borders (very faint)
- [ ] **Sticky Cards** (stories, create post): Slightly more opaque (~80%)
- [ ] **Card Shadows**: Darker, more pronounced

#### Typography:
- [ ] **Main Text**: White or very light colored (~90% white)
- [ ] **Headings**: White, clearly visible
- [ ] **Muted Text** (timestamps, metadata): Light gray (~65% white opacity)
- [ ] **Link Text**: Light colored, visible
- [ ] **All text readable** against dark backgrounds

#### UI Elements:
- [ ] **Input Fields**: Dark backgrounds with white borders
- [ ] **Placeholder Text**: Visible but subtle (~40% white opacity)
- [ ] **Buttons**: Dark or semi-transparent with light text
- [ ] **Icons/SVG**: Light colored (~70% white opacity)
- [ ] **Hover States**: Subtle glow or highlight effects

#### Colored Elements (Should Preserve Colors):
- [ ] **Badges** (yellow, purple, blue backgrounds): Colors maintained
- [ ] **Badge Text**: Original dark text on light badges
- [ ] **Colored Buttons**: Keep their original colors
- [ ] **User Avatars**: Normal colors, not washed out

#### Sidebars:
- [ ] **Left Sidebar**: Dark styling consistent with cards
- [ ] **Right Sidebar**: Dark styling, friend list readable
- [ ] **Sidebar Text**: Light colored, good contrast

### Common Issues to Check:

#### Text Readability:
- [ ] No black or dark gray text on dark backgrounds
- [ ] Timestamps and metadata visible
- [ ] Button text clearly readable
- [ ] Comment text visible

#### Contrast Problems:
- [ ] Cards not too transparent (text should be clear)
- [ ] Borders visible but not harsh
- [ ] Icons not too dim

#### Layout Issues:
- [ ] No overlapping elements
- [ ] Proper spacing maintained
- [ ] Cards properly aligned
- [ ] No broken grid layouts

#### Color Consistency:
- [ ] Dark theme throughout (no light mode leaks)
- [ ] Consistent blue/purple accent colors
- [ ] No harsh white backgrounds
- [ ] Smooth color transitions

### Take Screenshot: `04-maya-immersive.png`

---

## STEP 5: Page-by-Page Testing (In Immersive Mode)

Test each page and note visual issues:

### Home Page (`/home`)
- [ ] Stories row visible and styled correctly
- [ ] Create post card dark themed
- [ ] Posts feed readable
- [ ] Sidebars dark themed
- **Screenshot**: `05-home-immersive.png`

### Friends Page (`/friends`)
- [ ] Friend list cards dark themed
- [ ] Search bar dark with light text
- [ ] Friend requests section styled
- [ ] Tab navigation visible
- **Screenshot**: `06-friends-immersive.png`

### Search Page (`/search`)
- [ ] Search input dark themed
- [ ] Search results visible
- [ ] Filter options styled
- [ ] Result cards dark
- **Screenshot**: `07-search-immersive.png`

### Settings Page (`/settings`)
- [ ] Settings panels dark
- [ ] Form inputs dark with light text
- [ ] Toggle switches styled
- [ ] Save buttons visible
- **Screenshot**: `08-settings-immersive.png`

### Gallery Page (`/gallery`)
- [ ] Image grid visible
- [ ] Image previews clear
- [ ] Upload button styled
- [ ] Gallery controls visible
- **Screenshot**: `09-gallery-immersive.png`

### Profile Page (`/myprofile`)
- [ ] Profile header dark themed
- [ ] Avatar/banner visible
- [ ] Stats/bio readable
- [ ] Posts section styled
- **Screenshot**: `10-myprofile-immersive.png`

### Missions Page (`/missions`)
- [ ] Mission cards dark themed
- [ ] Progress indicators visible
- [ ] Action buttons styled
- [ ] Mission details readable
- **Screenshot**: `11-missions-immersive.png`

### Other Pages
Test any additional pages like:
- Matches (`/matches`)
- Integrations (`/integrations`)
- Avatar Visualization (`/avatar-visualization`)
- Avatar Control (`/avatar-control`)

---

## STEP 6: Toggle Back to Classic

### From Immersive mode, click "Immersive" button to return to Classic

### Checklist:
- [ ] Smooth transition back to light mode
- [ ] All elements return to light styling
- [ ] No dark mode remnants
- [ ] Page still functional

### Take Screenshot: `12-return-to-classic.png`

---

## STEP 7: Toggle to Sense World

### Click "Maya" button to return to Sense world

### Checklist:
- [ ] View mode toggle disappears
- [ ] Returns to default light theme
- [ ] All elements properly styled
- [ ] No Maya world effects remaining

### Take Screenshot: `13-return-to-sense.png`

---

## STEP 8: Mobile Responsive Testing (Optional)

### Resize browser to mobile width (< 768px)

### Maya Immersive Mode Checklist:
- [ ] Sidebars hidden on mobile
- [ ] Bottom navigation bar visible
- [ ] Bottom nav bar dark themed
- [ ] Cards full width
- [ ] Header compact with toggles accessible
- [ ] Text still readable at small size

### Take Screenshot: `14-mobile-immersive.png`

---

## Issues to Report

For each issue found, please provide:

### Issue Template:
```
Page: [page name]
Mode: [Sense / Maya Classic / Maya Immersive]
Issue Type: [Text Readability / Color / Layout / Contrast / Other]
Description: [detailed description]
Severity: [High / Medium / Low]
Screenshot: [filename]
```

### Common Issue Types:

#### HIGH Severity:
- Text completely unreadable
- Major layout breaks
- Missing critical UI elements
- Application crashes or freezes

#### MEDIUM Severity:
- Text hard to read (poor contrast)
- Minor layout shifts
- Inconsistent styling
- Elements misaligned

#### LOW Severity:
- Subtle color inconsistencies
- Minor visual artifacts
- Hover states not perfect
- Minor spacing issues

---

## Screenshot Naming Convention

Follow this naming pattern for consistency:
- `01-initial-state.png`
- `02-sense-world.png`
- `03-maya-classic.png`
- `04-maya-immersive.png`
- `05-home-immersive.png`
- `06-friends-immersive.png`
- etc.

---

## Expected Visual Themes

### Sense World:
- Light, clean, professional
- Blue accent colors
- High contrast for readability
- Standard social media aesthetics

### Maya Classic:
- Same as Sense but with subtle ambient touches
- Very light atmospheric effects
- Maintains light theme
- Hint of mystical presence

### Maya Immersive:
- Dark, cosmic, space-like
- Blue/purple/indigo color palette
- Semi-transparent dark cards
- Glowing effects and particles
- Mystical, immersive feel
- All text white/light colored

---

## Quick Reference: CSS Specifics

### Immersive Mode Card Backgrounds:
- Regular cards: `rgba(12, 15, 25, 0.70)`
- Sticky cards: `rgba(12, 15, 25, 0.80)`
- Header: `rgba(15, 23, 42, 0.90)`

### Immersive Mode Text Colors:
- Main text: `rgba(255, 255, 255, 0.9)`
- Muted text: `rgba(255, 255, 255, 0.65)`
- Placeholder: `rgba(255, 255, 255, 0.4)`
- Icons: `rgba(255, 255, 255, 0.7)`

### Immersive Mode Borders:
- Cards: `rgba(255, 255, 255, 0.08)`
- Inputs: `rgba(255, 255, 255, 0.15)`
- General borders: `rgba(255, 255, 255, 0.1)`

---

## Automated Testing Script

If you prefer automated screenshot capture after logging in manually, run:

```bash
node test-screenshots-with-auth.js
```

This script will:
1. Open a visible browser
2. Wait for you to log in manually
3. Automatically capture screenshots of all modes and pages
4. Save them to the `screenshots/` directory

---

## Contact & Support

If you encounter any issues during testing or need clarification on expected behavior, please document them with screenshots and detailed descriptions.

Happy testing! 🚀
