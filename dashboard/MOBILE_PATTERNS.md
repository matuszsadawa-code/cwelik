# Mobile Responsive Patterns - Quick Reference

## Common Patterns for OpenClaw Dashboard

### 1. Responsive Grid Pattern

**Use Case:** Stack elements vertically on mobile, multi-column on desktop

```typescript
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
  {items.map(item => (
    <div key={item.id}>{/* Content */}</div>
  ))}
</div>
```

**Breakpoints:**
- Mobile: 1 column
- Tablet (≥768px): 2 columns
- Desktop (≥1024px): 3 columns

---

### 2. Conditional Layout Pattern (Table vs Cards)

**Use Case:** Show table on desktop, cards on mobile

```typescript
{/* Desktop Table */}
<div className="hidden md:block">
  <table className="w-full">
    {/* Table content */}
  </table>
</div>

{/* Mobile Cards */}
<div className="md:hidden space-y-3">
  {items.map(item => (
    <div key={item.id} className="bg-slate-900 border rounded-lg p-4">
      {/* Card content */}
    </div>
  ))}
</div>
```

**Benefits:**
- Prevents rendering unused DOM elements
- Optimized for each screen size
- Better performance

---

### 3. Touch-Friendly Button Pattern

**Use Case:** All interactive elements (buttons, links, tap targets)

```typescript
<button
  className="p-2 rounded-lg hover:bg-white/5 transition-colors touch-manipulation"
  style={{ minWidth: '44px', minHeight: '44px' }}
  aria-label="Descriptive label"
>
  <svg className="w-6 h-6">{/* Icon */}</svg>
</button>
```

**Requirements:**
- Minimum 44x44px tap target (WCAG 2.1 AA)
- `touch-manipulation` CSS for instant feedback
- Clear visual feedback on tap
- Descriptive ARIA labels

---

### 4. Mobile Overlay Sidebar Pattern

**Use Case:** Navigation menu that slides in from the side

