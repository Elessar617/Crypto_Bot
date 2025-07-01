from __future__ import annotations

import decimal
import logging
import unittest
from decimal import Decimal

from unittest.mock import MagicMock, Mock, patch

from trading.order_calculator import (
    determine_sell_orders_params,
    _round_decimal,
    _calculate_tier_price_and_size,
    calculate_buy_order_details,
)


class TestOrderCalculator(unittest.TestCase):
    @patch(
        "trading.order_calculator._calculate_tier_price_and_size",
        side_effect=Exception("Generic error for testing"),
    )
    def test_generic_exception_logs_exc_info(self, mock_calculate):
        """Test that a generic exception logs exc_info=True, killing mutant #99."""
        result = determine_sell_orders_params(
            Decimal("100.0"),
            Decimal("1.0"),
            self.product_details,
            self.config_asset_params,
            self.mock_logger,
        )

        self.assertEqual(result, [])
        self.mock_logger.error.assert_called_once()
        # Check that exc_info=True was passed to the logger.
        call_args = self.mock_logger.error.call_args
        self.assertIn("exc_info", call_args.kwargs)
        self.assertTrue(call_args.kwargs["exc_info"])

    def setUp(self):
        """Set up common test data."""
        self.mock_logger = MagicMock()
        self.product_details = {
            "product_id": "BTC-USD",
            "quote_increment": "0.01",
            "base_increment": "0.0001",
            "base_min_size": "0.001",
        }
        self.config_asset_params = {
            "sell_profit_tiers": [
                {"profit_target": 0.02, "quantity_percentage": 0.5},
                {"profit_target": 0.04, "quantity_percentage": 0.5},
            ]
        }

    # --- Tests for _round_decimal ---

    def test_round_decimal_down(self):
        """Test that rounding down works correctly for various scenarios."""
        # Standard case
        self.assertEqual(
            _round_decimal(Decimal("123.4567"), Decimal("0.01")),
            Decimal("123.45"),
        )
        # More decimal places
        self.assertEqual(
            _round_decimal(Decimal("99.99999"), Decimal("0.01")),
            Decimal("99.99"),
        )
        # Larger number
        self.assertEqual(
            _round_decimal(Decimal("123456789.123456789"), Decimal("0.0001")),
            Decimal("123456789.1234"),
        )

    def test_round_decimal(self):
        """Test rounding a Decimal to a specified increment."""
        self.assertEqual(
            _round_decimal(Decimal("1.234"), Decimal("0.01")), Decimal("1.23")
        )
        self.assertEqual(
            _round_decimal(Decimal("1.239"), Decimal("0.01")), Decimal("1.23")
        )
        self.assertEqual(
            _round_decimal(Decimal("1.23"), Decimal("0.1")), Decimal("1.2")
        )

    def test_rounding_with_increment_of_one(self):
        """Test rounding with an increment of 1 to kill mutant #20."""
        result = _round_decimal(Decimal("123.456"), Decimal("1"))
        self.assertEqual(result, Decimal("123"))

    def test_rounding_with_decimal_increment(self):
        """Test rounding with a non-integer increment to kill mutant #25."""
        result = _round_decimal(Decimal("10.55"), Decimal("0.1"))
        self.assertEqual(result, Decimal("10.5"))

    def test_round_decimal_with_integer_increment(self):
        """Test rounding with an integer increment greater than 1."""
        self.assertEqual(
            _round_decimal(Decimal("123.45"), Decimal("2")),
            Decimal("122"),
        )

    def test_round_decimal_no_change(self):
        """Test that no rounding occurs if the value is already on an increment."""
        self.assertEqual(
            _round_decimal(Decimal("123.45"), Decimal("0.01")),
            Decimal("123.45"),
        )

    # --- Tests for determine_sell_orders_params ---

    def test_remaining_quantity_initialization(self):
        """Test that remaining_quantity is correctly initialized, killing mutant #64."""
        # This is a very simple, two-tier case that must succeed.
        # The mutant sets remaining_quantity=None, causing a TypeError and returning [].
        # This test will fail because len([]) is not 2.
        params = determine_sell_orders_params(
            buy_price=Decimal("100.0"),
            buy_quantity=Decimal("1.0"),
            product_details=self.product_details,
            config_asset_params=self.config_asset_params,
            logger=self.mock_logger,
        )
        self.assertEqual(len(params), 2)  # There are two tiers in the default config

    def test_determine_sell_orders_happy_path(self):
        """Test standard tiered sell order creation."""
        params = determine_sell_orders_params(
            Decimal("100.0"),
            Decimal("1.0"),
            self.product_details,
            self.config_asset_params,
            self.mock_logger,
        )
        self.assertEqual(len(params), 2)

        expected_tier1 = {"price": "102.00", "size": "0.5000"}
        expected_tier2 = {"price": "104.00", "size": "0.5000"}

        self.assertDictEqual(params[0], expected_tier1)
        self.assertDictEqual(params[1], expected_tier2)

    def test_last_tier_sells_remaining_quantity(self):
        """Test last tier sells all remaining quantity, with rounding (mutant #67)."""
        # Use a quantity that will have a remainder after rounding
        buy_quantity = Decimal("1.0001")
        self.config_asset_params["sell_profit_tiers"] = [
            {"profit_target": 0.01, "quantity_percentage": 0.5},
            {"profit_target": 0.02, "quantity_percentage": 0.5},
        ]

        params = determine_sell_orders_params(
            Decimal("100.0"),
            buy_quantity,
            self.product_details,
            self.config_asset_params,
            self.mock_logger,
        )

        self.assertEqual(len(params), 2)
        # Tier 1: 1.0001 * 0.5 = 0.50005, rounded down to 0.5000
        self.assertEqual(params[0]["size"], "0.5000")
        # Tier 2 (last): Sells the rest (1.0001 - 0.5000 = 0.5001)
        self.assertEqual(params[1]["size"], "0.5001")

        total_sold_quantity = sum(Decimal(p["size"]) for p in params)
        self.assertEqual(total_sold_quantity, buy_quantity)

    def test_skips_tier_if_quantity_below_min_size(self):
        """Test tier is skipped if its quantity is below the minimum."""
        # Set a low quantity percentage to ensure the first tier is skipped
        self.config_asset_params["sell_profit_tiers"][0][
            "quantity_percentage"
        ] = 0.00001

        params = determine_sell_orders_params(
            Decimal("100.0"),
            Decimal("10.0"),  # High enough quantity to not be the issue
            self.product_details,
            self.config_asset_params,
            self.mock_logger,
        )

        # The first tier should be skipped, and the second should be processed
        self.assertEqual(len(params), 1)
        self.assertEqual(params[0]["price"], "104.00")
        self.assertEqual(params[0]["size"], "10.0000")

        # Verify that the info log was called for the skipped tier
        self.mock_logger.info.assert_called_once()
        call_args, call_kwargs = self.mock_logger.info.call_args
        self.assertIn("[BTC-USD] Skipping tier 1", call_args[0])
        self.assertIn("size is below min", call_args[0])

        # Kill mutant #92 by checking the 'extra' dictionary content
        extra_data = call_kwargs.get("extra", {})
        self.assertIn("calculated_size", extra_data)
        self.assertEqual(extra_data.get("tier"), 1)

    def test_skips_tier_if_quantity_below_min_size_logs_extra_details(self):
        """Test that the log message for a skipped tier contains extra details."""
        determine_sell_orders_params(
            Decimal("100.0"),
            Decimal("0.001"),
            self.product_details,
            self.config_asset_params,
            self.mock_logger,
        )

        self.mock_logger.info.assert_called_once()
        _call_args, call_kwargs = self.mock_logger.info.call_args
        self.assertIn("extra", call_kwargs)
        extra = call_kwargs["extra"]
        self.assertEqual(extra["tier"], 1)
        self.assertEqual(extra["calculated_size"], "0.0005")
        self.assertEqual(extra["min_size"], "0.001")

    def test_missing_product_id_logs_default(self):
        """Test that a default product_id is used when missing, killing mutant #1."""
        product_details = self.product_details.copy()
        del product_details["product_id"]
        # Trigger a KeyError to check the asset_id in the log
        del product_details["quote_increment"]

        params = determine_sell_orders_params(
            Decimal("100.0"),
            Decimal("1.0"),
            product_details,
            self.config_asset_params,
            self.mock_logger,
        )

        self.assertEqual(params, [])
        self.mock_logger.error.assert_called_once()
        call_args, kwargs = self.mock_logger.error.call_args
        self.assertIn(
            (
                "[UNKNOWN_ASSET] Missing key in config or product details: "
                "'quote_increment'"
            ),
            call_args[0],
        )
        self.assertTrue(kwargs.get("exc_info"))

    def test_returns_empty_if_all_tiers_below_min_size(self):
        """Test empty list is returned if all tiers are below minimum size."""
        self.product_details["base_min_size"] = "10.0"  # Set a high min size
        params = determine_sell_orders_params(
            Decimal("100.0"),
            Decimal("1.0"),
            self.product_details,
            self.config_asset_params,
            self.mock_logger,
        )
        self.assertEqual(params, [])
        # The default config has 2 tiers, so info should be called twice.
        self.assertEqual(self.mock_logger.info.call_count, 2)

        # Check the log call for the first tier
        call_args, call_kwargs = self.mock_logger.info.call_args_list[0]
        self.assertIn("Skipping tier 1 because its size is below min", call_args[0])
        extra_data = call_kwargs.get("extra", {})
        self.assertIn("calculated_size", extra_data)
        self.assertEqual(extra_data.get("min_size"), "10.0")

    def test_skips_tier_if_quantity_is_zero(self):
        """Test that tiers with a zero quantity are skipped (mutant #81)."""
        config = {
            "sell_profit_tiers": [{"profit_target": 0.01, "quantity_percentage": 1.0}]
        }
        params = determine_sell_orders_params(
            Decimal("50000"),
            Decimal("1E-8"),
            self.product_details,
            config,
            self.mock_logger,
        )
        self.assertEqual(params, [])
        self.mock_logger.warning.assert_called_once_with(
            "[BTC-USD] Tier 1 sell quantity is zero. Skipping."
        )

    def test_input_validation_assertions(self):
        """Test that assertions fire for invalid inputs, killing mutant #32."""
        # Test non-positive buy_price
        result = determine_sell_orders_params(
            Decimal("0"),
            Decimal("1"),
            self.product_details,
            self.config_asset_params,
            self.mock_logger,
        )
        self.assertEqual(result, [])
        self.mock_logger.error.assert_called_once()
        call_args, kwargs = self.mock_logger.error.call_args
        self.assertIn(
            "Invalid value for sell calc: Buy price must be positive.", call_args[0]
        )
        self.assertTrue(kwargs.get("exc_info"))

        # Test non-positive buy_quantity
        self.mock_logger.reset_mock()
        result = determine_sell_orders_params(
            Decimal("1"),
            Decimal("0"),
            self.product_details,
            self.config_asset_params,
            self.mock_logger,
        )
        self.assertEqual(result, [])
        self.mock_logger.error.assert_called_once()
        call_args, kwargs = self.mock_logger.error.call_args
        self.assertIn(
            "Invalid value for sell calc: Buy quantity must be positive.", call_args[0]
        )
        self.assertTrue(kwargs.get("exc_info"))

    def test_key_error_handling_in_product_details(self):
        """Test graceful failure on missing product_details key (mutant #57)."""
        bad_details = self.product_details.copy()
        del bad_details["quote_increment"]
        result = determine_sell_orders_params(
            Decimal("100"),
            Decimal("1"),
            bad_details,
            self.config_asset_params,
            self.mock_logger,
        )
        self.assertEqual(result, [])
        self.mock_logger.error.assert_called_once()
        call_args, kwargs = self.mock_logger.error.call_args
        self.assertIn(
            "[BTC-USD] Missing key in config or product details: 'quote_increment'",
            call_args[0],
        )
        self.assertTrue(kwargs.get("exc_info"))

    def test_buy_price_le_one_is_valid(self):
        """Test that a buy_price less than or equal to 1 is handled correctly."""
        # This test is designed to kill a mutant that changes `> 0` to `> 1`
        buy_price = Decimal("1")
        buy_quantity = Decimal("10")

        result = determine_sell_orders_params(
            buy_price,
            buy_quantity,
            self.product_details,
            self.config_asset_params,
            self.mock_logger,
        )
        self.assertTrue(result)
        self.mock_logger.error.assert_not_called()

    def test_non_positive_buy_price_raises_error(self):
        """Test non-positive buy_price is handled gracefully (mutant #37)."""
        result = determine_sell_orders_params(
            Decimal("0"),
            Decimal("1.0"),
            self.product_details,
            self.config_asset_params,
            self.mock_logger,
        )
        self.assertEqual(result, [])
        self.mock_logger.error.assert_called_once_with(
            "[BTC-USD] Invalid value for sell calc: Buy price must be positive.",
            exc_info=True,
        )

    def test_buy_price_of_one_is_valid(self):
        """Test that a buy_price of 1 is valid, killing mutant #36."""
        # This test is designed to kill the mutant that changes `> 0` to `> 1`.
        # A buy_price of 1 should be valid, but will fail the mutated assertion.
        result = determine_sell_orders_params(
            Decimal("1.0"),
            Decimal("1.0"),
            self.product_details,
            self.config_asset_params,
            self.mock_logger,
        )
        self.assertNotEqual(result, [])
        self.mock_logger.error.assert_not_called()

    def test_non_positive_buy_quantity_raises_error(self):
        """Test non-positive buy_quantity is handled gracefully (mutant #40)."""
        result = determine_sell_orders_params(
            Decimal("100.0"),
            Decimal("0"),
            self.product_details,
            self.config_asset_params,
            self.mock_logger,
        )
        self.assertEqual(result, [])
        self.mock_logger.error.assert_called_once_with(
            "[BTC-USD] Invalid value for sell calc: Buy quantity must be positive.",
            exc_info=True,
        )

    def test_buy_quantity_of_one_is_valid(self):
        """Test that a buy_quantity of 1 is valid, which kills mutant #35."""
        # This test is designed to kill the mutant that changes `> 0` to `> 1`.
        # A buy_quantity of 1 should be valid, but will fail the mutated assertion.
        try:
            determine_sell_orders_params(
                Decimal("100.0"),
                Decimal("1.0"),
                self.product_details,
                self.config_asset_params,
                self.mock_logger,
            )
        except AssertionError as e:
            self.fail(
                "determine_sell_orders_params raised AssertionError unexpectedly "
                f"for buy_quantity=1: {e}"
            )

    def test_missing_sell_profit_tiers_is_handled(self):
        """Test that missing 'sell_profit_tiers' in config is handled gracefully."""
        config_asset_params = self.config_asset_params.copy()
        del config_asset_params["sell_profit_tiers"]

        result = determine_sell_orders_params(
            Decimal("100.0"),
            Decimal("1.0"),
            self.product_details,
            config_asset_params,
            self.mock_logger,
        )

        self.assertEqual(result, [])
        self.mock_logger.error.assert_called_once()
        call_args, _ = self.mock_logger.error.call_args
        self.assertIn("'sell_profit_tiers' not found", call_args[0])

    def test_zero_profit_target_raises_error(self):
        """Test that a zero profit_target is handled gracefully."""
        bad_config = {
            "sell_profit_tiers": [
                {"profit_target": 0, "quantity_percentage": 0.5},
                {"profit_target": 0.04, "quantity_percentage": 0.5},
            ]
        }
        result = determine_sell_orders_params(
            Decimal("100"),
            Decimal("10"),
            self.product_details,
            bad_config,
            self.mock_logger,
        )
        self.assertEqual(result, [])
        self.mock_logger.error.assert_called_once()
        call_args, kwargs = self.mock_logger.error.call_args
        self.assertIn(
            "Invalid value for sell calc: Tier 1 profit target must be positive.",
            call_args[0],
        )
        self.assertTrue(kwargs.get("exc_info"))

    def test_zero_quantity_percentage_raises_error(self):
        """Test that a zero quantity_percentage is handled gracefully."""
        bad_config = {
            "sell_profit_tiers": [
                {"profit_target": 0.02, "quantity_percentage": 0},
                {"profit_target": 0.04, "quantity_percentage": 0.5},
            ]
        }
        result = determine_sell_orders_params(
            Decimal("100"),
            Decimal("10"),
            self.product_details,
            bad_config,
            self.mock_logger,
        )
        self.assertEqual(result, [])
        self.mock_logger.error.assert_called_once()
        call_args, kwargs = self.mock_logger.error.call_args
        self.assertIn(
            (
                "Invalid value for sell calc: "
                "Tier 1 quantity percentage must be between 0 and 1."
            ),
            call_args[0],
        )
        self.assertTrue(kwargs.get("exc_info"))

    def test_quantity_percentage_of_one_is_valid(self):
        """Test that a quantity_percentage of 1 is valid."""
        config = {
            "sell_profit_tiers": [
                {"profit_target": 0.02, "quantity_percentage": 1},
            ]
        }
        result = determine_sell_orders_params(
            Decimal("100"),
            Decimal("10"),
            self.product_details,
            config,
            self.mock_logger,
        )
        self.assertEqual(len(result), 1)

    def test_quantity_percentage_greater_than_one_raises_error(self):
        """Test that a quantity_percentage > 1 is handled gracefully."""
        bad_config = {
            "sell_profit_tiers": [
                {"profit_target": 0.02, "quantity_percentage": 1.1},
            ]
        }
        result = determine_sell_orders_params(
            Decimal("100"),
            Decimal("10"),
            self.product_details,
            bad_config,
            self.mock_logger,
        )
        self.assertEqual(result, [])
        expected_error_msg = (
            "[BTC-USD] Invalid value for sell calc: "
            "Tier 1 quantity percentage must be between 0 and 1."
        )
        self.mock_logger.error.assert_called_once_with(
            expected_error_msg, exc_info=True
        )

    def test_none_quote_increment_causes_exception(self):
        """Test that a None quote_increment raises an exception, killing mutant #7."""
        product_details = self.product_details.copy()
        product_details["quote_increment"] = None

        # Use a single tier to avoid excessive logging in mutant runs
        config_asset_params = {
            "sell_profit_tiers": [
                {"profit_target": "0.01", "quantity_percentage": "0.2"},
            ]
        }

        result = determine_sell_orders_params(
            Decimal("100.0"),
            Decimal("1.0"),
            product_details,
            config_asset_params,
            self.mock_logger,
        )

        self.assertEqual(result, [])
        # It should be called for the single tier
        self.mock_logger.error.assert_called_once()
        _args, kwargs = self.mock_logger.error.call_args
        self.assertIn("Invalid value for sell calc", _args[0])
        self.assertTrue(kwargs.get("exc_info"))

    def test_assertion_error_in_product_details_logs_correctly(self):
        """Test that an assertion error in product details is logged correctly."""
        # Force an exception by providing an invalid 'base_increment' for an assertion
        product_details = self.product_details.copy()
        product_details["base_increment"] = "0"

        result = determine_sell_orders_params(
            Decimal("100.0"),
            Decimal("1.0"),
            product_details,
            self.config_asset_params,
            self.mock_logger,
        )

        self.assertEqual(result, [])
        self.mock_logger.error.assert_called_once()
        _args, kwargs = self.mock_logger.error.call_args
        self.assertIn("Invalid value for sell calc", _args[0])
        self.assertTrue(kwargs.get("exc_info"))

    def test_key_error_in_sell_profit_tiers(self):
        """Test graceful failure for malformed sell_profit_tiers."""
        # Test with 'quantity_percentage' missing
        malformed_tiers = [{"profit_target": 0.02}]
        self.config_asset_params["sell_profit_tiers"] = malformed_tiers

        result = determine_sell_orders_params(
            Decimal("100.0"),
            Decimal("1.0"),
            self.product_details,
            self.config_asset_params,
            self.mock_logger,
        )

        self.assertEqual(result, [])
        self.mock_logger.error.assert_called_once_with(
            "[BTC-USD] Missing key in config or product details: 'quantity_percentage'",
            exc_info=True,
        )

    def test_key_error_in_sell_profit_tiers_missing_target(self):
        """Test that a missing 'profit_target' in a tier is handled."""
        malformed_tiers = [{"quantity_percentage": 0.2}]
        self.config_asset_params["sell_profit_tiers"] = malformed_tiers

        result = determine_sell_orders_params(
            Decimal("100.0"),
            Decimal("1.0"),
            self.product_details,
            self.config_asset_params,
            self.mock_logger,
        )

        self.assertEqual(result, [])
        self.mock_logger.error.assert_called_once_with(
            "[BTC-USD] Missing key in config or product details: 'profit_target'",
            exc_info=True,
        )

    def test_key_error_on_missing_base_increment(self):
        """Test that a missing 'base_increment' in product_details is handled."""
        del self.product_details["base_increment"]

        result = determine_sell_orders_params(
            Decimal("100.0"),
            Decimal("1.0"),
            self.product_details,
            self.config_asset_params,
            self.mock_logger,
        )

        self.assertEqual(result, [])
        self.mock_logger.error.assert_called_once_with(
            "[BTC-USD] Missing key in config or product details: 'base_increment'",
            exc_info=True,
        )

    def test_invalid_profit_target_in_tiers_is_handled_gracefully(self):
        """Test invalid profit target in a tier is handled gracefully (mutant #49)."""
        config_asset_params = self.config_asset_params.copy()
        # Make the second tier invalid
        config_asset_params["sell_profit_tiers"] = [
            {"profit_target": "0.01", "quantity_percentage": "0.5"},
            {"profit_target": "-0.01", "quantity_percentage": "0.5"},
        ]

        result = determine_sell_orders_params(
            Decimal("100.0"),
            Decimal("1.0"),
            self.product_details,
            config_asset_params,
            self.mock_logger,
        )

        self.assertEqual(result, [])
        self.mock_logger.error.assert_called_once()
        call_args, kwargs = self.mock_logger.error.call_args
        self.assertIn(
            "Invalid value for sell calc: Tier 2 profit target must be positive.",
            call_args[0],
        )
        self.assertTrue(kwargs.get("exc_info"))

    def test_type_error_on_invalid_profit_target(self):
        """Test that a TypeError is handled gracefully for non-numeric profit_target."""
        self.config_asset_params["sell_profit_tiers"] = [
            {"profit_target": "not-a-number", "quantity_percentage": "0.5"}
        ]

        params = determine_sell_orders_params(
            Decimal("100.0"),
            Decimal("1.0"),
            self.product_details,
            self.config_asset_params,
            self.mock_logger,
        )

        self.assertEqual(params, [])
        self.mock_logger.error.assert_called_once()
        call_args, kwargs = self.mock_logger.error.call_args
        self.assertIn("Invalid value for sell calc", call_args[0])
        self.assertTrue(kwargs.get("exc_info"))

    def test_continue_on_zero_quantity_tier(self):
        """Test loop continues if a tier has zero quantity (mutant #82)."""
        # A tier must pass validation but result in a quantity that rounds to zero,
        # ensuring the loop continues to the next tier instead of breaking.
        test_config = {
            "sell_profit_tiers": [
                {
                    "profit_target": "0.01",
                    # This percentage > 0 will result in a quantity that rounds to 0.
                    "quantity_percentage": "0.000000001",
                },
                {
                    "profit_target": "0.02",
                    "quantity_percentage": "1.0",  # This tier is processed.
                },
            ]
        }

        params = determine_sell_orders_params(
            buy_price=Decimal("100.0"),
            buy_quantity=Decimal("1.0"),
            product_details=self.product_details,
            config_asset_params=test_config,
            logger=self.mock_logger,
        )

        # The loop should not break; it should process the second tier.
        self.assertEqual(len(params), 1)
        self.assertEqual(params[0]["price"], "102.00")
        self.assertEqual(Decimal(params[0]["size"]), Decimal("1.0"))

        # Check that the first tier was skipped with the correct warning.
        self.mock_logger.warning.assert_called_once_with(
            "[BTC-USD] Tier 1 sell quantity is zero. Skipping."
        )

    def test_internal_type_error_is_handled(self):
        """Test that a TypeError from internal calculations is handled."""
        with patch(
            "trading.order_calculator._round_decimal",
            side_effect=TypeError("mocked error"),
        ):
            params = determine_sell_orders_params(
                Decimal("100.0"),
                Decimal("1.0"),
                self.product_details,
                self.config_asset_params,
                self.mock_logger,
            )

        self.assertEqual(params, [])
        self.mock_logger.error.assert_called_once()
        call_args, kwargs = self.mock_logger.error.call_args
        # This check is now more robust and will not fail due to prefixes.
        self.assertIn("Invalid value for sell calc:", call_args[0])
        self.assertTrue(kwargs.get("exc_info"))

    def test_sell_quantity_of_one_is_valid(self):
        """Test a sell quantity of 1 is processed correctly (mutant #79)."""
        product_details = self.product_details.copy()
        product_details["base_increment"] = "1"

        test_config = {
            "sell_profit_tiers": [
                {"profit_target": "0.02", "quantity_percentage": "1.0"},
            ]
        }

        params = determine_sell_orders_params(
            buy_price=Decimal("100.0"),
            buy_quantity=Decimal("1"),
            product_details=product_details,
            config_asset_params=test_config,
            logger=self.mock_logger,
        )

        self.assertEqual(len(params), 1)
        self.assertEqual(Decimal(params[0]["size"]), Decimal("1"))
        self.mock_logger.warning.assert_not_called()

    def test_last_tier_uses_remaining_quantity(self):
        """Test last tier uses remaining quantity (mutant #74)."""
        config_asset_params = {
            "sell_profit_tiers": [
                {"profit_target": "0.01", "quantity_percentage": "0.3"},
                {"profit_target": "0.02", "quantity_percentage": "0.3"},
                # The last tier uses the remaining quantity. Its `quantity_percentage`
                # is for validation only; it's ignored for the size calculation.
                {"profit_target": "0.03", "quantity_percentage": "0.4"},
            ]
        }

        params = determine_sell_orders_params(
            Decimal("50000"),
            Decimal("1.0"),
            self.product_details,
            config_asset_params,
            self.mock_logger,
        )

        self.assertEqual(len(params), 3)
        self.mock_logger.error.assert_not_called()
        tier1_qty = Decimal(params[0]["size"])
        tier2_qty = Decimal(params[1]["size"])
        tier3_qty = Decimal(params[2]["size"])
        self.assertEqual(tier1_qty, Decimal("0.3"))
        self.assertEqual(tier2_qty, Decimal("0.3"))
        self.assertEqual(tier3_qty, Decimal("0.4"))
        self.assertEqual(tier1_qty + tier2_qty + tier3_qty, Decimal("1.0"))

    def test_attribute_error_in_sell_calc_logs_exc_info(self):
        """Test AttributeError in sell calc logs exc_info (mutant #97)."""
        with patch(
            "trading.order_calculator._calculate_tier_price_and_size",
            side_effect=AttributeError("mock attribute error"),
        ):
            result = determine_sell_orders_params(
                Decimal("100.0"),
                Decimal("1.0"),
                self.product_details,
                self.config_asset_params,
                self.mock_logger,
            )
            self.assertEqual(result, [])
            self.mock_logger.error.assert_called_once()
            _args, kwargs = self.mock_logger.error.call_args
            self.assertIn("Attribute error in sell calc", _args[0])
            self.assertTrue(kwargs.get("exc_info"))

    def test_unexpected_exception_in_sell_calc_logs_exc_info(self):
        """Test generic Exception in sell calc logs exc_info (mutant #98)."""
        with patch(
            "trading.order_calculator._calculate_tier_price_and_size",
            side_effect=Exception("mock unexpected error"),
        ):
            result = determine_sell_orders_params(
                Decimal("100.0"),
                Decimal("1.0"),
                self.product_details,
                self.config_asset_params,
                self.mock_logger,
            )
            self.assertEqual(result, [])
            self.mock_logger.error.assert_called_once()
            _args, kwargs = self.mock_logger.error.call_args
            self.assertIn("Unexpected exception in sell calc", _args[0])
            self.assertTrue(kwargs.get("exc_info"))

    def test_decimal_invalid_operation_in_sell_calc_is_handled(self):
        """
        Test that a decimal.InvalidOperation in _calculate_tier_price_and_size
        is handled gracefully, killing mutant #27.
        """
        original_decimal_constructor = decimal.Decimal

        def mock_decimal(value, *args, **kwargs):
            if str(value) == "1":
                raise decimal.InvalidOperation("Mocked invalid operation for '1'")
            return original_decimal_constructor(value, *args, **kwargs)

        with patch("trading.order_calculator.Decimal", side_effect=mock_decimal):
            result = determine_sell_orders_params(
                Decimal("100.0"),
                Decimal("1.0"),
                self.product_details,
                self.config_asset_params,
                self.mock_logger,
            )
            self.assertEqual(result, [])
            self.mock_logger.error.assert_called_once()
            call_args, kwargs = self.mock_logger.error.call_args
            self.assertEqual(
                call_args[0],
                (
                    "[BTC-USD] Invalid value for sell calc: "
                    "Mocked invalid operation for '1'"
                ),
            )
            self.assertTrue(kwargs.get("exc_info"))

    def test_invalid_quantity_percentage_in_tier(self):
        """Test invalid quantity_percentage in a tier is handled (mutant #46)."""
        self.config_asset_params["sell_profit_tiers"][0][
            "quantity_percentage"
        ] = "not-a-decimal"

        result = determine_sell_orders_params(
            Decimal("100.0"),
            Decimal("1.0"),
            self.product_details,
            self.config_asset_params,
            self.mock_logger,
        )

        self.assertEqual(result, [])
        self.mock_logger.error.assert_called_once()
        call_args, kwargs = self.mock_logger.error.call_args
        self.assertIn("Invalid value for sell calc", call_args[0])
        self.assertTrue(kwargs.get("exc_info"))


