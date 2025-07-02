"""Tests for the order_calculator.py module in pytest style."""

from __future__ import annotations

import pytest
from decimal import Decimal, InvalidOperation
from unittest.mock import patch

from trading.order_calculator import (
    determine_sell_orders_params,
    _round_decimal,
    calculate_buy_order_details,
)


# --- Tests for _round_decimal ---


@pytest.mark.parametrize(
    "value, increment, expected",
    [
        # Standard cases
        (Decimal("123.4567"), Decimal("0.01"), Decimal("123.45")),
        (Decimal("99.99999"), Decimal("0.01"), Decimal("99.99")),
        (Decimal("1.239"), Decimal("0.01"), Decimal("1.23")),
        (Decimal("1.23"), Decimal("0.1"), Decimal("1.2")),
        # Increment of 1
        (Decimal("123.456"), Decimal("1"), Decimal("123")),
        # Non-integer increment
        (Decimal("10.55"), Decimal("0.1"), Decimal("10.5")),
        # Integer increment > 1
        (Decimal("123.45"), Decimal("2"), Decimal("122")),
        # No change needed
        (Decimal("123.45"), Decimal("0.01"), Decimal("123.45")),
    ],
)
def test_round_decimal(value, increment, expected):
    """Test rounding a Decimal to a specified increment using various scenarios."""
    assert _round_decimal(value, increment) == expected


# --- Tests for determine_sell_orders_params ---