```typescript
{/* Backdrop Overlay */}
{isMobileMenuOpen && (
  <div
    className="fixed inset-0 bg-black/60 z-40 md:hidden"
    onClick={() => setMobileMenuOpen(false)}
  />
)}

{/* Sidebar */}
<aside className={`
  fixed md:static inset-y-0 left-0 z-50
  w-64 bg-background-secondary border-r border-slate-700
  transform transition-transform duration-300 ease-in-out
  ${isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
`}>
  {/* Sidebar content */}
</aside>
```

**Features:**
- Smooth slide animation (300ms)
- Dark backdrop overlay
- Click outside to close
- Escape key support
- Auto-close on navigation

---

### 5. Responsive Spacing Pattern

**Use Case:** Adjust padding/margins based on screen size

```typescript
<div className="px-4 sm:px-6 lg:px-8 py-3 sm:py-4 lg:py-6">
  {/* Content */}
</div>
```

**Scale:**
- Mobile: Smaller spacing (px-4, py-3)
- Tablet: Medium spacing (px-6, py-4)
- Desktop: Larger spacing (px-8, py-6)

---

### 6. Responsive Typography Pattern

**Use Case:** Scale text size based on screen size

```typescript
<h1 className="text-xl sm:text-2xl lg:text-3xl font-bold">
  OpenClaw
</h1>

<p className="text-sm sm:text-base lg:text-lg">
  Description text
</p>
```

**Scale:**
- Mobile: Smaller text (text-xl, text-sm)
- Tablet: Medium text (text-2xl, text-base)
- Desktop: Larger text (text-3xl, text-lg)

---

### 7. Mobile Card Layout Pattern

**Use Case:** Display data in card format on mobile

```typescript
<div className="bg-slate-900 border border-slate-800 rounded-lg p-4 touch-manipulation">
  {/* Header Row */}
  <div className="flex items-center justify-between mb-3">
    <div className="flex items-center gap-2">
      <span className="text-base font-bold">{symbol}</span>
      <span className="badge">{status}</span>
    </div>
    <span className="text-base font-bold text-green-500">
      +{change}%
    </span>
  </div>

  {/* Primary Info */}
  <div className="flex items-baseline justify-between mb-2">
    <span className="text-xs text-slate-400">Price</span>
    <span className="text-lg font-mono">${price}</span>
  </div>

  {/* Stats Grid */}
  <div className="grid grid-cols-2 gap-2 text-xs">
    <div className="flex justify-between">
      <span className="text-slate-400">Volume</span>
      <span className="font-mono">${volume}</span>
    </div>
    <div className="flex justify-between">
      <span className="text-slate-400">CVD</span>
      <span className="font-mono">{cvd}</span>
    </div>
  </div>
</div>
```

**Information Hierarchy:**
1. **Header:** Most important info (symbol, status, change)
2. **Primary:** Key metric (price, P&L)
3. **Secondary:** Supporting metrics (volume, CVD)
4. **Action:** Buttons/links at bottom

---

### 8. Responsive Visibility Pattern

**Use Case:** Show/hide elements based on screen size

```typescript
{/* Show only on mobile */}
<div className="md:hidden">
  Mobile-only content
</div>

{/* Show only on tablet and up */}
<div className="hidden md:block">
  Desktop content
</div>

{/* Show only on desktop */}
<div className="hidden lg:block">
  Large screen content
</div>

{/* Hide on mobile, show on tablet+ */}
<span className="hidden sm:inline">
  Connection status text
</span>
```

**Classes:**
- `md:hidden` - Hide on tablet and up
- `hidden md:block` - Hide on mobile, show on tablet+
- `hidden lg:block` - Hide until desktop
- `hidden sm:inline` - Hide on mobile, inline on tablet+

---

### 9. Collapsible Section Pattern

**Use Case:** Expandable content sections

```typescript
const [isExpanded, setIsExpanded] = useState(false);

<div className="bg-slate-900 border rounded-lg">
  {/* Header - Always Visible */}
  <button
    onClick={() => setIsExpanded(!isExpanded)}
    className="w-full flex items-center justify-between p-4 touch-manipulation"
    style={{ minHeight: '44px' }}
  >
    <span className="font-semibold">Section Title</span>
    <svg className={`w-5 h-5 transition-transform ${isExpanded ? 'rotate-180' : ''}`}>
      {/* Chevron icon */}
    </svg>
  </button>

  {/* Content - Collapsible */}
  {isExpanded && (
    <div className="p-4 border-t border-slate-800">
      {/* Expanded content */}
    </div>
  )}
</div>
```

**Features:**
- Touch-friendly toggle button
- Smooth rotation animation
- Clear visual indicator (chevron)
- Accessible keyboard navigation

---

### 10. Modal Dialog Pattern (Mobile-Optimized)

**Use Case:** Confirmation dialogs, detail views

```typescript
{isOpen && (
  <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
    <div className="bg-slate-900 border border-slate-700 rounded-lg p-6 max-w-md w-full">
      <h3 className="text-lg font-semibold mb-4">
        Dialog Title
      </h3>
      <p className="text-slate-300 mb-6">
        Dialog content
      </p>
      <div className="flex gap-3 justify-end">
        <button
          onClick={onCancel}
          className="px-4 py-2 border rounded touch-manipulation"
          style={{ minHeight: '44px' }}
        >
          Cancel
        </button>
        <button
          onClick={onConfirm}
          className="px-4 py-2 bg-cta rounded touch-manipulation"
          style={{ minHeight: '44px' }}
        >
          Confirm
        </button>
      </div>
    </div>
  </div>
)}
```

**Features:**
- Full-screen overlay
- Centered dialog
- Mobile padding (p-4)
- Touch-friendly buttons
- Max-width constraint

---

## Tailwind Breakpoint Reference

| Breakpoint | Min Width | Usage |
|------------|-----------|-------|
| (default) | 0px | Mobile-first base styles |
| `sm:` | 640px | Small tablets |
| `md:` | 768px | Tablets (our mobile breakpoint) |
| `lg:` | 1024px | Desktops |
| `xl:` | 1280px | Large desktops |
| `2xl:` | 1536px | Extra large screens |

**OpenClaw Dashboard Breakpoints:**
- **Mobile:** < 768px (default + sm:)
- **Tablet:** ≥ 768px (md:)
- **Desktop:** ≥ 1024px (lg:)

---

## Touch Optimization Checklist

- [ ] Minimum 44x44px tap targets
- [ ] `touch-manipulation` CSS class
- [ ] Adequate spacing between interactive elements
- [ ] No hover-only interactions
- [ ] Clear visual feedback on tap
- [ ] Swipe gestures for navigation (optional)
- [ ] Prevent accidental taps (spacing, confirmation)

---

## Performance Best Practices

1. **Conditional Rendering:**
   - Use `hidden md:block` instead of rendering both layouts
   - Prevents unnecessary DOM elements

2. **CSS Transitions:**
   - Use `transform` for animations (hardware-accelerated)
   - Keep duration 200-300ms for smooth feel

3. **Touch Events:**
   - Use `touch-manipulation` to disable double-tap zoom
   - Improves perceived responsiveness

4. **Lazy Loading:**
   - Virtual scrolling for long lists
   - Lazy load images and charts
   - Code splitting for routes

---

## Accessibility (A11y) Checklist

- [ ] ARIA labels on all interactive elements
- [ ] Keyboard navigation support (Tab, Enter, Escape)
- [ ] Focus indicators visible
- [ ] Color contrast ≥4.5:1 (WCAG AA)
- [ ] Touch targets ≥44x44px (WCAG 2.1 AA)
- [ ] Screen reader announcements for dynamic content
- [ ] Semantic HTML structure
- [ ] No reliance on color alone

---

## Testing Checklist

### Screen Sizes:
- [ ] iPhone SE (375x667) - Minimum
- [ ] iPhone 12/13 (390x844)
- [ ] iPhone 14 Pro Max (430x932)
- [ ] iPad Mini (768x1024) - Breakpoint
- [ ] Desktop (1920x1080)

### Functionality:
- [ ] Navigation works on all screens
- [ ] All interactive elements accessible
- [ ] No horizontal scroll
- [ ] Touch targets adequate size
- [ ] Smooth transitions
- [ ] Content readable at all sizes

### Browsers:
- [ ] Chrome Mobile
- [ ] Safari iOS
- [ ] Firefox Mobile
- [ ] Chrome Desktop
- [ ] Safari Desktop

---

## Common Pitfalls to Avoid

1. **Fixed Widths:** Use `max-w-*` instead of `w-[px]`
2. **Hover-Only:** Provide touch alternatives
3. **Small Tap Targets:** Always ≥44x44px
4. **Horizontal Scroll:** Test on 375px width
5. **Tiny Text:** Minimum 14px (text-sm)
6. **Dense Layouts:** Add adequate spacing on mobile
7. **Hidden Content:** Ensure critical info visible
8. **Slow Animations:** Keep under 300ms
9. **Missing Breakpoints:** Test all screen sizes
10. **Accessibility:** Don't forget ARIA labels

---

## Quick Reference: Common Classes

```typescript
// Responsive Grid
"grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"

// Responsive Spacing
"px-4 sm:px-6 lg:px-8 py-3 sm:py-4 lg:py-6"

// Responsive Text
"text-sm sm:text-base lg:text-lg"

// Hide on Mobile
"hidden md:block"

// Show on Mobile Only
"md:hidden"

// Touch-Friendly Button
"p-2 rounded-lg hover:bg-white/5 transition-colors touch-manipulation"

// Mobile Card
"bg-slate-900 border border-slate-800 rounded-lg p-4 touch-manipulation"

// Slide Animation
"transform transition-transform duration-300 ease-in-out"

// Overlay Backdrop
"fixed inset-0 bg-black/60 z-40"
```

---

## Resources

- [Tailwind CSS Responsive Design](https://tailwindcss.com/docs/responsive-design)
- [WCAG 2.1 Touch Target Size](https://www.w3.org/WAI/WCAG21/Understanding/target-size.html)
- [MDN Touch Events](https://developer.mozilla.org/en-US/docs/Web/API/Touch_events)
- [React Responsive Best Practices](https://react.dev/learn/responding-to-events)
