# Plan for Crypto Trading Bot v6

This document outlines the plan for developing version 6 of the crypto trading bot, building upon lessons learned from v5 and the original GDAX_Trader.R script.

## I. Core Design Philosophy

1.  **Modularity:** Break down the bot into logical, independent components to improve manageability and testability.
2.  **Clarity:** Ensure code within each component is clear, well-commented, and accurately reflects the intended trading strategy.
3.  **Configuration-Driven:** Utilize clear, centralized configuration for all parameters, product details, and strategy settings.
4.  **Robustness:** Implement solid error handling, appropriate retry mechanisms for API calls, and comprehensive logging.
5.  **Testability:** Design components with unit testing in mind from the outset to facilitate a reliable testing suite.

## II. Agreed Design Decisions (Summary from v5 Analysis & Inspiration)

Based on the review of the inspiration article, R-bot, previous v5 Python bot, and user feedback, the following design decisions have been made for the new v6 bot:

1.  **Core Strategy:** Align with the R-bot's RSI-based buy signal and 3-tier profit-taking sell strategy.
    *   **Buy Signal:** Current 14-period RSI (15-min candles) > 30, previous RSI <= 30, and one of 3 prior RSIs < 30.
    *   **Sell Strategy:** Upon successful buy, place 3 limit sell orders (e.g., 1/3 at 1% profit, 1/2 of remainder at 4%, rest at 7%).
2.  **Currency Focus:** BTC-USD, ETH-USD, LTC-USD.
3.  **Buy Order Execution:** Place a limit buy order. If not filled by the next bot run, the logic will reassess. No rapid retry loop.
4.  **Position State Persistence:** Upon a successful buy, save the execution price to a simple text file per asset (e.g., `ETH_buy_price.txt`). This file will be used to calculate sell tiers.
5.  **Initial Buy Amount:** Use a configurable fixed USD amount per trade, per asset.
6.  **Execution Model:** The bot will be designed as a script that runs, executes one full pass of logic for all configured assets, and then exits. It's intended to be scheduled externally (e.g., via cron).
7.  **Modularity:** Code will be broken down into specific modules for configuration, API client interaction, technical analysis, trading logic, persistence, and logging.
8.  **Adherence to Rules:** Strict adherence to NASA Power of 10, global coding standards, and use of development tools (mypy, black, flake8, bandit, pytest).

## III. Proposed Directory Structure & File Purposes

The new bot will reside in `/home/gman/workspace/Crypto-Bots/Active/Single-File/v6/` with the following structure:

```
/home/gman/workspace/Crypto-Bots/Active/Single-File/v6/
├── main.py                 # Main entry point, orchestrates bot execution cycle.
├── config.py               # Holds all static configurations (trading pairs, RSI settings, file paths, etc.) and loads API keys from environment variables.
├── coinbase_client.py      # Thin wrapper for all Coinbase API interactions (getting data, placing orders).
├── technical_analysis.py   # Functions for calculating technical indicators (e.g., RSI).
├── trading_logic.py        # Core decision-making: should_buy, determine_sell_orders, manage trade cycle per asset.
├── persistence.py          # Simple functions to save/load the initial buy price for an asset.
├── logger.py               # Basic logging setup and utility functions.
├── requirements.txt        # Python package dependencies.
├── .gitignore              # Specifies intentionally untracked files that Git should ignore.
└── v6_plan.md              # This planning document.
```

### File Purposes:

