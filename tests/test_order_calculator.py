from __future__ import annotations

import logging
import unittest
from decimal import Decimal
from unittest.mock import MagicMock

from trading.order_calculator import _round_decimal, determine_sell_orders_params


class TestOrderCalculator(unittest.TestCase):
    def setUp(self):
        """Set up common test data."""
        self.mock_logger = MagicMock(spec=logging.Logger)
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
        """Test that rounding works correctly."""
        self.assertEqual(
            _round_decimal(Decimal("123.456"), Decimal("0.01")),
            Decimal("123.45"),
        )

    def test_round_decimal_no_change(self):
        """Test that no rounding occurs if the value is already on an increment."""
        self.assertEqual(
            _round_decimal(Decimal("123.45"), Decimal("0.01")),
            Decimal("123.45"),
        )

    def test_round_decimal_with_assertion_error(self):
        """Test that _round_decimal raises an error for invalid input types."""
        with self.assertRaises(AssertionError):
            _round_decimal(123.45, Decimal("0.01"))  # type: ignore

    # --- Tests for determine_sell_orders_params ---

    def test_determine_sell_orders_happy_path(self):
        """Test standard tiered sell order creation."""
        params = determine_sell_orders_params(
            100.0, 1.0, self.product_details, self.config_asset_params, self.mock_logger
        )
        self.assertEqual(len(params), 2)
        # Tier 1: Price=102.00, Size=0.5000
        self.assertEqual(params[0]["price"], "102.00")
        self.assertEqual(params[0]["size"], "0.5000")
        # Tier 2: Price=104.00, Size=0.5000
        self.assertEqual(params[1]["price"], "104.00")
        self.assertEqual(params[1]["size"], "0.5000")

    def test_last_tier_sells_remaining_quantity(self):
        """Test that the last tier sells all remaining quantity, even with rounding."""
        self.config_asset_params["sell_profit_tiers"] = [
            {"profit_target": 0.01, "quantity_percentage": 0.3333},
            {"profit_target": 0.02, "quantity_percentage": 0.3333},
            {"profit_target": 0.03, "quantity_percentage": 0.3334},
        ]
        params = determine_sell_orders_params(
            100.0, 1.0, self.product_details, self.config_asset_params, self.mock_logger
        )
        self.assertEqual(len(params), 3)
        # Tier 1: 0.3333
        self.assertEqual(params[0]["size"], "0.3333")
        # Tier 2: 0.3333
        self.assertEqual(params[1]["size"], "0.3333")
        # Tier 3 (last): Sells the rest (1.0 - 0.3333 - 0.3333 = 0.3334)
        self.assertEqual(params[2]["size"], "0.3334")

    def test_skips_tier_if_quantity_below_min_size(self):
        """Test that a tier is skipped if its calculated quantity is below the minimum."""
        # Make the buy quantity very small
        params = determine_sell_orders_params(
            100.0, 0.001, self.product_details, self.config_asset_params, self.mock_logger
        )
        self.assertEqual(len(params), 1)
        # First tier (0.001 * 0.5 = 0.0005) is skipped because it's < 0.001 min_size
        # The last tier gets all the quantity
        self.assertEqual(params[0]["price"], "104.00")
        self.assertEqual(params[0]["size"], "0.0010")

    def test_returns_empty_if_all_tiers_below_min_size(self):
        """Test returns an empty list if no tier meets the minimum size."""
        params = determine_sell_orders_params(
            100.0, 0.0005, self.product_details, self.config_asset_params, self.mock_logger
        )
        self.assertEqual(len(params), 0)

    def test_input_validation_assertions(self):
        """Test that assertions fire for invalid inputs."""
        with self.assertRaises(AssertionError):
            determine_sell_orders_params(0, 1.0, self.product_details, self.config_asset_params, self.mock_logger)
        with self.assertRaises(AssertionError):
            determine_sell_orders_params(100.0, 0, self.product_details, self.config_asset_params, self.mock_logger)
        with self.assertRaises(AssertionError):
            determine_sell_orders_params(100.0, 1.0, {}, self.config_asset_params, self.mock_logger)
        with self.assertRaises(AssertionError):
            determine_sell_orders_params(100.0, 1.0, self.product_details, {}, self.mock_logger)