class TestDetermineSellOrdersParams:
    """Grouped tests for the determine_sell_orders_params function."""

    def test_happy_path(
        self, btc_product_details, btc_config_asset_params, mock_logger
    ):
        """Test standard tiered sell order creation."""
        result = determine_sell_orders_params(
            buy_price=Decimal("100.0"),
            buy_quantity=Decimal("10.0"),
            product_details=btc_product_details,
            config_asset_params=btc_config_asset_params,
            logger=mock_logger,
        )

        assert len(result) == 2
        # Tier 1: 50% of 10.0 at +2% price
        assert result[0]["size"] == "5.0000"
        assert result[0]["price"] == "102.00"
        # Tier 2: Remaining quantity at +4% price
        assert result[1]["size"] == "5.0000"
        assert result[1]["price"] == "104.00"

    def test_last_tier_sells_remaining_quantity(
        self,
        btc_product_details,
        mock_logger,
    ):
        """Test last tier sells all remaining quantity, with rounding (mutant #67)."""
        buy_quantity = Decimal("1.0001")

        # Use a local config to avoid modifying the session-scoped fixture
        config = {
            "profit_tiers": [
                {"profit_pct": "0.01", "sell_portion_initial": 0.5},
                {"profit_pct": "0.02", "sell_portion_initial": "all_remaining"},
            ]
        }

        result = determine_sell_orders_params(
            buy_price=Decimal("100.0"),
            buy_quantity=buy_quantity,
            product_details=btc_product_details,
            config_asset_params=config,
            logger=mock_logger,
        )

        assert len(result) == 2
        # Tier 1: 1.0001 * 0.5 = 0.50005, rounded down to 0.5000
        assert result[0]["size"] == "0.5000"
        # Tier 2 (last): Sells the rest (1.0001 - 0.5000 = 0.5001)
        assert result[1]["size"] == "0.5001"

        total_sold_quantity = sum(Decimal(p["size"]) for p in result)
        assert total_sold_quantity == buy_quantity

    def test_one_tier_below_min_size_is_skipped(
        self, btc_product_details, btc_config_asset_params, mock_logger
    ):
        """Test that a tier with a quantity below min_size is skipped."""
        btc_product_details["base_min_size"] = "0.6"
        params = determine_sell_orders_params(
            Decimal("100"),
            Decimal("1"),
            btc_product_details,
            btc_config_asset_params,
            mock_logger,
        )
        assert len(params) == 1
        mock_logger.info.assert_called_once()
        # Check the positional argument for the message
        assert (
            "Skipping tier 1 because its size is below min"
            in mock_logger.info.call_args[0][0]
        )

    def test_all_tiers_below_min_size_logs_extra_details(
        self, btc_product_details, btc_config_asset_params, mock_logger
    ):
        """Test that extra details are logged if all tiers are skipped."""
        btc_product_details["base_min_size"] = "1.1"
        params = determine_sell_orders_params(
            Decimal("100"),
            Decimal("1"),
            btc_product_details,
            btc_config_asset_params,
            mock_logger,
        )
        assert len(params) == 0
        assert mock_logger.info.call_count == 2  # For the two skipped tiers
        mock_logger.warning.assert_called_once_with(
            "[BTC-USD] No sell orders were created."
        )

    def test_missing_product_id_is_handled(
        self, btc_product_details, btc_config_asset_params, mock_logger
    ):
        """Test that a missing product_id is handled gracefully."""
        del btc_product_details["product_id"]
        # The function should proceed with the default "UNKNOWN_ASSET"
        determine_sell_orders_params(
            Decimal("100"),
            Decimal("1"),
            btc_product_details,
            btc_config_asset_params,
            mock_logger,
        )
        # No error or warning should be logged for this specific case
        mock_logger.warning.assert_not_called()
        mock_logger.error.assert_not_called()

    def test_zero_sell_quantity_is_skipped(
        self, btc_product_details, btc_config_asset_params, mock_logger
    ):
        """Test that a tier with a calculated quantity of zero is skipped."""
        # Set base_increment to 1.0 to force rounding to zero
        btc_product_details["base_increment"] = "1.0"
        params = determine_sell_orders_params(
            buy_price=Decimal("100"),
            buy_quantity=Decimal(
                "0.4"
            ),  # This will result in a size of 0.2, which rounds to 0
            product_details=btc_product_details,
            config_asset_params=btc_config_asset_params,
            logger=mock_logger,
        )
        # Both tiers will result in a quantity of 0, so no orders are created.
        assert len(params) == 0
        assert mock_logger.warning.call_count == 3  # Two for tiers, one for summary

    @pytest.mark.parametrize(
        "buy_price, buy_quantity, error_msg",
        [
            (Decimal("0"), Decimal("1"), "Buy price must be positive"),
            (Decimal("1"), Decimal("0"), "Buy quantity must be positive"),
        ],
    )
    def test_invalid_inputs_log_error(
        self,
        buy_price,
        buy_quantity,
        error_msg,
        btc_product_details,
        btc_config_asset_params,
        mock_logger,
    ):
        """Test that an error is logged for various invalid inputs."""
        result = determine_sell_orders_params(
            buy_price=buy_price,
            buy_quantity=buy_quantity,
            product_details=btc_product_details,
            config_asset_params=btc_config_asset_params,
            logger=mock_logger,
        )
        assert result == []
        mock_logger.error.assert_called_once()
        call_args, kwargs = mock_logger.error.call_args
        assert error_msg in call_args[0]
        assert kwargs.get("exc_info")

    def test_key_error_handling_in_product_details(
        self, btc_product_details, btc_config_asset_params, mock_logger
    ):
        """Test graceful failure on missing product_details key."""
        del btc_product_details["quote_increment"]

        result = determine_sell_orders_params(
            buy_price=Decimal("100"),
            buy_quantity=Decimal("1"),
            product_details=btc_product_details,
            config_asset_params=btc_config_asset_params,
            logger=mock_logger,
        )
        assert result == []
        mock_logger.error.assert_called_once()
        call_args, kwargs = mock_logger.error.call_args
        assert (
            "Missing key in config or product details: 'quote_increment'"
            in call_args[0]
        )
        assert kwargs.get("exc_info")

    def test_quantity_percentage_of_one_is_valid(
        self, btc_product_details, mock_logger
    ):
        """Test that a quantity_percentage of 1 is valid."""
        config = {
            "profit_tiers": [
                {
                    "profit_pct": Decimal("0.01"),
                    "sell_portion_initial": Decimal("1.0"),
                }
            ]
        }
        result = determine_sell_orders_params(
            buy_price=Decimal("100"),
            buy_quantity=Decimal("1"),
            product_details=btc_product_details,
            config_asset_params=config,
            logger=mock_logger,
        )
        assert len(result) == 1
        assert result[0]["size"] == "1.0000"
        mock_logger.error.assert_not_called()

    def test_last_tier_uses_remaining_quantity(self, btc_product_details, mock_logger):
        """Test last tier uses remaining quantity."""
        config = {
            "profit_tiers": [
                {
                    "profit_pct": Decimal("0.01"),
                    "sell_portion_initial": Decimal("0.3"),
                },
                {
                    "profit_pct": Decimal("0.02"),
                    "sell_portion_initial": Decimal("0.3"),
                },
                # The last tier uses the remaining quantity. Its `sell_portion_initial`
                # is for validation only; it's ignored for the size calculation.
                {
                    "profit_pct": Decimal("0.03"),
                    "sell_portion_initial": "all_remaining",
                },
            ]
        }

        result = determine_sell_orders_params(
            buy_price=Decimal("50000"),
            buy_quantity=Decimal("1.0"),
            product_details=btc_product_details,
            config_asset_params=config,
            logger=mock_logger,
        )

        assert len(result) == 3
        mock_logger.error.assert_not_called()
        tier1_qty = Decimal(result[0]["size"])
        tier2_qty = Decimal(result[1]["size"])
        tier3_qty = Decimal(result[2]["size"])
        assert tier1_qty == Decimal("0.3")
        assert tier2_qty == Decimal("0.3")
        assert tier3_qty == Decimal("0.4")
        assert tier1_qty + tier2_qty + tier3_qty == Decimal("1.0")

    def test_attribute_error_in_sell_calc_logs_exc_info(
        self, btc_product_details, btc_config_asset_params, mock_logger
    ):
        """Test AttributeError in sell calc logs exc_info."""
        with patch(
            "trading.order_calculator._calculate_tier_price_and_size",
            side_effect=AttributeError("mock attribute error"),
        ):
            result = determine_sell_orders_params(
                buy_price=Decimal("100.0"),
                buy_quantity=Decimal("1.0"),
                product_details=btc_product_details,
                config_asset_params=btc_config_asset_params,
                logger=mock_logger,
            )
            assert result == []
            mock_logger.error.assert_called_once()
            _args, kwargs = mock_logger.error.call_args
            assert "Attribute error in sell calc" in _args[0]
            assert kwargs.get("exc_info")

    def test_unexpected_exception_in_sell_calc_logs_exc_info(
        self, btc_product_details, btc_config_asset_params, mock_logger
    ):
        """Test generic Exception in sell calc logs exc_info."""
        with patch(
            "trading.order_calculator._calculate_tier_price_and_size",
            side_effect=Exception("mock unexpected error"),
        ):
            result = determine_sell_orders_params(
                buy_price=Decimal("100.0"),
                buy_quantity=Decimal("1.0"),
                product_details=btc_product_details,
                config_asset_params=btc_config_asset_params,
                logger=mock_logger,
            )
            assert result == []
            mock_logger.error.assert_called_once()
            _args, kwargs = mock_logger.error.call_args
            assert "Unexpected exception in sell calc" in _args[0]
            assert kwargs.get("exc_info")

    def test_decimal_invalid_operation_in_sell_calc_is_handled(
        self, btc_product_details, mock_logger
    ):
        """
        Test that a decimal.InvalidOperation in _calculate_tier_price_and_size
        is handled gracefully.
        """
        original_decimal = Decimal

        def mock_decimal_constructor(value, *args, **kwargs):
            # Trigger the error on the profit_pct of the first tier
            if str(value) == "0.02":
                raise InvalidOperation("Mocked invalid operation")
            return original_decimal(value, *args, **kwargs)

        # Use a local config where the tier will trigger the invalid op
        local_config = {
            "profit_tiers": [
                {"profit_pct": "0.02", "sell_portion_initial": 0.5},
                {"profit_pct": "0.04", "sell_portion_initial": "all_remaining"},
            ]
        }
        # Patch Decimal in the module where it is used
        with patch("trading.order_calculator.Decimal", new=mock_decimal_constructor):
            result = determine_sell_orders_params(
                buy_price=Decimal("100.0"),
                buy_quantity=Decimal("1.0"),
                product_details=btc_product_details,
                config_asset_params=local_config,
                logger=mock_logger,
            )
            assert result == []
            mock_logger.error.assert_called_once()
            call_args, kwargs = mock_logger.error.call_args
            assert "Invalid value for sell calc" in call_args[0]
            assert kwargs.get("exc_info")


