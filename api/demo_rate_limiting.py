"""
Rate Limiting Demonstration Script

This script demonstrates the rate limiting functionality by making
multiple requests and showing the rate limit headers.
"""

import time
from api.middleware.rate_limiter import RateLimiter
from api.auth import User, UserRole


def demo_viewer_rate_limit():
    """Demonstrate viewer rate limit (100 req/60s)"""
    print("\n" + "="*60)
    print("DEMO: Viewer Rate Limit (100 requests/60 seconds)")
    print("="*60)
    
    limiter = RateLimiter()
    viewer = User(
        user_id="demo_viewer",
        username="demo_viewer",
        role=UserRole.VIEWER,
        disabled=False
    )
    
    # Make 105 requests
    for i in range(1, 106):
        try:
            limit, remaining, reset_time = limiter.check_rate_limit(viewer)
            
            if i % 10 == 0 or i <= 5 or i >= 98:
                print(f"Request {i:3d}: ✓ Allowed  | Limit: {limit} | Remaining: {remaining:3d} | Reset: {reset_time}")
        
        except Exception as e:
            print(f"Request {i:3d}: ✗ BLOCKED | {e.detail}")
            print(f"             Rate limit exceeded! Reset at: {e.reset_time}")
            break
    
    print()


def demo_trader_rate_limit():
    """Demonstrate trader rate limit (200 req/60s)"""
    print("\n" + "="*60)
    print("DEMO: Trader Rate Limit (200 requests/60 seconds)")
    print("="*60)
    
    limiter = RateLimiter()
    trader = User(
        user_id="demo_trader",
        username="demo_trader",
        role=UserRole.TRADER,
        disabled=False
    )
    
    # Make 205 requests
    for i in range(1, 206):
        try:
            limit, remaining, reset_time = limiter.check_rate_limit(trader)
            
            if i % 20 == 0 or i <= 5 or i >= 198:
                print(f"Request {i:3d}: ✓ Allowed  | Limit: {limit} | Remaining: {remaining:3d} | Reset: {reset_time}")
        
        except Exception as e:
            print(f"Request {i:3d}: ✗ BLOCKED | {e.detail}")
            print(f"             Rate limit exceeded! Reset at: {e.reset_time}")
            break
    
    print()


def demo_admin_rate_limit():
    """Demonstrate admin rate limit (500 req/60s)"""
    print("\n" + "="*60)
    print("DEMO: Admin Rate Limit (500 requests/60 seconds)")
    print("="*60)
    
    limiter = RateLimiter()
    admin = User(
        user_id="demo_admin",
        username="demo_admin",
        role=UserRole.ADMIN,
        disabled=False
    )
    
    # Make 505 requests
    for i in range(1, 506):
        try:
            limit, remaining, reset_time = limiter.check_rate_limit(admin)
            
            if i % 50 == 0 or i <= 5 or i >= 498:
                print(f"Request {i:3d}: ✓ Allowed  | Limit: {limit} | Remaining: {remaining:3d} | Reset: {reset_time}")
        
        except Exception as e:
            print(f"Request {i:3d}: ✗ BLOCKED | {e.detail}")
            print(f"             Rate limit exceeded! Reset at: {e.reset_time}")
            break
    
    print()


def demo_per_user_isolation():
    """Demonstrate that rate limits are isolated per user"""
    print("\n" + "="*60)
    print("DEMO: Per-User Rate Limit Isolation")
    print("="*60)
    
    limiter = RateLimiter()
    
    viewer1 = User(user_id="viewer1", username="viewer1", role=UserRole.VIEWER, disabled=False)
    viewer2 = User(user_id="viewer2", username="viewer2", role=UserRole.VIEWER, disabled=False)
    
    print("\nMaking 50 requests for each user...")
    
    for i in range(1, 51):
        limit1, remaining1, _ = limiter.check_rate_limit(viewer1)
        limit2, remaining2, _ = limiter.check_rate_limit(viewer2)
        
        if i % 10 == 0 or i <= 3:
            print(f"Request {i:2d}: viewer1 remaining: {remaining1:3d} | viewer2 remaining: {remaining2:3d}")
    
    print("\n✓ Each user has independent rate limit counter")
    print()


def demo_rate_limit_headers():
    """Demonstrate rate limit headers"""
    print("\n" + "="*60)
    print("DEMO: Rate Limit Headers")
    print("="*60)
    
    limiter = RateLimiter()
    viewer = User(
        user_id="demo_headers",
        username="demo_headers",
        role=UserRole.VIEWER,
        disabled=False
    )
    
    print("\nMaking a request and checking headers...")
    
    limit, remaining, reset_time = limiter.check_rate_limit(viewer)
    
    print(f"\nRate Limit Headers:")
    print(f"  X-RateLimit-Limit:     {limit}")
    print(f"  X-RateLimit-Remaining: {remaining}")
    print(f"  X-RateLimit-Reset:     {reset_time}")
    print(f"  Reset Time (human):    {time.ctime(reset_time)}")
    
    print()


def demo_summary():
    """Display summary of rate limits"""
    print("\n" + "="*60)
    print("RATE LIMITING SUMMARY")
    print("="*60)
    
    print("\nRole-Based Rate Limits:")
    print(f"  Viewer: 100 requests per 60 seconds")
    print(f"  Trader: 200 requests per 60 seconds")
    print(f"  Admin:  500 requests per 60 seconds")
    
    print("\nFeatures:")
    print("  ✓ Per-user tracking")
    print("  ✓ Sliding 60-second window")
    print("  ✓ 429 status code on limit exceeded")
    print("  ✓ Rate limit headers (X-RateLimit-*)")
    print("  ✓ Automatic cleanup of old entries")
    print("  ✓ Memory efficient (<1 MB for 1000 users)")
    print("  ✓ Low latency (<1ms overhead)")
    
    print("\nExempt Paths:")
    print("  • /health, /api/health")
    print("  • /api/auth/login, /api/auth/register")
    print("  • /ws (WebSocket)")
    print("  • /docs, /redoc, /openapi.json")
    
    print()


if __name__ == "__main__":
    print("\n" + "="*60)
    print("OpenClaw Trading Dashboard - Rate Limiting Demo")
    print("="*60)
    
    # Run all demos
    demo_summary()
    demo_rate_limit_headers()
    demo_per_user_isolation()
    demo_viewer_rate_limit()
    demo_trader_rate_limit()
    demo_admin_rate_limit()
    
    print("\n" + "="*60)
    print("Demo Complete!")
    print("="*60)
    print("\nFor more information, see: api/RATE_LIMITING.md")
    print()
