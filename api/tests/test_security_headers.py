"""
Unit tests for Security Headers Middleware

Tests that all security headers are correctly added to HTTP responses
and that configuration options work as expected.
"""

import pytest
import os
from fastapi import FastAPI
from fastapi.testclient import TestClient
from api.middleware.security_headers import SecurityHeadersMiddleware


@pytest.fixture
def app():
    """Create a test FastAPI application"""
    app = FastAPI()
    
    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}
    
    return app


@pytest.fixture
def client_with_security_headers(app):
    """Create test client with security headers middleware"""
    app.add_middleware(SecurityHeadersMiddleware)
    return TestClient(app)


@pytest.fixture
def client_with_https_enforced(app):
    """Create test client with HTTPS enforcement enabled"""
    app.add_middleware(SecurityHeadersMiddleware, enforce_https=True)
    return TestClient(app)


@pytest.fixture
def client_without_csp(app):
    """Create test client with CSP disabled"""
    app.add_middleware(SecurityHeadersMiddleware, csp_enabled=False)
    return TestClient(app)


@pytest.fixture
def client_with_csp_report_only(app):
    """Create test client with CSP in report-only mode"""
    app.add_middleware(SecurityHeadersMiddleware, csp_report_only=True)
    return TestClient(app)


class TestBasicSecurityHeaders:
    """Test basic security headers that should always be present"""
    
    def test_x_content_type_options_header(self, client_with_security_headers):
        """Test X-Content-Type-Options header is set to nosniff"""
        response = client_with_security_headers.get("/test")
        assert response.status_code == 200
        assert "x-content-type-options" in response.headers
        assert response.headers["x-content-type-options"] == "nosniff"
    
    def test_x_frame_options_header(self, client_with_security_headers):
        """Test X-Frame-Options header is set to DENY"""
        response = client_with_security_headers.get("/test")
        assert response.status_code == 200
        assert "x-frame-options" in response.headers
        assert response.headers["x-frame-options"] == "DENY"
    
    def test_x_xss_protection_header(self, client_with_security_headers):
        """Test X-XSS-Protection header is set correctly"""
        response = client_with_security_headers.get("/test")
        assert response.status_code == 200
        assert "x-xss-protection" in response.headers
        assert response.headers["x-xss-protection"] == "1; mode=block"
    
    def test_referrer_policy_header(self, client_with_security_headers):
        """Test Referrer-Policy header is set correctly"""
        response = client_with_security_headers.get("/test")
        assert response.status_code == 200
        assert "referrer-policy" in response.headers
        assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    
    def test_x_permitted_cross_domain_policies_header(self, client_with_security_headers):
        """Test X-Permitted-Cross-Domain-Policies header is set to none"""
        response = client_with_security_headers.get("/test")
        assert response.status_code == 200
        assert "x-permitted-cross-domain-policies" in response.headers
        assert response.headers["x-permitted-cross-domain-policies"] == "none"


class TestHTTPSEnforcement:
    """Test HTTPS enforcement (HSTS) behavior"""
    
    def test_hsts_not_present_by_default(self, client_with_security_headers):
        """Test HSTS header is not present in development mode"""
        response = client_with_security_headers.get("/test")
        assert response.status_code == 200
        assert "strict-transport-security" not in response.headers
    
    def test_hsts_present_when_enforced(self, client_with_https_enforced):
        """Test HSTS header is present when HTTPS is enforced"""
        response = client_with_https_enforced.get("/test")
        assert response.status_code == 200
        assert "strict-transport-security" in response.headers
        hsts = response.headers["strict-transport-security"]
        assert "max-age=31536000" in hsts
        assert "includeSubDomains" in hsts
        assert "preload" in hsts
    
    def test_hsts_auto_enabled_in_production(self, app, monkeypatch):
        """Test HSTS is automatically enabled when ENVIRONMENT=production"""
        monkeypatch.setenv("ENVIRONMENT", "production")
        app.add_middleware(SecurityHeadersMiddleware)
        client = TestClient(app)
        
        response = client.get("/test")
        assert response.status_code == 200
        assert "strict-transport-security" in response.headers
    
    def test_hsts_disabled_in_development(self, app, monkeypatch):
        """Test HSTS is disabled when ENVIRONMENT=development"""
        monkeypatch.setenv("ENVIRONMENT", "development")
        app.add_middleware(SecurityHeadersMiddleware)
        client = TestClient(app)
        
        response = client.get("/test")
        assert response.status_code == 200
        assert "strict-transport-security" not in response.headers


