"""Placeholder tests for KPO service filtering of stornirane fakture.

These tests are placeholders for Story 4.5 Task 5.
They will be implemented when KPO service is created (Story 4.7+).
"""
import pytest


@pytest.mark.skip(reason="KPO service not yet implemented (Story 4.7+)")
def test_stornirane_fakture_excluded_from_kpo():
    """
    Placeholder test: Stornirane fakture ne utiču na KPO promet.
    
    Story: 4.5 Task 5
    Implements AC: 5 - "Stornirane fakture NE uključuju se u KPO izveštaje"
    
    When implemented, this test should:
    1. Create two fakture (one izdata, one stornirana)
    2. Call KPO service to calculate promet
    3. Verify only izdata faktura is included in calculation
    4. Verify stornirana faktura is excluded
    
    Expected implementation in Story 4.7+:
    - Filter in KPO query: status != 'stornirana'
    - Located in: app/services/kpo_service.py
    """
    pass
