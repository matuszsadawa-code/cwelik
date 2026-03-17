# Performance Optimization Quick Reference Guide

## Quick Checklist for Optimizing Components

### ✅ Before You Start
- [ ] Identify if component has performance issues (use React DevTools Profiler)
- [ ] Understand what state the component needs
- [ ] Identify expensive calculations
- [ ] List all event handlers passed as props

### ✅ Optimization Steps

#### 1. Selective Zustand Subscriptions (5 min)
```typescript
// ❌ Bad - subscribes to entire store
const data = useDashboardStore((state) => state.data);

// ✅ Good - selective subscription
import { shallowEqual } from '../utils/performanceOptimization';
const data = useDashboardStore((state) => state.data, shallowEqual);
```

#### 2. Wrap Component with React.memo (2 min)
```typescript
// ❌ Bad
export const MyComponent: React.FC<Props> = ({ data }) => {
  // ...
};

// ✅ Good
const MyComponentImpl: React.FC<Props> = ({ data }) => {
  // ...
};

export const MyComponent = memo(MyComponentImpl);
```

#### 3. Memoize Expensive Calculations (10 min)
```typescript
// ❌ Bad - recalculates every render
const sortedData = data.sort((a, b) => a.value - b.value);

// ✅ Good - only recalculates when dependencies change
const sortedData = useMemo(() => {
  return data.sort((a, b) => a.value - b.value);
}, [data]);
```

#### 4. Memoize Event Handlers (5 min)
```typescript
// ❌ Bad - new function every render
const handleClick = (id: string) => {
  doSomething(id);
};

// ✅ Good - stable function reference
const handleClick = useCallback((id: string) => {
  doSomething(id);
}, []);
```

#### 5. Memoize List Item Components (15 min)
```typescript
// ❌ Bad - all items re-render
{items.map(item => (
  <div key={item.id} onClick={() => handleClick(item.id)}>
    {item.name}
  </div>
))}

// ✅ Good - only changed items re-render
const ListItem = memo<ItemProps>(({ item, onClick }) => (
  <div onClick={() => onClick(item.id)}>
    {item.name}
  </div>
));

{items.map(item => (
  <ListItem key={item.id} item={item} onClick={handleClick} />
))}
```

## Common Patterns

### Pattern: Filter + Sort + Map
```typescript
const processedData = useMemo(() => {
  return data
    .filter(item => item.active)
    .sort((a, b) => a.value - b.value)
    .map(item => ({ ...item, formatted: format(item.value) }));
}, [data]);
```

### Pattern: Aggregate Calculations
```typescript
const metrics = useMemo(() => {
  const total = items.reduce((sum, item) => sum + item.value, 0);
  const average = total / items.length;
  const max = Math.max(...items.map(i => i.value));
  
  return { total, average, max };
}, [items]);
```

### Pattern: Event Handler with State Update
```typescript
// Use functional update to avoid dependencies
const handleToggle = useCallback(() => {
  setIsOpen(prev => !prev);
}, []); // No dependencies!
```

### Pattern: Event Handler with Props
```typescript
// Include prop in dependencies
const handleClick = useCallback((id: string) => {
  onItemClick(id);
}, [onItemClick]);
```

## Quick Wins (Biggest Impact)

### 1. Selective Subscriptions (40-50% improvement)
Replace all `useDashboardStore((state) => state.x)` with selective subscriptions.

### 2. Memoize List Components (50-60% improvement)
Extract list items into memoized components.

### 3. Memoize Sorting/Filtering (20-30% improvement)
Wrap expensive array operations in useMemo.

## Debugging Re-renders

### Use React DevTools Profiler
1. Open React DevTools
2. Go to Profiler tab
3. Click record button
4. Interact with app
5. Stop recording
6. Analyze flame graph

### Use useWhyDidYouUpdate Hook
```typescript
import { useWhyDidYouUpdate } from '../utils/performanceOptimization';

const MyComponent: React.FC<Props> = (props) => {
  useWhyDidYouUpdate('MyComponent', props);
  // ...
};
```

### Use useRenderProfile Hook
```typescript
import { useRenderProfile } from '../utils/performanceOptimization';

const MyComponent: React.FC<Props> = (props) => {
  useRenderProfile('MyComponent', 16); // Warns if > 16ms
  // ...
};
```

## Common Mistakes

### ❌ Mistake 1: Missing Dependencies
```typescript
// Bad - missing dependency
const handleClick = useCallback(() => {
  doSomething(value); // value not in dependencies!
}, []);

// Good
const handleClick = useCallback(() => {
  doSomething(value);
}, [value]);
```

### ❌ Mistake 2: Inline Object/Array Props
```typescript
// Bad - new object every render
<MyComponent config={{ option: true }} />

// Good - memoize object
const config = useMemo(() => ({ option: true }), []);
<MyComponent config={config} />
```

### ❌ Mistake 3: Inline Functions
```typescript
// Bad - new function every render
<MyComponent onClick={() => handleClick(id)} />

// Good - use useCallback
const handleItemClick = useCallback(() => handleClick(id), [id]);
<MyComponent onClick={handleItemClick} />
```

### ❌ Mistake 4: Over-memoization
```typescript
// Bad - unnecessary memoization
const simpleValue = useMemo(() => props.value * 2, [props.value]);

// Good - simple calculation, no memoization needed
const simpleValue = props.value * 2;
```

## When NOT to Optimize

- Simple components that render quickly (<5ms)
- Components that rarely re-render
- Calculations that are very cheap (< 1ms)
- Components without children

## Performance Targets

| Component Type | Target Render Time | Target Re-renders/sec |
|----------------|-------------------|----------------------|
| Simple | < 5ms | Any |
| Medium | < 10ms | < 10 |
| Complex | < 20ms | < 5 |
| Charts | < 50ms | < 2 |

## Tools & Resources

### React DevTools
- Install: Chrome/Firefox extension
- Use: Profiler tab for render analysis
- Look for: Unnecessary re-renders, slow components

### Performance Monitor
```typescript
import { performanceMonitor } from '../utils/performanceOptimization';

// View report
performanceMonitor.logReport();

// Reset metrics
performanceMonitor.reset();
```

### ESLint Rules
Enable `react-hooks/exhaustive-deps` to catch missing dependencies.

## Quick Reference Card

```typescript
// Selective subscription
const data = useDashboardStore(s => s.data, shallowEqual);

// Memoize component
export const MyComponent = memo(MyComponentImpl);

// Memoize calculation
const result = useMemo(() => calculate(data), [data]);

// Memoize handler
const handleClick = useCallback((id) => onClick(id), [onClick]);

// Memoize list item
const Item = memo<ItemProps>(({ item, onClick }) => <div>...</div>);
```

## Need Help?

1. Check `TASK_6.10_PERFORMANCE_OPTIMIZATION.md` for detailed guide
2. Review optimized components in `src/components/*.optimized.tsx`
3. Use performance utilities in `src/utils/performanceOptimization.ts`
4. Profile with React DevTools Profiler
5. Ask team for code review

## Remember

- **Measure first**: Use React DevTools to identify actual problems
- **Optimize strategically**: Focus on components that re-render frequently
- **Test thoroughly**: Ensure optimizations don't break functionality
- **Document patterns**: Help future developers understand optimizations