class TestContentSecurityPolicy:
    """Test Content Security Policy (CSP) behavior"""
    
    def test_csp_present_by_default(self, client_with_security_headers):
        """Test CSP header is present by default"""
        response = client_with_security_headers.get("/test")
        assert response.status_code == 200
        assert "content-security-policy" in response.headers
    
    def test_csp_not_present_when_disabled(self, client_without_csp):
        """Test CSP header is not present when disabled"""
        response = client_without_csp.get("/test")
        assert response.status_code == 200
        assert "content-security-policy" not in response.headers
        assert "content-security-policy-report-only" not in response.headers
    
    def test_csp_report_only_mode(self, client_with_csp_report_only):
        """Test CSP uses report-only header when configured"""
        response = client_with_csp_report_only.get("/test")
        assert response.status_code == 200
        assert "content-security-policy-report-only" in response.headers
        assert "content-security-policy" not in response.headers
    
    def test_csp_contains_default_src(self, client_with_security_headers):
        """Test CSP contains default-src directive"""
        response = client_with_security_headers.get("/test")
        csp = response.headers["content-security-policy"]
        assert "default-src 'self'" in csp
    
    def test_csp_contains_script_src(self, client_with_security_headers):
        """Test CSP contains script-src directive with necessary values"""
        response = client_with_security_headers.get("/test")
        csp = response.headers["content-security-policy"]
        assert "script-src" in csp
        assert "'self'" in csp
        assert "'unsafe-inline'" in csp
        assert "'unsafe-eval'" in csp
    
    def test_csp_contains_style_src(self, client_with_security_headers):
        """Test CSP contains style-src directive"""
        response = client_with_security_headers.get("/test")
        csp = response.headers["content-security-policy"]
        assert "style-src 'self' 'unsafe-inline'" in csp
    
    def test_csp_contains_img_src(self, client_with_security_headers):
        """Test CSP contains img-src directive"""
        response = client_with_security_headers.get("/test")
        csp = response.headers["content-security-policy"]
        assert "img-src 'self' data: https:" in csp
    
    def test_csp_contains_connect_src_with_websocket(self, client_with_security_headers):
        """Test CSP contains connect-src with WebSocket support"""
        response = client_with_security_headers.get("/test")
        csp = response.headers["content-security-policy"]
        assert "connect-src 'self' ws: wss:" in csp
    
    def test_csp_blocks_objects(self, client_with_security_headers):
        """Test CSP blocks object/embed/applet"""
        response = client_with_security_headers.get("/test")
        csp = response.headers["content-security-policy"]
        assert "object-src 'none'" in csp
    
    def test_csp_blocks_frame_ancestors(self, client_with_security_headers):
        """Test CSP blocks frame ancestors"""
        response = client_with_security_headers.get("/test")
        csp = response.headers["content-security-policy"]
        assert "frame-ancestors 'none'" in csp
    
    def test_csp_restricts_base_uri(self, client_with_security_headers):
        """Test CSP restricts base URI"""
        response = client_with_security_headers.get("/test")
        csp = response.headers["content-security-policy"]
        assert "base-uri 'self'" in csp
    
    def test_csp_restricts_form_action(self, client_with_security_headers):
        """Test CSP restricts form actions"""
        response = client_with_security_headers.get("/test")
        csp = response.headers["content-security-policy"]
        assert "form-action 'self'" in csp
    
    def test_csp_upgrade_insecure_requests_in_production(self, client_with_https_enforced):
        """Test CSP includes upgrade-insecure-requests in production"""
        response = client_with_https_enforced.get("/test")
        csp = response.headers["content-security-policy"]
        assert "upgrade-insecure-requests" in csp
    
    def test_csp_block_mixed_content_in_production(self, client_with_https_enforced):
        """Test CSP includes block-all-mixed-content in production"""
        response = client_with_https_enforced.get("/test")
        csp = response.headers["content-security-policy"]
        assert "block-all-mixed-content" in csp


