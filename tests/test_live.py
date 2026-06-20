"""Live end-to-end test — hits real yfinance. Skipped unless --runlive passed."""

import pytest


@pytest.mark.live
class TestLiveEndToEnd:
    """Sanity check against real market data. Run manually before releases."""

    def test_real_pair_info(self):
        from afterquote import SecurityPair

        pair = SecurityPair("3USL.L", "SPY")
        info = pair.info()
        assert info["base_security"].iloc[0] == "3USL.L"
        assert info["underlying_security"].iloc[0] == "SPY"
        assert "base_is_live" in info.columns

    def test_real_pair_pricing_when_closed(self):
        from afterquote import SecurityPair

        pair = SecurityPair("3USL.L", "SPY")
        if pair.is_pair_fully_live():
            pytest.skip("base is live, synthetic not applicable right now")
        pricing = pair.pricing()
        if pricing.empty:
            pytest.skip("no underlying data since base's last close")
        assert list(pricing.columns) == [
            "Impl_Open",
            "Impl_High",
            "Impl_Low",
            "Impl_Close",
        ]
