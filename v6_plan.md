# Plan for Crypto Trading Bot v6

This document outlines the development, maintenance, and testing plan for version 6 of the crypto trading bot.

## I. Core Design & Structure

1.  **Core Strategy:** RSI-based buy signal with a 3-tier profit-taking sell strategy.
2.  **Execution Model:** A single-pass script, intended for external scheduling (e.g., cron).
3.  **Modularity:** Code is organized into distinct modules for clarity and testability.
4.  **Adherence to Rules:** Strict adherence to NASA Power of 10, global coding standards, and use of development tools (mypy, black, flake8, bandit, pytest).
5.  **Directory Structure:**
    ```
    /home/gman/workspace/Crypto-Bots/Active/Single-File/v6/
    ├── main.py
    ├── trading/              # Core application package
    ├── tests/                # Test suite
    ├── pyproject.toml
    ├── requirements.txt
    └── v6_plan.md
    ```

---

## II. Maintenance & Advanced Testing

This section outlines ongoing efforts to improve the project's structure, stability, and test coverage.

### 1. Mutation Testing

**Objective:** Achieve 100% mutation test coverage on all critical modules using `mutmut` to systematically find and kill surviving mutants.

**Run Command:** `mutmut run --paths-to-mutate trading/<module_name>.py`

#### a. `trading/coinbase_client.py`
- **Status:** **COMPLETED**
- **Outcome:** Achieved 100% mutation test coverage. All surviving and suspicious mutants were analyzed and killed by strengthening the test suite with new, targeted tests for edge cases.

#### b. `trading/trade_manager.py`
- **Status:** **COMPLETED**
- **Outcome:** All non-equivalent mutants have been killed.
  - **Killed Mutants:** Added new, focused tests to kill mutants related to local status updates (`#70`), `KeyError` handling in the order placement loop (`#87`, `#89`), and skipping orders with empty IDs (`#52`).
  - **Tooling Anomalies:** Investigated suspicious mutants (`#16`, `#87`, `#121`) and concluded they are `mutmut` tooling anomalies, not gaps in test coverage.
  - **Equivalent Mutants:** Analyzed survived mutants (`#63`, `#74`, `#77`) and confirmed they are equivalent, as they do not alter the program's logic.

#### c. Other Modules
- `[ ] PENDING`  `persistence.py`
- `[ ] PENDING`  `order_calculator.py`
- `[ ] PENDING`  `signal_analyzer.py`
- `[ ] PENDING`  `technical_analysis.py`

### 2. Code Cleanup & Logging Enhancements
- **Status:** **Ongoing**
- **Latest Changes:**
  - Added an `INFO` level log for the raw API response in `get_public_candles` to improve debugging visibility.
  - Removed a stray `print` statement from the error handling block in `get_public_candles`.

---

## III. Future Roadmap

This section outlines high-level goals for future development.

*   [ ] **Test Suite Refactoring:** Consolidate test helpers and fixtures into `tests/conftest.py` to reduce duplication.
*   [ ] **New Features & Enhancements:** Enhance the bot with new strategies, indicators, or performance optimizations.
*   [ ] **Final Code Review:** After all advanced testing is complete, conduct a final review of the entire codebase.

---

## Appendix: Completed Milestones

This section archives the historical progress of the project for reference.

### 1. Initial V6 Development
*   **[X] Overall Setup & Foundation**
*   **[X] Static Analysis & Code Quality**
*   **[X] Module: `logger.py`**
*   **[X] Module: `config.py`**
*   **[X] Module: `coinbase_client.py`**
*   **[X] Module: `technical_analysis.py`**
*   **[X] Module: `persistence.py`**
*   **[X] Package: `trading/`**
*   **[X] Module: `main.py`**
*   **[X] Final Review and Refinement**

### 2. Major Refactoring & Cleanup
*   **[X] Structural Refactoring:** Consolidated all core logic into the `trading/` package, standardized on absolute imports, and resolved all resulting test failures and `ModuleNotFoundError` issues.
*   **[X] Persistence Layer Refactor:** Replaced the procedural `persistence.py` with a class-based `PersistenceManager` and updated all dependent code and tests.
*   **[X] Re-implementation of Retry Logic:** Re-implemented the API call retry logic in `coinbase_client.py` with an exponential backoff strategy and ensured all tests pass.
*   **[X] Final Verification:** Ran the full `pytest` suite and all static analysis tools (`mypy`, `flake8`, `bandit`) to confirm the codebase is stable and clean after all refactoring.
*   **[X] Run main.py and verify runtime**