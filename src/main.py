"""Main entry point for the v6 crypto trading bot.

This module initializes all necessary components and orchestrates the trading
cycle for each configured asset.

Typical usage:
    python3 main.py

Expects API keys to be set as environment variables as specified in config.py.
"""

import sys
import time

# Local application imports
from trading import (
    coinbase_client,
    config,
    order_calculator,
    signal_analyzer,
    technical_analysis,
)
from trading.logger import LoggerDirectoryError, get_logger, setup_logging
from trading.persistence import PersistenceManager
from trading.trade_manager import TradeManager


def run_bot() -> None:
    """Main entry point for the trading bot.

    Initializes all components, iterates through configured trading pairs,
    and executes the trading logic for each asset.

    Includes comprehensive error handling and logging.
    """
    try:
        setup_logging(
            level=config.LOG_LEVEL,
            log_file=config.LOG_FILE,
            persistence_dir=config.PERSISTENCE_DIR,
        )
        logger = get_logger()
    except (LoggerDirectoryError, ValueError) as e:
        print(f"CRITICAL: Logger initialization failed: {e}", file=sys.stderr)
        sys.exit(1)

    logger.info("--- Starting v6 crypto trading bot run ---")
    start_time = time.time()

    try:
        # Assert that the configuration is valid before proceeding.
        assert config.TRADING_PAIRS, "Configuration error: TRADING_PAIRS is empty."

        client = coinbase_client.CoinbaseClient()
        persistence_manager = PersistenceManager(logger=logger)
        trade_manager = TradeManager(
            client=client,
            persistence_manager=persistence_manager,
            ta_module=technical_analysis,
            config_module=config,
            logger=logger,
            signal_analyzer=signal_analyzer,
            order_calculator=order_calculator,
        )

        logger.info(f"Processing {len(config.TRADING_PAIRS)} configured trading pairs.")
        for asset_id in config.TRADING_PAIRS:
            logger.info(f"--- Starting trade cycle for {asset_id} ---")
            try:
                trade_manager.process_asset_trade_cycle(asset_id=asset_id)
            except Exception as e:
                logger.error(
                    f"An unexpected error occurred while processing {asset_id}: {e}",
                    exc_info=True,
                )
            finally:
                logger.info(f"--- Completed trade cycle for {asset_id} ---")

    except (AssertionError, RuntimeError) as e:
        logger.critical(f"A critical error halted the bot: {e}", exc_info=True)
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