*   **`main.py`**: Orchestrates the bot's lifecycle. Initializes components, iterates through configured trading pairs, and calls functions from `trading_logic.py`.
*   **`config.py`**: Centralized configuration. Includes API key loading (from environment variables), definitions for trading pairs (BTC-USD, ETH-USD, LTC-USD) with their specific parameters (RSI settings, profit tiers, min trade sizes, candle granularity, buy price file names).
*   **`coinbase_client.py`**: Provides an abstraction layer over the `coinbase-advanced-py` library. Contains functions like `get_account_balance`, `get_product_candles`, `get_order_book`, `place_limit_order`, `cancel_order`, `get_open_orders`. Each function will handle API call specifics and basic error checking.
*   **`technical_analysis.py`**: Implements functions to calculate necessary technical indicators. The primary one will be `calculate_rsi` based on the logic derived from the R-bot (14-period, 15-min candles, specific entry conditions).
*   **`trading_logic.py`**: Contains the core intelligence. Functions like `should_buy_asset` (evaluates RSI conditions), `determine_sell_orders` (calculates tiered sell prices and sizes), and `process_asset_trade` (manages the buy/sell cycle for a single asset).
*   **`persistence.py`**: Handles the simple file I/O for storing and retrieving the buy price of an asset (e.g., `save_buy_price(asset_id, price)`, `load_buy_price(asset_id)`).
*   **`logger.py`**: Configures a simple logger (e.g., using Python's `logging` module) to output information about bot actions, decisions, and errors to the console and/or a log file.
*   **`requirements.txt`**: Lists all Python dependencies with their specific versions for reproducible environments.
*   **`.gitignore`**: Standard git ignore file, including `.env`, `*_buy_price.txt`, `__pycache__`, virtual environment folders, IDE files, and log files.
*   **`v6_plan.md`**: This document, outlining the project goals, analysis, design, and progress.

## IV. Implementation Plan & Progress

This section tracks the development progress of the Crypto Trading Bot v6.

**1. Overall Setup & Foundation:**
*   [X] Finalize and approve initial plan.
*   [X] Create `/home/gman/workspace/Crypto-Bots/Active/Single-File/v6/` directory structure.
*   [X] Develop `requirements.txt` and set up virtual environment.
*   [X] Implement `.gitignore`.
*   **[X] Static Analysis & Code Quality:**
    *   [X] `mypy`: All Python files successfully pass type checks.
    *   [X] `flake8`: All Python files conform to style and quality guidelines.
    *   [X] `bandit`: Security analysis performed.
        *   Findings in `coinbase_client.py` (B101 `assert_used`) reviewed and acknowledged as intentional.
        *   Findings in `tests/test_coinbase_client.py` (B108, B105, B106) addressed using `tempfile` and `#nosec` comments.
    *   [X] `pytest`: All 56 unit tests across the project are passing.

**2. Module: `logger.py`**
*   [X] Implement `logger.py` for console and file logging.
*   [X] Develop `tests/test_logger.py` with comprehensive unit tests.
*   [X] All tests passing.

**3. Module: `config.py`**
*   [X] Implement `config.py` for static configurations and API key loading from environment variables.
*   [X] Develop `tests/test_config.py` with unit tests.
*   [X] All tests passing.

**4. Module: `coinbase_client.py`**
*   [X] Implement `coinbase_client.py` as a thin wrapper for Coinbase Advanced Trade API interactions.
*   [X] Develop `tests/test_coinbase_client.py` with comprehensive unit tests covering:
    *   [X] Initialization (success and failure).
    *   [X] `_generate_client_order_id`.
    *   [X] `get_accounts` (success, empty response, API error, unexpected format).
    *   [X] `get_product_candles` (success, empty response, API error, invalid granularity, unexpected format).
    *   [X] `get_product_book` (success, API error, unexpected format).
    *   [X] `limit_order_buy` (success, API error, insufficient funds).
    *   [X] `limit_order_sell` (success, API error, insufficient funds).
    *   [X] `cancel_orders` (success, API error, no orders to cancel).
    *   [X] `get_product` (success, API error).
    *   [X] `get_order` (success, API error).
*   [X] All tests passing.

**5. Module: `technical_analysis.py`**
*   [X] **Implement `calculate_rsi(candles_df: pd.DataFrame, period: int = 14) -> Optional[pd.Series]`:**
    *   Handles empty or insufficient data.
    *   Correctly computes RSI using `ta` library.
*   [X] **Implement `calculate_sma(candles_df: pd.DataFrame, period: int = 20) -> Optional[pd.Series]`:**
    *   Handles empty or insufficient data.
    *   Correctly computes SMA using `ta` library.
*   [X] **Implement `add_rsi_to_dataframe(candles_df: pd.DataFrame, rsi_period: int = 14) -> pd.DataFrame`:**
    *   Adds 'rsi' column to the DataFrame.
    *   Handles cases where RSI cannot be calculated.
*   [X] Develop `tests/test_technical_analysis.py` with comprehensive unit tests covering:
    *   [X] `calculate_rsi` (valid data, empty data, insufficient data, data type checks).
    *   [X] `calculate_sma` (valid data, empty data, insufficient data, data type checks).
    *   [X] `add_rsi_to_dataframe` (valid data, RSI calculation success, RSI calculation failure).
*   [X] Improve test coverage for `technical_analysis.py` (Target: 100%, Achieved: 94% - generic exception handlers for RSI/SMA missed, deemed acceptable).
*   [X] All tests passing.

**6. Module: `persistence.py`**
*   Manages the state of trades (open buy orders, filled buy trades) using JSON files per asset (e.g., `BTC-USD_trade_state.json`).
*   [X] **Implement `save_trade_state(asset_id: str, state_data: Dict) -> None`:**
    *   [X] Saves the provided `state_data` dictionary to `[asset_id]_trade_state.json`.
*   [X] **Implement `load_trade_state(asset_id: str) -> Dict`:**
    *   [X] Loads trade state from `[asset_id]_trade_state.json`.
    *   [X] Returns an empty dictionary if the file doesn't exist or is invalid.
*   [X] **Implement helper functions built upon `save/load_trade_state`:**
    *   [X] `save_open_buy_order(asset_id: str, order_id: str, buy_params: Dict)`
    *   [X] `load_open_buy_order(asset_id: str) -> Optional[Dict]` (returns dict with order_id and params)
    *   [X] `clear_open_buy_order(asset_id: str)`
    *   [X] `save_filled_buy_trade(asset_id: str, trade_details: Dict)` (e.g., price, quantity, timestamp, associated sell order IDs)
    *   [X] `load_filled_buy_trade(asset_id: str) -> Optional[Dict]`
    *   [X] `clear_filled_buy_trade(asset_id: str)`
    *   [X] `add_sell_order_to_filled_trade(asset_id: str, sell_order_id: str)`
    *   [X] `update_sell_order_status_in_filled_trade(asset_id: str, sell_order_id: str, status: str)`
*   [X] **Develop `tests/test_persistence.py`:**
    *   [X] Mock file system operations (`open`, `os.path.exists`, `os.remove`, `json.dump`, `json.load`).
    *   [X] Test all save, load, and clear operations for both open buy orders and filled buy trades.
    *   [X] Test scenarios: file exists, file doesn't exist, corrupted file (if feasible to simulate).
    *   [X] All tests passing.

**7. Module: `trading_logic.py`**
*   [X] **Implement `should_buy_asset(rsi_series: Optional[pd.Series], config_asset_params: Dict) -> bool`:**
    *   [X] Conditions: Current 14-period RSI (15-min candles) > 30, Previous RSI <= 30, One of 3 prior RSIs < 30.
    *   [X] Input validation: `rsi_series` not None, length >= 5. `config_asset_params` has `buy_rsi_threshold` (numeric, 0-100).
    *   [X] Assertions for all validations.
    *   [X] **Develop tests in `tests/test_trading_logic.py`:**
        *   [X] Test cases for conditions met, not met (each condition failing), invalid inputs (None series, short series, missing/invalid config).
*   [X] **Implement `should_sell_asset(asset_id: str, current_price: float, coinbase_client: CoinbaseClient, persistence_manager: PersistenceManager, config_asset_params: Dict) -> Tuple[bool, Optional[str], Optional[Dict]]`:**
    *   [X] Retrieves filled buy trade details using `persistence_manager.load_filled_buy_trade(asset_id)`.
    *   [X] If no filled trade, returns `(False, None, None)`.
    *   [X] Calculates stop-loss and take-profit prices based on `buy_price` from trade details and `stop_loss_percentage`, `take_profit_percentage` from `config_asset_params`.
    *   [X] Returns `(True, "stop_loss", trade_details)` if `current_price <= stop_loss_price`.
    *   [X] Returns `(True, "take_profit", trade_details)` if `current_price >= take_profit_price`.
    *   [X] Otherwise, returns `(False, None, None)`.
    *   [X] Input validation and assertions (asset_id, current_price, config params, trade details content).
    *   [X] **Develop tests in `tests/test_trading_logic.py`:**
        *   [X] Test cases: no filled trade, stop-loss triggered, take-profit triggered, neither triggered, invalid inputs/config, missing buy_price in trade details.
        *   [X] Use `math.isclose` for float comparisons.
*   [X] **Implement `determine_sell_orders_params(buy_price: float, buy_quantity: float, product_details: Dict, config_asset_params: Dict) -> List[Dict]`:**
    *   Calculates 3-tier sell prices and quantities based on `config_asset_params` profit tiers.
    *   Adjusts quantities to meet `product_details` (base_increment, quote_increment, min_order_size).
    *   Returns a list of dictionaries, each with `price` and `size` for a limit sell order.
*   [X] **Implement `process_asset_trade_cycle(asset_id: str, client: CoinbaseClient, ta_module, persistence_module, config_module, logger_instance)`:**
    *   **Load State:** Use `persistence_module` to load `open_buy_order` and `filled_buy_trade`.
    *   **Handle Filled Buy Trade (Sell Logic):**
        *   If a `filled_buy_trade` exists:
            *   Check status of its associated sell orders using `client.get_order`. Update status in persistence.
            *   If no sell orders were placed yet (or all failed/cancelled):
                *   Fetch `product_details` using `client.get_product`.
                *   Call `determine_sell_orders_params`.
                *   Place sell orders using `client.limit_order_sell`. Store their IDs in persistence.
            *   If all sell orders are filled, `clear_filled_buy_trade` and log completion.
    *   **Handle Open Buy Order (Buy Order Management):**
        *   Else if an `open_buy_order` exists:
            *   Check its status using `client.get_order(order_id)`.
            *   If filled: `clear_open_buy_order`, `save_filled_buy_trade` (with actual fill details: price, quantity, timestamp). Log buy success. Then, immediately attempt to place sell orders (as above).
            *   If still open: Log and wait for the next run.
            *   If cancelled/failed: `clear_open_buy_order`. Log failure.
    *   **Handle No Active Trade/Order (Buy Signal Check):**
        *   Else (no filled trade and no open buy order):
            *   Fetch candles using `client.get_product_candles`. Convert to DataFrame.
            *   Calculate RSI using `ta_module.calculate_rsi`.
            *   Fetch `product_details` using `client.get_product`.
            *   If `should_buy_asset` is true:
                *   (Potentially check account balance for quote currency via `client.get_accounts`).
                *   Calculate buy order size based on `config_asset_params.buy_amount_usd` and current market price (e.g., from `client.get_product_book` or last candle close). Adjust for `base_increment`.
                *   Place limit buy order using `client.limit_order_buy`.
                *   If order placement successful, `save_open_buy_order` to persistence.
*   [X] **Develop `tests/test_trading_logic.py` (including `tests/test_trading_logic_process.py`):**
    *   [X] Mock all dependencies (`CoinbaseClient`, `technical_analysis`, `persistence`, `config`).
    *   [X] Test `should_buy_asset` with various RSI series.
    *   [X] Test `determine_sell_orders_params` for correct price/quantity calculations and adjustments.
    *   [X] Test `process_asset_trade_cycle` through various scenarios (covered in `test_trading_logic_process.py`):
        *   [X] No existing trade -> buy signal -> buy order placed.
        *   [X] Open buy order -> filled -> sell orders placed.
        *   [X] Open buy order -> still open.
        *   [X] Filled buy trade -> sell orders placed.
        *   [X] Filled buy trade -> one sell order filled.
        *   [X] Filled buy trade -> all sell orders filled.

**8. Module: `main.py`**
*   [X] **Implement `run_bot()` function:**
    *   Initializes `CoinbaseClient`, logger, and loads configuration from `config.py`.
    *   Iterates through `TRADING_PAIRS` defined in `config.py`.
    *   For each `asset_id` and its `asset_config`:
        *   Calls `trading_logic.process_asset_trade_cycle`.
    *   Includes top-level try-except block for graceful error handling and logging.
*   [X] **Implement `if __name__ == "__main__":` block to call `run_bot()`.**
*   [X] **Develop `tests/test_main.py`:**
    *   Mock `trading_logic.process_asset_trade_cycle` and other initializations.
    *   Test that `process_asset_trade_cycle` is called for each configured asset.
    *   Test overall error handling if `run_bot` itself has complex logic.

**9. Final Review and Refinement**
*   [X] Review all code for adherence to NASA Power of 10 and other user-defined coding standards.
*   [X] Run all linters (`mypy`, `black`, `flake8`, `bandit`) and address all reported issues.
*   [X] Ensure all unit tests pass and aim for high test coverage.
*   [X] Update/create a comprehensive `README.md` for setup, configuration, and execution.
*   [X] Manually test the bot in a controlled environment if possible (e.g., with very small amounts or against a sandbox if available, though Coinbase Advanced Trade sandbox is limited).

## V. Test Suite Refactoring & Technical Debt

This phase focuses on improving the quality, maintainability, and organization of the existing test suite.

*   [ ] **Review and Refactor Existing Tests:**
    *   Analyze all tests in `tests/` for clarity, efficiency, and adherence to best practices (e.g., DRY principle).
    *   Refactor complex or brittle tests to make them more robust and easier to understand.
*   [ ] **Consolidate Test Helpers and Fixtures:**
    *   Identify common setup logic, mock objects, and test data.
    *   Create shared `pytest` fixtures in `tests/conftest.py` to remove duplication.
    *   Develop helper functions for generating common test data (e.g., mock API responses).
*   [ ] **Improve Mocking Strategies:**
    *   Ensure mocks are narrowly scoped and specific to the unit under test.
    *   Replace broad `unittest.mock.patch` calls with more targeted fixtures where appropriate.
    *   Verify that mocks accurately represent the behavior of the real components.
*   [ ] **Enhance Test Coverage and Scenarios:**
    *   Identify any gaps in test coverage for critical logic paths.
    *   Add tests for edge cases, error conditions, and invalid inputs that may have been missed.
*   [ ] **Standardize Test Structure:**
    *   Ensure a consistent structure across all test files for better readability.
    *   Organize tests logically within classes or modules.