class TestCalculateTierPriceAndSize(unittest.TestCase):
    def test_successful_calculation(self):
        """Test a successful tier calculation."""
        buy_price = Decimal("100.0")
        quantity = Decimal("0.5")
        profit_target = Decimal("0.02")  # 2%
        quote_increment = Decimal("0.01")
        base_increment = Decimal("0.0001")

        rounded_size, rounded_price = _calculate_tier_price_and_size(
            buy_price,
            quantity,
            profit_target,
            quote_increment,
            base_increment,
        )

        self.assertEqual(rounded_size, Decimal("0.5000"))
        self.assertEqual(rounded_price, Decimal("102.00"))

    @unittest.expectedFailure
    def test_invalid_decimal_in_calculation_raises_exception(self):
        """
        Test that an invalid decimal operation is raised, killing mutant #27.
        This test is expected to fail on un-mutated code.
        """
        with self.assertRaises(decimal.InvalidOperation):
            _calculate_tier_price_and_size(
                Decimal("100.0"),
                Decimal("0.5"),
                Decimal("0.02"),
                Decimal("0.01"),
                Decimal("0.0001"),
            )


class TestPrivateHelpers(unittest.TestCase):
    def test_round_decimal_asserts_on_invalid_value_type(self):
        """Test _round_decimal asserts on a non-Decimal value."""
        with self.assertRaises(AssertionError) as cm:
            _round_decimal(123.45, Decimal("0.01"))  # type: ignore
        self.assertEqual(str(cm.exception), "Value to round must be a Decimal.")

    def test_round_decimal_asserts_on_string_value_type(self):
        """Test _round_decimal asserts on a string value."""
        with self.assertRaises(AssertionError) as cm:
            _round_decimal("not a decimal", Decimal("1"))
        self.assertEqual(str(cm.exception), "Value to round must be a Decimal.")

    def test_round_decimal_asserts_on_zero_increment(self):
        """Test _round_decimal asserts on a zero increment, killing mutant #22."""
        with self.assertRaises(AssertionError) as cm:
            _round_decimal(Decimal("123.45"), Decimal("0"))
        self.assertEqual(str(cm.exception), "Increment must be a positive Decimal.")

    def test_round_decimal_asserts_on_negative_increment(self):
        """Test _round_decimal asserts on a negative increment."""
        with self.assertRaises(AssertionError) as cm:
            _round_decimal(Decimal("123.45"), Decimal("-0.01"))
        self.assertEqual(str(cm.exception), "Increment must be a positive Decimal.")


