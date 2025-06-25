# Plan for Crypto Trading Bot v6

This document outlines the plan for developing version 6 of the crypto trading bot, building upon lessons learned from v5 and the original GDAX_Trader.R script.

## I. Core Design Philosophy

1.  **Modularity:** Break down the bot into logical, independent components to improve manageability and testability.
2.  **Clarity:** Ensure code within each component is clear, well-commented, and accurately reflects the intended trading strategy.
3.  **Configuration-Driven:** Utilize clear, centralized configuration for all parameters, product details, and strategy settings.
4.  **Robustness:** Implement solid error handling, appropriate retry mechanisms for API calls, and comprehensive logging.
5.  **Testability:** Design components with unit testing in mind from the outset to facilitate a reliable testing suite.

## II. Agreed Design Decisions

Based on the review of the inspiration article, R-bot, previous v5 Python bot, and user feedback, the following design decisions have been made for the new v6 bot:

1.  **Core Strategy:** Align with the R-bot's RSI-based buy signal and 3-tier profit-taking sell strategy.
2.  **Execution Model:** The bot is a script that runs one full pass of logic for all configured assets and then exits. It's intended to be scheduled externally (e.g., via cron).
3.  **Modularity:** Code is broken down into specific modules for configuration, API client interaction, technical analysis, trading logic, persistence, and logging.
4.  **Adherence to Rules:** Strict adherence to NASA Power of 10, global coding standards, and use of development tools (mypy, black, flake8, bandit, pytest).

## III. Final Directory Structure

```
/home/gman/workspace/Crypto-Bots/Active/Single-File/v6/
├── main.py
├── config.py
├── coinbase_client.py
├── technical_analysis.py
├── trading/
│   ├── __init__.py
│   ├── trade_manager.py
│   ├── signal_analyzer.py
│   └── order_calculator.py
├── persistence.py
├── logger.py
├── requirements.txt
├── .gitignore
├── v6_plan.md
└── tests/
    ├── __init__.py
    ├── test_main.py
    ├── test_config.py
    ├── test_coinbase_client.py
    ├── test_technical_analysis.py
    ├── test_trade_manager.py
    ├── test_signal_analyzer.py
    ├── test_order_calculator.py
    └── test_persistence.py
```

## IV. Implementation and Progress

This section tracks the development progress of the Crypto Trading Bot v6.

*   **[X] Overall Setup & Foundation:**
    *   [X] Finalize and approve initial plan.
    *   [X] Create directory structure.
    *   [X] Develop `requirements.txt` and set up virtual environment.
    *   [X] Implement `.gitignore`.
*   **[X] Static Analysis & Code Quality:**
    *   [X] `mypy`: All Python files successfully pass type checks.
    *   [X] `flake8`: All Python files conform to style and quality guidelines.
    *   [X] `bandit`: Security analysis performed and findings addressed.
    *   [X] `pytest`: All 138 unit tests across the project are passing.
*   **[X] Module: `logger.py`**
    *   [X] Implemented and tested.
*   **[X] Module: `config.py`**
    *   [X] Implemented and tested.
*   **[X] Module: `coinbase_client.py`**
    *   [X] Implemented as a thin wrapper for Coinbase Advanced Trade API.
    *   [X] Comprehensively tested with mocks.
*   **[X] Module: `technical_analysis.py`**
    *   [X] Implemented RSI and SMA calculations.
    *   [X] Comprehensively tested.
*   **[X] Module: `persistence.py`**
    *   [X] Implemented JSON-based state persistence.
    *   [X] Comprehensively tested with file system mocks.
*   **[X] Package: `trading/`**
    *   **[X] `trading/signal_analyzer.py`:**
        *   [X] Implemented `should_buy_asset` with core RSI logic.
        *   [X] Fully tested.
    *   **[X] `trading/order_calculator.py`:**
        *   [X] Implemented `calculate_buy_order_details` and `determine_sell_orders_params`.
        *   [X] Logic includes adjustments for product-specific increments.
        *   [X] Fully tested.
    *   **[X] `trading/trade_manager.py`:**
        *   [X] Implemented `TradeManager` class to orchestrate the trade cycle.
        *   [X] Handles all core logic: checking for open orders, evaluating new buy signals, and placing sell orders.
        *   [X] Fully tested after extensive debugging of mock interactions and data validation.
*   **[X] Module: `main.py`**
    *   [X] Implemented `run_bot()` to orchestrate the full cycle for all configured assets.
    *   [X] Fully tested.
*   **[X] Final Review and Refinement**
    *   [X] Reviewed all code for adherence to NASA Power of 10 and other user-defined coding standards.

## V. Project Status & Next Steps

*   **Status:** **COMPLETE.** All modules are implemented and unit tested. The test suite is stable with 138 passing tests. The core logic is considered validated and robust.
*   **Next Steps:** The project is ready for the next phase. Choose one of the following:
    1.  **Implement New Features:** Enhance the bot with new strategies or indicators.
    2.  **Further Refactoring:** Pursue performance optimizations or other code improvements.
    3.  **Deployment:** Prepare the bot for a live production environment.
