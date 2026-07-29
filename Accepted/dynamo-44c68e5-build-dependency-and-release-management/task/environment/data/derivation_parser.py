"""Parser for Nix-style build configuration files."""

import json
import os


def load_build_config(config_path: str) -> dict:
    """Load and validate a build configuration JSON file."""
    with open(config_path, 'r') as f:
        config = json.load(f)
    validate_config(config)
    return config


def validate_config(config: dict) -> None:
    """Validate required fields exist in build configuration."""
    required_top = ['derivations', 'cache_config', 'system']
    for field in required_top:
        if field not in config:
            raise ValueError(f'Missing required top-level field: {field}')
    for drv in config['derivations']:
        validate_derivation(drv)


def validate_derivation(drv: dict) -> None:
    """Validate required fields in a single derivation entry."""
    required_fields = ['name', 'builder', 'inputs', 'build_args',
                       'is_fixed_output', 'outputs', 'has_self_reference']
    for field in required_fields:
        if field not in drv:
            raise ValueError(f'Derivation {drv.get("name", "?")} missing field: {field}')
    if drv['is_fixed_output']:
        if 'hash_algo' not in drv or 'output_hash' not in drv:
            raise ValueError(f'Fixed-output derivation {drv["name"]} needs hash_algo and output_hash')


def parse_derivations(config: dict) -> list:
    """Extract and return ordered list of derivation definitions."""
    return config['derivations']


def parse_cache_config(config: dict) -> dict:
    """Extract binary cache configuration section."""
    return config['cache_config']


def get_system_info(config: dict) -> dict:
    """Extract system platform and architecture info."""
    return config['system']


def get_derivation_by_name(derivations: list, name: str) -> dict:
    """Look up a derivation by its name field."""
    for drv in derivations:
        if drv['name'] == name:
            return drv
    raise KeyError(f'Derivation not found: {name}')


def get_output_names(drv: dict) -> list:
    """Return the list of output names for a derivation."""
    return drv.get('outputs', ['out'])


def build_derivation_map(derivations: list) -> dict:
    """Create a name-to-derivation lookup dictionary."""
    return {drv['name']: drv for drv in derivations}
