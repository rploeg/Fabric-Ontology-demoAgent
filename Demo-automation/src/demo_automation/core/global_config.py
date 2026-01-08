"""
Global configuration management for fabric-demo CLI.

Provides a unified configuration system with the following precedence:
1. CLI arguments (highest priority)
2. Environment variables
3. Global config file (~/.fabric-demo/config.yaml)
4. Demo-specific config (demo.yaml)
5. Built-in defaults (lowest priority)
"""

import os
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any

import yaml


logger = logging.getLogger(__name__)


# Default config file location
if os.name == 'nt':  # Windows
    CONFIG_DIR = Path(os.environ.get('USERPROFILE', '~')) / '.fabric-demo'
else:  # Unix/Mac
    CONFIG_DIR = Path(os.environ.get('HOME', '~')) / '.fabric-demo'

CONFIG_FILE = CONFIG_DIR / 'config.yaml'


@dataclass
class GlobalConfig:
    """Global configuration settings for fabric-demo CLI."""
    
    # Fabric settings
    workspace_id: Optional[str] = None
    tenant_id: Optional[str] = None
    
    # Authentication
    auth_method: str = "interactive"  # interactive, service_principal, default
    
    # Default options
    skip_existing: bool = True
    dry_run: bool = False
    verbose: bool = False
    
    # UI settings
    confirm_cleanup: bool = True  # Require confirmation for cleanup by default
    
    # Rate limiting (Fabric API throttling)
    rate_limit_enabled: bool = True
    rate_limit_requests_per_minute: int = 30  # Fabric API default
    rate_limit_burst: int = 10
    
    @classmethod
    def load(cls) -> "GlobalConfig":
        """Load global configuration from file and environment."""
        config = cls()
        
        # Load from config file if exists
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f) or {}
                config = cls._from_dict(data)
                logger.debug(f"Loaded config from {CONFIG_FILE}")
            except Exception as e:
                logger.warning(f"Failed to load config file: {e}")
        
        # Override with environment variables
        config._apply_env_overrides()
        
        return config
    
    @classmethod
    def _from_dict(cls, data: Dict[str, Any]) -> "GlobalConfig":
        """Create config from dictionary."""
        defaults = data.get('defaults', {})
        options = data.get('options', {})
        rate_limiting = data.get('rate_limiting', {})
        
        return cls(
            workspace_id=defaults.get('workspace_id'),
            tenant_id=defaults.get('tenant_id'),
            auth_method=defaults.get('auth_method', 'interactive'),
            skip_existing=options.get('skip_existing', True),
            dry_run=options.get('dry_run', False),
            verbose=options.get('verbose', False),
            confirm_cleanup=options.get('confirm_cleanup', True),
            rate_limit_enabled=rate_limiting.get('enabled', True),
            rate_limit_requests_per_minute=rate_limiting.get('requests_per_minute', 30),
            rate_limit_burst=rate_limiting.get('burst', 10),
        )
    
    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides."""
        if os.environ.get('FABRIC_WORKSPACE_ID'):
            self.workspace_id = os.environ['FABRIC_WORKSPACE_ID']
        if os.environ.get('AZURE_TENANT_ID'):
            self.tenant_id = os.environ['AZURE_TENANT_ID']
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for saving."""
        return {
            'defaults': {
                'workspace_id': self.workspace_id,
                'tenant_id': self.tenant_id,
                'auth_method': self.auth_method,
            },
            'options': {
                'skip_existing': self.skip_existing,
                'dry_run': self.dry_run,
                'verbose': self.verbose,
                'confirm_cleanup': self.confirm_cleanup,
            },
            'rate_limiting': {
                'enabled': self.rate_limit_enabled,
                'requests_per_minute': self.rate_limit_requests_per_minute,
                'burst': self.rate_limit_burst,
            },
        }
    
    def save(self) -> None:
        """Save configuration to file."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, sort_keys=False)
        logger.info(f"Saved config to {CONFIG_FILE}")
    
    def get_workspace_id(self, cli_override: Optional[str] = None) -> Optional[str]:
        """Get workspace ID with proper precedence."""
        # CLI argument takes highest priority
        if cli_override:
            return cli_override
        # Then environment variable (already applied)
        # Then config file value
        return self.workspace_id
    
    def get_tenant_id(self, cli_override: Optional[str] = None) -> Optional[str]:
        """Get tenant ID with proper precedence."""
        if cli_override:
            return cli_override
        return self.tenant_id


def get_config_file_path() -> Path:
    """Get the path to the global config file."""
    return CONFIG_FILE


def config_file_exists() -> bool:
    """Check if global config file exists."""
    return CONFIG_FILE.exists()


def generate_config_template() -> str:
    """Generate a template config file content."""
    return """# Fabric Demo Automation - Global Configuration
# =============================================
# This file provides default settings for all fabric-demo commands.
# Location: ~/.fabric-demo/config.yaml (or %USERPROFILE%\\.fabric-demo\\config.yaml on Windows)
#
# Configuration precedence (highest to lowest):
#   1. CLI arguments (e.g., --workspace-id)
#   2. Environment variables (e.g., FABRIC_WORKSPACE_ID)
#   3. This config file
#   4. Built-in defaults

defaults:
  # Your default Fabric workspace ID (GUID)
  # Can use environment variable: ${FABRIC_WORKSPACE_ID}
  workspace_id: 
  
  # Azure AD tenant ID (optional, for multi-tenant scenarios)
  tenant_id: 
  
  # Authentication method: interactive, service_principal, or default
  # - interactive: Opens browser for login (recommended for demos)
  # - service_principal: Uses AZURE_CLIENT_ID and AZURE_CLIENT_SECRET env vars
  # - default: Uses DefaultAzureCredential chain
  auth_method: interactive

options:
  # Skip creation if resources already exist (default: true)
  skip_existing: true
  
  # Preview mode - don't make changes (default: false)
  dry_run: false
  
  # Show verbose output (default: false)
  verbose: false
  
  # Require --confirm or interactive confirmation for cleanup (default: true)
  confirm_cleanup: true

# API rate limiting settings
# Adjust these if you have higher Fabric SKU quotas or experience throttling
rate_limiting:
  # Enable/disable rate limiting (default: true)
  enabled: true
  
  # Maximum requests per minute (default: 30)
  # Fabric API typically allows 30-60 requests/minute depending on SKU
  requests_per_minute: 30
  
  # Burst allowance for short request spikes (default: 10)
  burst: 10
"""
