"""Main entry point for the v6 crypto trading bot.

This module initializes all necessary components and orchestrates the trading
cycle for each configured asset.

Typical usage:
    python3 main.py

Expects API keys to be set as environment variables as specified in config.py.
"""

import sys
import time
import types

# Internal modules
import config
import coinbase_client
import persistence
import technical_analysis
from trading import signal_analyzer, order_calculator
from trading.trade_manager import TradeManager
from logger import get_logger


def run_bot() -> None:
    """Main entry point for the trading bot.

    Initializes all components, iterates through configured trading pairs,
    and executes the trading logic for each asset.

    Includes comprehensive error handling and logging.
    """
    # Initialize logger
    logger = get_logger("v6_bot_main")
    logger.info("--- Starting v6 crypto trading bot run ---")
    start_time = time.time()

    try:
        # Initialize the Coinbase client. It reads config internally.
        # A RuntimeError will be raised if initialization fails, which is caught below.
        client = coinbase_client.CoinbaseClient()
        logger.info("Coinbase client initialized successfully.")

        # The persistence module is used directly; its directory is created on import.

        # Initialize the TradeManager once, outside the loop
        trade_manager = TradeManager(
            client=client,
            persistence_manager=persistence,
            ta_module=technical_analysis,
            config_module=config,
            logger=logger,
            signal_analyzer=signal_analyzer,
            order_calculator=order_calculator,
        )

        # Process each configured trading pair
        logger.info(f"Processing {len(config.TRADING_PAIRS)} configured trading pairs.")
        for asset_id in config.TRADING_PAIRS:
            logger.info(f"--- Starting trade cycle for {asset_id} ---")
            try:
                trade_manager.process_asset_trade_cycle(asset_id=asset_id)
            except Exception as e:
                logger.error(
                    f"An unexpected error occurred while processing asset {asset_id}: {e}",
                    exc_info=True,
                )
                # Continue to the next asset
            finally:
                logger.info(f"--- Completed trade cycle for {asset_id} ---")

    except RuntimeError as e:
        # This catches critical initialization errors (e.g., from CoinbaseClient)
        logger.critical(
            f"A critical error occurred during bot initialization: {e}", exc_info=True
        )
        sys.exit(1)
    except Exception as e:
        logger.critical(
            f"An unhandled exception occurred at the top level: {e}", exc_info=True
        )
        sys.exit(1)
    finally:
        execution_time = time.time() - start_time
        logger.info(f"--- Trading bot run finished in {execution_time:.2f} seconds ---")


if __name__ == "__main__":
    run_bot()
