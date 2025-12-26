"""
Security Configuration Module
Centralized security settings and best practices for the SQLBot application
"""

from pydantic import BaseModel, Field
from typing import Optional


class SecurityConfig(BaseModel):
    """Security configuration settings"""
    
    # SSL/TLS Settings
    verify_ssl_certificates: bool = Field(
        default=True,
        description="Enable SSL certificate verification for external requests"
    )
    
    ssl_cert_path: Optional[str] = Field(
        default=None,
        description="Path to custom CA bundle for SSL verification"
    )
    
    # JWT Settings
    jwt_verify_signature: bool = Field(
        default=True,
        description="Enable JWT signature verification"
    )
    
    jwt_verify_expiration: bool = Field(
        default=True,
        description="Enable JWT expiration verification"
    )
    
    # Request Timeout Settings
    default_request_timeout: int = Field(
        default=30,
        description="Default timeout for HTTP requests in seconds"
    )
    
    database_connection_timeout: int = Field(
        default=10,
        description="Default timeout for database connections in seconds"
    )
    
    # Password Security
    min_password_length: int = Field(
        default=8,
        description="Minimum password length"
    )
    
    require_password_uppercase: bool = Field(
        default=True,
        description="Require at least one uppercase letter in passwords"
    )
    
    require_password_lowercase: bool = Field(
        default=True,
        description="Require at least one lowercase letter in passwords"
    )
    
    require_password_digit: bool = Field(
        default=True,
        description="Require at least one digit in passwords"
    )
    
    require_password_special: bool = Field(
        default=True,
        description="Require at least one special character in passwords"
    )
    
    # Rate Limiting
    enable_rate_limiting: bool = Field(
        default=True,
        description="Enable rate limiting for API endpoints"
    )
    
    rate_limit_per_minute: int = Field(
        default=60,
        description="Maximum requests per minute per user"
    )
    
    # SQL Injection Prevention
    use_parameterized_queries: bool = Field(
        default=True,
        description="Always use parameterized queries to prevent SQL injection"
    )
    
    # XSS Prevention
    sanitize_html_input: bool = Field(
        default=True,
        description="Sanitize HTML input to prevent XSS attacks"
    )
    
    # CSRF Protection
    enable_csrf_protection: bool = Field(
        default=True,
        description="Enable CSRF protection for state-changing requests"
    )
    
    # Logging and Monitoring
    log_security_events: bool = Field(
        default=True,
        description="Log security-related events"
    )
    
    log_failed_auth_attempts: bool = Field(
        default=True,
        description="Log failed authentication attempts"
    )
    
    max_failed_auth_attempts: int = Field(
        default=5,
        description="Maximum failed authentication attempts before account lockout"
    )
    
    account_lockout_duration_minutes: int = Field(
        default=15,
        description="Duration of account lockout in minutes"
    )


# Default security configuration
DEFAULT_SECURITY_CONFIG = SecurityConfig()


def get_security_config() -> SecurityConfig:
    """Get the current security configuration"""
    return DEFAULT_SECURITY_CONFIG


def validate_password_strength(password: str, config: SecurityConfig = DEFAULT_SECURITY_CONFIG) -> tuple[bool, str]:
    """
    Validate password strength based on security configuration
    
    Args:
        password: The password to validate
        config: Security configuration to use
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(password) < config.min_password_length:
        return False, f"Password must be at least {config.min_password_length} characters long"
    
    if config.require_password_uppercase and not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    
    if config.require_password_lowercase and not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    
    if config.require_password_digit and not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"
    
    if config.require_password_special:
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(c in special_chars for c in password):
            return False, "Password must contain at least one special character"
    
    return True, ""
