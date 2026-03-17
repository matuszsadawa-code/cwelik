---
name: async-parallel-processing
description: Async/await patterns and parallel processing for the OpenClaw system. Use when working with async operations, parallel symbol processing, concurrent API calls, or performance optimization through parallelism.
---

# Async Parallel Processing

Implementation guidelines for high-performance asynchronous operations in the trading system.

## Performance Optimization
OpenClaw uses `async/await` to achieve up to 16x faster data fetching and processing.

## Key Patterns

### Parallel Data Fetching
Use `asyncio.gather` to fetch data for multiple symbols concurrently.
```python
async def refresh_all(self, symbols: List[str]):
    tasks = [self._fetch_and_cache(symbol, tf) for symbol in symbols for tf in ["60", "240"]]
    results = await asyncio.gather(*tasks, return_exceptions=True)
```

### Async Context Managers
Always use async context managers for sessions to ensure proper resource cleanup.
```python
async with aiohttp.ClientSession() as session:
    async with session.get(url) as response:
        return await response.json()
```

### Rate Limiting
Use `asyncio.Semaphore` to prevent hitting API rate limits during parallel execution.
```python
self.semaphore = asyncio.Semaphore(10)
async with self.semaphore:
    return await self.fetch_data(symbol)
```

## Best Practices
- **Don't block the event loop** with heavy CPU-bound tasks or `time.sleep()`. Use `asyncio.sleep()`.
- **Handle exceptions** in parallel tasks individually to prevent one failure from stopping the entire batch.
- **Use timeouts** for all network requests to avoid hanging processes.