class TestCalculateBuyOrderDetails(unittest.TestCase):
    def test_successful_calculation(self):
        """Test a successful buy order calculation."""
        result = calculate_buy_order_details(
            self.buy_amount_usd,
            self.last_close_price,
            self.product_details,
            self.mock_logger,
        )

        self.assertIsNotNone(result)
        self.assertIsInstance(result, tuple)

        size, price = result

        expected_price = Decimal("50000.00")
        expected_size = Decimal("0.0020")

        self.assertEqual(price, expected_price)
        self.assertEqual(size, expected_size)

        self.mock_logger.error.assert_not_called()
        self.mock_logger.warning.assert_not_called()

    def setUp(self):
        """Set up test fixtures."""
        self.mock_logger = Mock(spec=logging.Logger)
        self.product_details = {
            "product_id": "BTC-USD",
            "quote_increment": "0.01",
            "base_increment": "0.0001",
            "base_min_size": "0.001",
        }
        self.buy_amount_usd = Decimal("100")
        self.last_close_price = Decimal("50000")

    @patch("trading.order_calculator._round_decimal")
    def test_calculate_buy_order_details_zero_limit_price(self, mock_round_decimal):
        """Test handling of a calculated limit price of zero."""
        mock_round_decimal.return_value = Decimal("0")

        result = calculate_buy_order_details(
            self.buy_amount_usd,
            self.last_close_price,
            self.product_details,
            self.mock_logger,
        )

        self.assertIsNone(result)
        self.mock_logger.error.assert_called_once_with(
            "[BTC-USD] Calculated limit price is zero or negative."
        )

    @patch("trading.order_calculator._round_decimal")
    def test_calculate_buy_order_details_generic_exception(self, mock_round_decimal):
        """Test the generic exception handler."""
        mock_round_decimal.side_effect = Exception("A wild error appears!")

        result = calculate_buy_order_details(
            self.buy_amount_usd,
            self.last_close_price,
            self.product_details,
            self.mock_logger,
        )

        self.assertIsNone(result)
        self.mock_logger.error.assert_called_once()
        args, kwargs = self.mock_logger.error.call_args
        self.assertIn("Exception calculating buy order details", args[0])
        self.assertTrue(kwargs.get("exc_info"))

    def test_limit_price_of_one(self):
        """Test successful calculation when the calculated limit_price is 1."""
        # Set a last_close_price that will result in a limit_price of 1
        self.last_close_price = Decimal("1.00")

        result = calculate_buy_order_details(
            self.buy_amount_usd,
            self.last_close_price,
            self.product_details,
            self.mock_logger,
        )

        # Add assertions to check logger output for debugging
        self.mock_logger.error.assert_not_called()
        self.mock_logger.warning.assert_not_called()

        # With mutant #12 (if limit_price <= 1), this will fail
        self.assertIsNotNone(result)

        size, price = result
        self.assertEqual(price, Decimal("1.00"))
        self.assertEqual(size, Decimal("100.0000"))  # size = round(100/1)

    def test_limit_price_of_one_is_valid(self):
        """Test that a limit_price of 1 is valid, which kills mutant #13."""
        # This test is designed to kill the mutant that changes `<= 0` to `<= 1`
        last_close_price = Decimal("1.00")
        result = calculate_buy_order_details(
            self.buy_amount_usd,
            last_close_price,
            self.product_details,
            self.mock_logger,
        )
        self.assertIsNotNone(result)
        self.mock_logger.error.assert_not_called()

    def test_size_below_minimum(self):
        """Test that a warning is logged if the calculated size is below the minimum."""
        # Use a low USD amount to ensure the calculated size is below the minimum
        self.buy_amount_usd = Decimal("1")  # $1 buy

        result = calculate_buy_order_details(
            self.buy_amount_usd,
            self.last_close_price,
            self.product_details,
            self.mock_logger,
        )

        self.assertIsNone(result)
        self.mock_logger.warning.assert_called_once()
        call_args, _ = self.mock_logger.warning.call_args
        self.assertIn("Calculated buy size", call_args[0])
        self.assertIn("is below min size", call_args[0])
        self.mock_logger.error.assert_not_called()

    def test_size_equal_to_minimum(self):
        """Test successful calculation when size is exactly the minimum size."""
        # Set buy amount so the calculated size is exactly the minimum.
        # size = round(50 / 50000) = 0.001, which is base_min_size.
        self.buy_amount_usd = Decimal("50")

        result = calculate_buy_order_details(
            self.buy_amount_usd,
            self.last_close_price,
            self.product_details,
            self.mock_logger,
        )

        # With mutant #15 (if size <= base_min_size), this will fail.
        self.assertIsNotNone(result)
        self.mock_logger.warning.assert_not_called()

    def test_key_error_handling(self):
        """Test that None is returned if a key is missing in product_details."""
        bad_details = self.product_details.copy()
        del bad_details["base_increment"]

        result = calculate_buy_order_details(
            self.buy_amount_usd,
            self.last_close_price,
            bad_details,
            self.mock_logger,
        )

        self.assertIsNone(result)
        self.mock_logger.error.assert_called_once()
        call_args, _ = self.mock_logger.error.call_args
        self.assertIn(
            "Missing required key in product_details: 'base_increment'", call_args[0]
        )

    def test_key_error_on_base_min_size(self):
        """Test that a KeyError on 'base_min_size' is handled."""
        bad_details = self.product_details.copy()
        del bad_details["base_min_size"]

        result = calculate_buy_order_details(
            self.buy_amount_usd,
            self.last_close_price,
            bad_details,
            self.mock_logger,
        )

        self.assertIsNone(result)
        self.mock_logger.error.assert_called_once()
        call_args, _ = self.mock_logger.error.call_args
        self.assertEqual(
            "[BTC-USD] Missing required key in product_details: 'base_min_size'",
            call_args[0],
        )

    def test_invalid_quote_increment_is_handled(self):
        """Test that an invalid quote_increment is handled gracefully."""
        product_details = self.product_details.copy()
        product_details["quote_increment"] = "not-a-decimal"

        result = calculate_buy_order_details(
            self.buy_amount_usd,
            self.last_close_price,
            product_details,
            self.mock_logger,
        )

        self.assertIsNone(result)
        self.mock_logger.error.assert_called_once()
        call_args, kwargs = self.mock_logger.error.call_args
        self.assertIn("Invalid numeric value in product_details", call_args[0])
        self.assertTrue(kwargs.get("exc_info"))

    def test_limit_price_rounds_to_zero(self):
        """Test a limit_price that rounds to zero is handled (mutants #11, #12)."""
        mock_logger = MagicMock(spec=logging.Logger)
        product_details = {
            "product_id": "BTC-USD",
            "quote_increment": "0.01",
            "base_increment": "0.0001",
            "base_min_size": "0.001",
        }
        # A very small price that will round down to 0
        last_close_price = Decimal("0.00001")

        result = calculate_buy_order_details(
            Decimal("10"),
            last_close_price,
            product_details,
            mock_logger,
        )

        self.assertIsNone(result)
        # Ensure the specific error is logged, not the generic one.
        mock_logger.error.assert_called_once()
        call_args, kwargs = mock_logger.error.call_args
        self.assertEqual(
            call_args[0], "[BTC-USD] Calculated limit price is zero or negative."
        )
        # The generic handler passes exc_info=True, the specific one does not.
        self.assertIsNone(kwargs.get("exc_info"))

    def test_invalid_numeric_value_in_product_details(self):
        """Test that a TypeError or InvalidOperation is handled gracefully."""
        # This test should kill mutant #9
        invalid_details = self.product_details.copy()
        invalid_details["base_min_size"] = "not-a-valid-decimal"

        result = calculate_buy_order_details(
            self.buy_amount_usd,
            self.last_close_price,
            invalid_details,
            self.mock_logger,
        )

        self.assertIsNone(result)
        self.mock_logger.error.assert_called_once()
        call_args, kwargs = self.mock_logger.error.call_args
        self.assertIn("Invalid numeric value in product_details", call_args[0])
        self.assertTrue(kwargs.get("exc_info"))

    def test_missing_product_id_logs_default_asset(self):
        """Test default asset ID is logged if product_id is missing (mutant #8)."""
        details_without_id = self.product_details.copy()
        del details_without_id["product_id"]
        del details_without_id["base_increment"]
        result = calculate_buy_order_details(
            self.buy_amount_usd,
            self.last_close_price,
            details_without_id,
            self.mock_logger,
        )
        self.assertIsNone(result)
        self.mock_logger.error.assert_called_once_with(
            "[UNKNOWN_ASSET] Missing required key in product_details: 'base_increment'"
        )

    def test_size_equal_to_min_size_is_valid(self):
        """Test that an order size equal to the minimum is valid, killing mutant #16."""
        buy_amount_usd = Decimal("0.1")
        last_close_price = Decimal("100")
        # With these values, size will be exactly base_min_size (0.001)
        # size = round(0.1 / 100, 0.001) = 0.001

        product_details = self.product_details.copy()
        product_details["base_min_size"] = "0.001"
        product_details["base_increment"] = "0.001"

        result = calculate_buy_order_details(
            buy_amount_usd,
            last_close_price,
            product_details,
            self.mock_logger,
        )

        self.assertIsNotNone(result)
        self.assertIsInstance(result, tuple)
        # Check size and price
        expected_size = Decimal("0.001")
        expected_price = Decimal("100.00")
        self.assertEqual(result[0], expected_size)
        self.assertEqual(result[1], expected_price)
        self.mock_logger.warning.assert_not_called()
