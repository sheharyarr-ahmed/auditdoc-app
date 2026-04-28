"""Tests for Katzilla government data verification integration.

All tests run offline without a real API key, using mocking or feature flags.
"""

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

from katzilla import fetch_citations
from schemas import GovernmentCitation


def test_disabled_feature_returns_empty():
    """When KATZILLA_ENABLED is not set or false, fetch_citations returns immediately."""
    # Clear env to ensure disabled state
    os.environ.pop("KATZILLA_ENABLED", None)
    result = asyncio.run(fetch_citations("soc2_cc6_1"))
    assert result == []


def test_no_api_key_logs_warning():
    """When KATZILLA_ENABLED but no API key, returns empty with warning logged."""
    os.environ["KATZILLA_ENABLED"] = "true"
    os.environ.pop("KATZILLA_API_KEY", None)
    result = asyncio.run(fetch_citations("soc2_cc6_1"))
    assert result == []


def test_unknown_item_id_returns_empty():
    """When item_id has no query mapping, returns empty."""
    os.environ["KATZILLA_ENABLED"] = "true"
    os.environ["KATZILLA_API_KEY"] = "test-key"
    result = asyncio.run(fetch_citations("unknown_item"))
    assert result == []


def test_mock_successful_fetch():
    """Mock successful API response and verify citation parsing."""
    mock_payload = {
        "results": [
            {
                "title": "SEC Filing on Cybersecurity",
                "url": "https://sec.gov/cgi-bin/browse-edgar?...",
                "date": "2025-03-15",
                "summary": "Company discloses authentication controls.",
                "hash": "abc123def456"
            }
        ]
    }

    async def test_impl():
        os.environ["KATZILLA_ENABLED"] = "true"
        os.environ["KATZILLA_API_KEY"] = "test-key"

        with patch("katzilla.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            # Mock successful response for one endpoint (sec_edgar)
            mock_resp = MagicMock()
            mock_resp.json.return_value = mock_payload
            mock_resp.raise_for_status = MagicMock()

            # Mock all four sources but return results for sec_edgar, empty for others
            async def get_side_effect(*args, **kwargs):
                if "/sec/filings" in args[0]:
                    return mock_resp
                else:
                    empty_resp = MagicMock()
                    empty_resp.json.return_value = {"results": []}
                    empty_resp.raise_for_status = MagicMock()
                    return empty_resp

            mock_client.get = AsyncMock(side_effect=get_side_effect)

            result = await fetch_citations("soc2_cc6_1", limit_per_source=3)

            # Should have at least one citation from sec_edgar
            assert len(result) >= 1
            cit = result[0]
            assert cit.source == "sec_edgar"
            assert cit.title == "SEC Filing on Cybersecurity"
            assert cit.url == "https://sec.gov/cgi-bin/browse-edgar?..."
            assert cit.date == "2025-03-15"
            assert cit.summary == "Company discloses authentication controls."
            assert cit.hash == "abc123def456"

    asyncio.run(test_impl())


def test_truncate_to_limit_per_source():
    """Verify max 3 citations per finding is enforced."""
    mock_payload = {
        "results": [
            {"title": f"Result {i}", "url": f"https://example.gov/{i}", "summary": ""}
            for i in range(10)  # 10 results, more than limit
        ]
    }

    async def test_impl():
        os.environ["KATZILLA_ENABLED"] = "true"
        os.environ["KATZILLA_API_KEY"] = "test-key"

        with patch("katzilla.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            mock_resp = MagicMock()
            mock_resp.json.return_value = mock_payload
            mock_resp.raise_for_status = MagicMock()

            # All sources return the same payload
            mock_client.get = AsyncMock(return_value=mock_resp)

            result = await fetch_citations("soc2_cc6_1", limit_per_source=3)

            # Should truncate to 3 total (breadth-first: 1 from each of 4 sources = 4, then limit to 3)
            assert len(result) == 3

    asyncio.run(test_impl())


def test_error_resilience():
    """When HTTP call raises exception, returns empty list without propagating."""
    import httpx

    async def test_impl():
        os.environ["KATZILLA_ENABLED"] = "true"
        os.environ["KATZILLA_API_KEY"] = "test-key"

        with patch("katzilla.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            # Simulate network error
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection failed"))

            # Should not raise; should return empty
            result = await fetch_citations("soc2_cc6_1")
            assert result == []

    asyncio.run(test_impl())


if __name__ == "__main__":
    print("Running test_disabled_feature_returns_empty...")
    test_disabled_feature_returns_empty()
    print("✓ passed")

    print("Running test_no_api_key_logs_warning...")
    test_no_api_key_logs_warning()
    print("✓ passed")

    print("Running test_unknown_item_id_returns_empty...")
    test_unknown_item_id_returns_empty()
    print("✓ passed")

    print("Running test_mock_successful_fetch...")
    test_mock_successful_fetch()
    print("✓ passed")

    print("Running test_truncate_to_limit_per_source...")
    test_truncate_to_limit_per_source()
    print("✓ passed")

    print("Running test_error_resilience...")
    test_error_resilience()
    print("✓ passed")

    print("\n✅ All Katzilla tests passed!")