*   [X] Run all linters (`mypy`, `black`, `flake8`, `bandit`) and address all reported issues.
*   [X] Ensure all unit tests pass and aim for high test coverage.
*   [X] Update/create a comprehensive `README.md` for setup, configuration, and execution.
*   [X] Manually test the bot in a controlled environment if possible (e.g., with very small amounts or against a sandbox if available, though Coinbase Advanced Trade sandbox is limited).

## V. Test Suite Refactoring & Stability (Completed)

This phase focused on improving the quality, maintainability, and organization of the existing test suite.

*   [X] **Review and Refactor Existing Tests:**
    *   Analyzed all tests in `tests/` for clarity, efficiency, and adherence to best practices.
    *   Refactored brittle tests to make them more robust, particularly by fixing mock strategies and aligning assertions.
*   [X] **Improve Mocking Strategies:**
    *   Ensured mocks are narrowly scoped and specific to the unit under test.
    *   Stabilized integration tests by mocking external API calls, making the test suite independent of sandbox availability.
*   [ ] **Consolidate Test Helpers and Fixtures:**
    *   Identify common setup logic, mock objects, and test data.
    *   Create shared `pytest` fixtures in `tests/conftest.py` to remove duplication.
    *   Develop helper functions for generating common test data (e.g., mock API responses).
*   [ ] **Standardize Test Structure:**
    *   Ensure a consistent structure across all test files for better readability.
    *   Organize tests logically within classes or modules.

## VI. Advanced Testing Strategy

This phase moves beyond simple line coverage to a more sophisticated, risk-based approach. The goal is not just to test more, but to test smarter, focusing effort where it provides the most value and confidence.

### 1. Strategic Code Coverage

Instead of a uniform coverage target, we will apply a tiered approach based on module criticality.

*   **Tier 1: Critical Modules (>95% Coverage + Mutation Testing)**
    *   *Definition:* Modules where a bug could lead to direct financial loss, data corruption, or major malfunction.
    *   *Modules:*
        *   `coinbase_client.py`
        *   `persistence.py`
        *   `trading/` (all modules within)
*   **Tier 2: High Importance (>85% Coverage)**
    *   *Definition:* Modules supporting core functionality where bugs could lead to flawed analysis or poor decisions.
    *   *Modules:*
        *   `technical_analysis.py`
        *   `main.py`
*   **Tier 3: Utility & Supporting (<85% Coverage Acceptable)**
    *   *Definition:* Modules that provide supporting functionality. The focus here is on testability and clarity over raw coverage percentage.
    *   *Modules:*
        *   `config.py`
        *   `logger.py`

### 2. Mutation Testing

To measure the *quality* and *effectiveness* of our tests, not just their quantity, we will introduce mutation testing.

*   **Goal:** Ensure that our test suite can detect small, intentionally introduced bugs (mutations). A "surviving" mutant indicates a weakness in our tests that must be fixed.
*   **Tool:** We will use `mutmut` for Python.
*   **Mutation Testing Progress:**
    *   **Status:** Iteratively analyzing and killing surviving mutants in `coinbase_client.py`.
    *   **Score:** 241/342 killed (70.5%) | 101 survived (29.5%)
    *   **Task List:**
        *   [x] Update test strategy in `v6_plan.md` to risk-based approach.
        *   [x] Add `mutmut` to `requirements.txt` and install.
        *   [x] Refactor `logger.py` for explicit, testable configuration.
        *   [x] Redesign and fix `logger.py` tests for reliability.
        *   [x] Run `mutmut` on `coinbase_client.py` and record baseline.
        *   [x] **`get_product_candles`:** Added tests for direct list response, invalid input, and HTTPError handling.
        *   [x] **`limit_order` methods:** Added tests for invalid, zero, and small price boundaries.
        *   [x] **`limit_order` methods:** Fixed bug in nested error message logging and updated tests.
        *   [x] **`get_product_book`:** Added comprehensive tests for input validation, malformed data, and exception handling. Fixed assertion propagation bug.
        *   [x] **`get_accounts`:** Added comprehensive tests for all response formats, data integrity, and malformed data. Fixed assertion propagation bug.
        *   [x] **`get_product`:** Added comprehensive tests for all response formats, data integrity, and exception handling. Fixed assertion propagation bug.
        *   [ ] **Next Target: `cancel_orders`:** Analyze surviving mutants and write targeted tests.
        *   [ ] Continue iterating until mutation score is satisfactory for Tier 1.

### 3. Refactoring for Testability

Low code coverage is often a symptom of code that is difficult to test. Instead of writing complex tests to force coverage, we will prioritize refactoring the code itself to be more testable.

*   **Case Study: `logger.py`**
    *   **Problem:** The logger module has proven difficult to test due to its reliance on module-level state and complex import-time logic. This has led to persistent, flaky test failures.
    *   **Solution:**
        *   [ ] Refactor `logger.py` to make its configuration explicit and repeatable, likely via a `setup_logging()` function.
        *   [ ] This will simplify the tests, eliminate the need for complex `sys.modules` manipulation, and resolve the outstanding test failures as a direct result of improved design.