def test_round_decimal_asserts_on_invalid_value_type():
    """Test _round_decimal asserts on a non-Decimal value."""
    with pytest.raises(AssertionError, match="Value to round must be a Decimal"):
        _round_decimal("not-a-decimal", Decimal("1"))


class TestCalculateBuyOrderDetails:
    """Test suite for the calculate_buy_order_details function."""

    def test_happy_path(self, btc_product_details, mock_logger):
        """Test the basic successful execution of calculate_buy_order_details."""
        result = calculate_buy_order_details(
            buy_amount_usd=Decimal("100"),
            last_close_price=Decimal("50000"),
            product_details=btc_product_details,
            logger=mock_logger,
        )
        assert result is not None
        size, price = result
        assert size == Decimal("0.0020")
        assert price == Decimal("50000.00")
        mock_logger.error.assert_not_called()
        mock_logger.warning.assert_not_called()

    def test_size_below_min_size_returns_none(self, btc_product_details, mock_logger):
        """Test that None is returned if calculated size is below min_size."""
        result = calculate_buy_order_details(
            buy_amount_usd=Decimal("0.01"),
            last_close_price=Decimal("50000"),
            product_details=btc_product_details,
            logger=mock_logger,
        )
        assert result is None
        mock_logger.warning.assert_called_once()
        assert "is below min size" in mock_logger.warning.call_args[0][0]

    def test_limit_price_rounds_to_zero(self, btc_product_details, mock_logger):
        """Test a limit_price that rounds to zero is handled."""
        result = calculate_buy_order_details(
            Decimal("10"),
            Decimal("0.00001"),
            btc_product_details,
            mock_logger,
        )
        assert result is None
        mock_logger.error.assert_called_once_with(
            "[BTC-USD] Calculated limit price is zero or negative."
        )

    def test_key_error_returns_none(self, btc_product_details, mock_logger):
        """Test that None is returned on a KeyError from missing product details."""
        del btc_product_details["base_increment"]
        result = calculate_buy_order_details(
            Decimal("100"), Decimal("50000"), btc_product_details, mock_logger
        )
        assert result is None
        mock_logger.error.assert_called_once()
        assert "Missing required key" in mock_logger.error.call_args[0][0]

    def test_invalid_numeric_value_in_product_details(
        self, btc_product_details, mock_logger
    ):
        """Test that a TypeError or InvalidOperation is handled gracefully."""
        btc_product_details["base_min_size"] = "not-a-valid-decimal"
        result = calculate_buy_order_details(
            Decimal("100"), Decimal("50000"), btc_product_details, mock_logger
        )
        assert result is None
        mock_logger.error.assert_called_once()
        call_args, kwargs = mock_logger.error.call_args
        assert "Invalid numeric value in product_details" in call_args[0]
        assert kwargs.get("exc_info") is True

    def test_generic_exception_returns_none(self, btc_product_details, mock_logger):
        """Test that None is returned on a generic exception."""
        with patch(
            "trading.order_calculator._round_decimal",
            side_effect=Exception("mock error"),
        ):
            result = calculate_buy_order_details(
                Decimal("100"), Decimal("50000"), btc_product_details, mock_logger
            )
            assert result is None
            mock_logger.error.assert_called_once()
            assert (
                "Exception calculating buy order details"
                in mock_logger.error.call_args[0][0]
            )

    def test_missing_product_id_logs_default_asset(
        self, btc_product_details, mock_logger
    ):
        """Test default asset ID is logged if product_id is missing."""
        del btc_product_details["product_id"]
        del btc_product_details["base_increment"]
        result = calculate_buy_order_details(
            Decimal("100"), Decimal("50000"), btc_product_details, mock_logger
        )
        assert result is None
        mock_logger.error.assert_called_once_with(
            "[UNKNOWN_ASSET] Missing required key in product_details: 'base_increment'"
        )

    def test_size_equal_to_min_size_is_valid(self, mock_logger):
        """Test that an order size equal to the minimum is valid."""
        product_details = {
            "product_id": "BTC-USD",
            "quote_increment": "0.01",
            "base_increment": "0.001",
            "base_min_size": "0.001",
        }
        result = calculate_buy_order_details(
            buy_amount_usd=Decimal("0.1"),
            last_close_price=Decimal("100"),
            product_details=product_details,
            logger=mock_logger,
        )
        assert result is not None
        size, price = result
        assert size == Decimal("0.001")
        assert price == Decimal("100.00")
        mock_logger.warning.assert_not_called()
