# Task 6.19: Semantic HTML and ARIA Labels Implementation Plan

## Requirements
- Use semantic HTML elements (nav, main, section, article, button)
- Add ARIA labels for complex interactive components
- Add ARIA live regions for dynamic content updates
- Ensure all form inputs have associated labels
- Add text alternatives for all images and icons
- Requirements: 30.1, 30.4, 30.6, 30.7, 30.9

## Current State Analysis

### Components Needing Updates

1. **Layout.tsx** ✓ Already has semantic structure
   - Uses semantic `<header>`, `<aside>`, `<main>` via child components
   - Has SkipNavigation component

2. **Header.tsx** ✓ Mostly compliant
   - Uses semantic `<header>` element
   - Has aria-label on buttons
   - Connection status needs aria-live region

3. **Sidebar.tsx** ✓ Mostly compliant
   - Uses semantic `<nav>` element
   - Navigation items are buttons (good for accessibility)
   - Needs aria-current for active page

4. **MainContent.tsx** - Needs review
   - Should use semantic `<main>` element

5. **MarketDataGrid.tsx** - Needs improvements
   - Table structure is good but needs:
     - aria-label on table
     - aria-sort attributes on sortable headers
     - aria-live region for real-time updates
     - Better mobile card accessibility

6. **ActiveSignalsPanel.tsx** - Needs improvements
   - Form inputs need associated labels
   - Filter section needs semantic structure
   - Signal cards need article elements
   - Needs aria-live for signal updates

7. **PositionsPanel.tsx** - Needs improvements
   - Table needs aria-label
   - Confirmation dialog needs proper ARIA dialog role
   - Portfolio metrics need semantic structure
   - Needs aria-live for P&L updates

8. **Dashboard.tsx** - Needs improvements
   - Stats cards need semantic structure (section/article)
   - Headings need proper hierarchy

## Implementation Plan

### Phase 1: Core Layout Components
1. Update MainContent.tsx to use `<main>` element
2. Add aria-current to Sidebar navigation
3. Add aria-live region to Header connection status

### Phase 2: Data Display Components
4. Add semantic HTML to MarketDataGrid (table aria-labels, aria-sort)
5. Add aria-live region for market data updates
6. Improve mobile card accessibility

### Phase 3: Interactive Components
7. Add proper labels to form inputs in ActiveSignalsPanel
8. Add aria-live regions for signal updates
9. Use article elements for signal cards
10. Add proper ARIA dialog role to PositionsPanel confirmation

### Phase 4: Page-Level Components
11. Add semantic structure to Dashboard page
12. Ensure proper heading hierarchy
13. Add aria-labels to stat cards

### Phase 5: Icons and Images
14. Ensure all SVG icons have aria-hidden="true" (decorative)
15. Add aria-label to icon-only buttons
16. Review all images for alt text

## ARIA Patterns to Implement

### Live Regions
- Market data updates: `aria-live="polite"`
- Signal updates: `aria-live="polite"`
- Position P&L updates: `aria-live="polite"`
- Connection status: `aria-live="assertive"`
- Alerts/notifications: `aria-live="assertive"`

### Navigation
- Current page: `aria-current="page"`
- Navigation landmark: `<nav aria-label="Main navigation">`

### Tables
- Sortable headers: `aria-sort="ascending|descending|none"`
- Table caption: `<caption>` or `aria-label`

### Dialogs
- Modal dialogs: `role="dialog"`, `aria-modal="true"`, `aria-labelledby`

### Forms
- All inputs: associated `<label>` or `aria-label`
- Required fields: `aria-required="true"`
- Error messages: `aria-invalid="true"`, `aria-describedby`

### Buttons
- Icon-only buttons: `aria-label`
- Toggle buttons: `aria-pressed`
- Expandable sections: `aria-expanded`

## Testing Checklist
- [ ] All interactive elements keyboard accessible
- [ ] Screen reader announces page changes
- [ ] Live regions announce updates appropriately
- [ ] All form inputs have labels
- [ ] All images/icons have text alternatives
- [ ] Proper heading hierarchy (h1 → h2 → h3)
- [ ] ARIA attributes validated
