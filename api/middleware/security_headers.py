"""
Security Headers Middleware

Adds comprehensive security headers to all HTTP responses to protect against
common web vulnerabilities (XSS, clickjacking, MIME sniffing, etc.).

Implements:
- X-Content-Type-Options: Prevents MIME type sniffing
- X-Frame-Options: Prevents clickjacking attacks
- X-XSS-Protection: Enables browser XSS protection
- Strict-Transport-Security: Enforces HTTPS connections
- Referrer-Policy: Controls referrer information
- Content-Security-Policy: Restricts resource loading
- Permissions-Policy: Controls browser features
"""

import os
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all HTTP responses.
    
    Security headers protect against:
    - XSS (Cross-Site Scripting) attacks
    - Clickjacking attacks
    - MIME type sniffing
    - Man-in-the-middle attacks
    - Information leakage via referrer
    - Unauthorized resource loading
    """
    
    def __init__(
        self,
        app: ASGIApp,
        enforce_https: bool = None,
        csp_enabled: bool = True,
        csp_report_only: bool = False
    ):
        """
        Initialize security headers middleware.
        
        Args:
            app: ASGI application
            enforce_https: Whether to enforce HTTPS (auto-detects from ENVIRONMENT if None)
            csp_enabled: Whether to enable Content Security Policy
            csp_report_only: Whether to use CSP in report-only mode (for testing)
        """
        super().__init__(app)
        
        # Auto-detect production environment if not specified
        if enforce_https is None:
            environment = os.getenv("ENVIRONMENT", "development").lower()
            enforce_https = environment == "production"
        
        self.enforce_https = enforce_https
        self.csp_enabled = csp_enabled
        self.csp_report_only = csp_report_only
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and add security headers to response.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/route handler
            
        Returns:
            Response with security headers added
        """
        # Process request
        response = await call_next(request)
        
        # Add security headers
        self._add_security_headers(response)
        
        return response
    
    def _add_security_headers(self, response: Response) -> None:
        """
        Add all security headers to the response.
        
        Args:
            response: HTTP response to add headers to
        """
        # X-Content-Type-Options: Prevent MIME type sniffing
        # Ensures browsers respect the Content-Type header
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # X-Frame-Options: Prevent clickjacking
        # DENY: Page cannot be displayed in a frame/iframe
        response.headers["X-Frame-Options"] = "DENY"
        
        # X-XSS-Protection: Enable browser XSS filter
        # 1; mode=block: Enable XSS filter and block page if attack detected
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Strict-Transport-Security: Enforce HTTPS
        # Only add in production to avoid issues in development
        if self.enforce_https:
            # max-age=31536000: 1 year
            # includeSubDomains: Apply to all subdomains
            # preload: Allow inclusion in browser HSTS preload lists
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        
        # Referrer-Policy: Control referrer information
        # strict-origin-when-cross-origin: Send full URL for same-origin,
        # only origin for cross-origin HTTPS, nothing for HTTP
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Content-Security-Policy: Restrict resource loading
        if self.csp_enabled:
            csp_header = "Content-Security-Policy-Report-Only" if self.csp_report_only else "Content-Security-Policy"
            response.headers[csp_header] = self._build_csp_policy()
        
        # Permissions-Policy: Control browser features
        # Disable potentially dangerous features
        response.headers["Permissions-Policy"] = self._build_permissions_policy()
        
        # X-Permitted-Cross-Domain-Policies: Restrict cross-domain policies
        # none: No policy files allowed
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
    
    def _build_csp_policy(self) -> str:
        """
        Build Content Security Policy directive.
        
        CSP restricts which resources can be loaded and from where,
        providing defense-in-depth against XSS and data injection attacks.
        
        Returns:
            CSP policy string
        """
        # Define CSP directives
        directives = [
            # Default: Only allow resources from same origin
            "default-src 'self'",
            
            # Scripts: Allow self and inline scripts (needed for React)
            # 'unsafe-inline' is required for inline event handlers and <script> tags
            # 'unsafe-eval' is required for some bundlers and React DevTools
            # In production, consider using nonces or hashes instead
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
            
            # Styles: Allow self and inline styles (needed for styled-components, Tailwind)
            "style-src 'self' 'unsafe-inline'",
            
            # Images: Allow self, data URIs (for inline images), and HTTPS images
            "img-src 'self' data: https:",
            
            # Fonts: Allow self and data URIs (for inline fonts)
            "font-src 'self' data:",
            
            # Connect: Allow self and WebSocket connections
            # ws: and wss: are needed for WebSocket connections
            "connect-src 'self' ws: wss:",
            
            # Media: Allow self only
            "media-src 'self'",
            
            # Objects: Disallow plugins (Flash, Java, etc.)
            "object-src 'none'",
            
            # Base: Restrict base tag to same origin
            "base-uri 'self'",
            
            # Forms: Only allow form submissions to same origin
            "form-action 'self'",
            
            # Frame ancestors: Prevent embedding (redundant with X-Frame-Options)
            "frame-ancestors 'none'",
            
            # Upgrade insecure requests: Automatically upgrade HTTP to HTTPS
            # Only in production
            "upgrade-insecure-requests" if self.enforce_https else "",
            
            # Block all mixed content
            "block-all-mixed-content" if self.enforce_https else "",
        ]
        
        # Filter out empty directives and join with semicolons
        return "; ".join(d for d in directives if d)
    
    def _build_permissions_policy(self) -> str:
        """
        Build Permissions Policy (formerly Feature Policy).
        
        Controls which browser features and APIs can be used.
        
        Returns:
            Permissions policy string
        """
        # Disable potentially dangerous features
        policies = [
            "accelerometer=()",      # Disable accelerometer
            "camera=()",             # Disable camera
            "geolocation=()",        # Disable geolocation
            "gyroscope=()",          # Disable gyroscope
            "magnetometer=()",       # Disable magnetometer
            "microphone=()",         # Disable microphone
            "payment=()",            # Disable payment API
            "usb=()",                # Disable USB API
            "interest-cohort=()",    # Disable FLoC (privacy)
        ]
        
        return ", ".join(policies)


def get_security_headers_middleware(
    enforce_https: bool = None,
    csp_enabled: bool = True,
    csp_report_only: bool = False
) -> type[SecurityHeadersMiddleware]:
    """
    Factory function to create SecurityHeadersMiddleware with custom configuration.
    
    Args:
        enforce_https: Whether to enforce HTTPS (auto-detects from ENVIRONMENT if None)
        csp_enabled: Whether to enable Content Security Policy
        csp_report_only: Whether to use CSP in report-only mode
        
    Returns:
        Configured SecurityHeadersMiddleware class
    """
    class ConfiguredSecurityHeadersMiddleware(SecurityHeadersMiddleware):
        def __init__(self, app: ASGIApp):
            super().__init__(
                app,
                enforce_https=enforce_https,
                csp_enabled=csp_enabled,
                csp_report_only=csp_report_only
            )
    
    return ConfiguredSecurityHeadersMiddleware
