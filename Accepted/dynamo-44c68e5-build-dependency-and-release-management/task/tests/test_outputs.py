"""Pytest test suite for validating pipeline output against expected results."""

import json
import os
import pytest


EXPECTED_OUTPUT_PATH = '/tests/expected_output.json'
ACTUAL_OUTPUT_PATH = '/app/output.json'


@pytest.fixture
def expected_output():
    """Load the expected output from the oracle file."""
    with open(EXPECTED_OUTPUT_PATH, 'r') as f:
        return json.load(f)


@pytest.fixture
def actual_output():
    """Load the actual pipeline output."""
    with open(ACTUAL_OUTPUT_PATH, 'r') as f:
        return json.load(f)


def test_store_paths_match(actual_output, expected_output):
    """Verify all computed store paths match expected values."""
    assert actual_output['store_paths'] == expected_output['store_paths']


def test_build_plan_to_build(actual_output, expected_output):
    """Verify the list of derivations requiring builds is correct."""
    actual_builds = sorted(actual_output['build_plan']['to_build'], key=lambda x: x['name'])
    expected_builds = sorted(expected_output['build_plan']['to_build'], key=lambda x: x['name'])
    assert actual_builds == expected_builds


def test_build_plan_to_substitute(actual_output, expected_output):
    """Verify the list of derivations available for substitution is correct."""
    actual_subs = sorted(actual_output['build_plan']['to_substitute'], key=lambda x: x['name'])
    expected_subs = sorted(expected_output['build_plan']['to_substitute'], key=lambda x: x['name'])
    assert actual_subs == expected_subs


def test_build_plan_counts(actual_output, expected_output):
    """Verify total build and substitute counts match expected values."""
    assert actual_output['build_plan']['total_builds'] == expected_output['build_plan']['total_builds']
    assert actual_output['build_plan']['total_substitutes'] == expected_output['build_plan']['total_substitutes']


def test_system_info(actual_output, expected_output):
    """Verify system information is correctly propagated to output."""
    assert actual_output['system'] == expected_output['system']


def test_fixed_output_paths(actual_output, expected_output):
    """Verify fixed-output derivations get content-addressed store paths."""
    for name in ['fetchurl-openssl', 'fetchgit-zlib']:
        if name in expected_output['store_paths']:
            assert actual_output['store_paths'][name] == expected_output['store_paths'][name], \
                f'Fixed-output derivation {name} has wrong store path'


def test_self_referencing_path(actual_output, expected_output):
    """Verify self-referencing derivation uses placeholder-based path computation."""
    if 'myapp' in expected_output['store_paths']:
        assert actual_output['store_paths']['myapp'] == expected_output['store_paths']['myapp'], \
            'Self-referencing derivation myapp has wrong store path'


def test_cache_validation(actual_output, expected_output):
    """Verify cache hits are correctly identified using NAR hash validation."""
    actual_sub_names = {s['name'] for s in actual_output['build_plan']['to_substitute']}
    expected_sub_names = {s['name'] for s in expected_output['build_plan']['to_substitute']}
    assert actual_sub_names == expected_sub_names, \
        f'Cache hit mismatch: got {actual_sub_names}, expected {expected_sub_names}'


def test_output_completeness(actual_output, expected_output):
    """Verify output contains all required top-level keys."""
    assert set(actual_output.keys()) == set(expected_output.keys())


def test_all_derivations_present(actual_output, expected_output):
    """Verify all derivation names appear in store paths output."""
    assert set(actual_output['store_paths'].keys()) == set(expected_output['store_paths'].keys())