class TestPermissionsPolicy:
    """Test Permissions Policy (Feature Policy) behavior"""
    
    def test_permissions_policy_present(self, client_with_security_headers):
        """Test Permissions-Policy header is present"""
        response = client_with_security_headers.get("/test")
        assert response.status_code == 200
        assert "permissions-policy" in response.headers
    
    def test_permissions_policy_disables_camera(self, client_with_security_headers):
        """Test Permissions-Policy disables camera"""
        response = client_with_security_headers.get("/test")
        policy = response.headers["permissions-policy"]
        assert "camera=()" in policy
    
    def test_permissions_policy_disables_microphone(self, client_with_security_headers):
        """Test Permissions-Policy disables microphone"""
        response = client_with_security_headers.get("/test")
        policy = response.headers["permissions-policy"]
        assert "microphone=()" in policy
    
    def test_permissions_policy_disables_geolocation(self, client_with_security_headers):
        """Test Permissions-Policy disables geolocation"""
        response = client_with_security_headers.get("/test")
        policy = response.headers["permissions-policy"]
        assert "geolocation=()" in policy
    
    def test_permissions_policy_disables_payment(self, client_with_security_headers):
        """Test Permissions-Policy disables payment API"""
        response = client_with_security_headers.get("/test")
        policy = response.headers["permissions-policy"]
        assert "payment=()" in policy
    
    def test_permissions_policy_disables_interest_cohort(self, client_with_security_headers):
        """Test Permissions-Policy disables FLoC (interest-cohort)"""
        response = client_with_security_headers.get("/test")
        policy = response.headers["permissions-policy"]
        assert "interest-cohort=()" in policy


class TestSecurityHeadersIntegration:
    """Test security headers work correctly with different endpoints"""
    
    def test_security_headers_on_root_endpoint(self, client_with_security_headers):
        """Test security headers are present on root endpoint"""
        response = client_with_security_headers.get("/test")
        assert response.status_code == 200
        assert "x-content-type-options" in response.headers
        assert "x-frame-options" in response.headers
        assert "content-security-policy" in response.headers
    
    def test_security_headers_on_json_response(self, client_with_security_headers):
        """Test security headers are present on JSON responses"""
        response = client_with_security_headers.get("/test")
        assert response.status_code == 200
        assert response.json() == {"message": "test"}
        assert "x-content-type-options" in response.headers
    
    def test_security_headers_on_404(self, client_with_security_headers):
        """Test security headers are present even on 404 responses"""
        response = client_with_security_headers.get("/nonexistent")
        assert response.status_code == 404
        assert "x-content-type-options" in response.headers
        assert "x-frame-options" in response.headers
    
    def test_security_headers_on_post_request(self, client_with_security_headers):
        """Test security headers are present on POST requests"""
        response = client_with_security_headers.post("/test", json={"data": "test"})
        # Will be 405 Method Not Allowed since we only defined GET
        assert "x-content-type-options" in response.headers
        assert "x-frame-options" in response.headers


class TestSecurityHeadersConfiguration:
    """Test security headers configuration options"""
    
    def test_factory_function_with_https_enabled(self, app):
        """Test factory function creates middleware with HTTPS enabled"""
        from api.middleware.security_headers import get_security_headers_middleware
        
        middleware_class = get_security_headers_middleware(enforce_https=True)
        app.add_middleware(middleware_class)
        client = TestClient(app)
        
        response = client.get("/test")
        assert "strict-transport-security" in response.headers
    
    def test_factory_function_with_csp_disabled(self, app):
        """Test factory function creates middleware with CSP disabled"""
        from api.middleware.security_headers import get_security_headers_middleware
        
        middleware_class = get_security_headers_middleware(csp_enabled=False)
        app.add_middleware(middleware_class)
        client = TestClient(app)
        
        response = client.get("/test")
        assert "content-security-policy" not in response.headers
    
    def test_factory_function_with_csp_report_only(self, app):
        """Test factory function creates middleware with CSP report-only"""
        from api.middleware.security_headers import get_security_headers_middleware
        
        middleware_class = get_security_headers_middleware(csp_report_only=True)
        app.add_middleware(middleware_class)
        client = TestClient(app)
        
        response = client.get("/test")
        assert "content-security-policy-report-only" in response.headers


class TestSecurityHeadersCompliance:
    """Test compliance with security best practices"""
    
    def test_all_required_headers_present(self, client_with_security_headers):
        """Test all required security headers are present"""
        response = client_with_security_headers.get("/test")
        
        required_headers = [
            "x-content-type-options",
            "x-frame-options",
            "x-xss-protection",
            "referrer-policy",
            "content-security-policy",
            "permissions-policy",
            "x-permitted-cross-domain-policies"
        ]
        
        for header in required_headers:
            assert header in response.headers, f"Missing required header: {header}"
    
    def test_no_information_leakage_headers(self, client_with_security_headers):
        """Test that information leakage headers are not present"""
        response = client_with_security_headers.get("/test")
        
        # These headers should not be present as they leak information
        leaky_headers = [
            "server",  # FastAPI adds this by default, but we shouldn't add more
            "x-powered-by",
            "x-aspnet-version",
            "x-aspnetmvc-version"
        ]
        
        for header in leaky_headers:
            if header in response.headers:
                # Only fail if we're adding these (FastAPI's server header is OK)
                if header != "server":
                    pytest.fail(f"Information leakage header present: {header}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
