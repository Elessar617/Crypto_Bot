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
    ├── src/
    │   ├── main.py
    │   └── trading/          # Core application package
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

#### c. `trading/persistence.py`
- **Status:** **COMPLETED**
- **Outcome:** All surviving mutants have been killed, achieving 100% mutation test coverage. All mutation-specific tests have been merged into the main test file, and the temporary test file has been deleted.
  - **Killed Mutants:** Added new tests to target surviving mutants, including tests for input validation, exception logging, and content validation for saved filled buy trades.

#### d. `trading/order_calculator.py`
- **Status:** **COMPLETED**
- **Outcome:** Completed a full technical debt cleanup.
  - **Static Analysis:** Ran `mypy`, `black`, `flake8`, and `bandit` to identify and fix all style, type, and security issues.
  - **Refactoring:** Removed duplicate test methods, unused imports, and resolved all line-length violations to improve code quality and maintainability.
  - **Verification:** Confirmed no regressions were introduced by running the full `pytest` suite. All 299 tests pass.
  - **Mutation Testing:** All mutants have been killed, achieving 100% mutation test coverage.

#### e. `trading/signal_analyzer.py`
- **Status:** **COMPLETED**
- **Outcome:** Achieved 100% effective mutation coverage. All non-equivalent, testable mutants were killed by adding new, targeted tests for boundary conditions. Remaining survivors were analyzed and confirmed to be either equivalent (e.g., changes to assertion messages) or untestable due to the project's dual-validation design. All static analysis checks (`black`, `flake8`, `mypy`, `bandit`) passed successfully after the changes.

#### f. `trading/technical_analysis.py`
- **Status:** **COMPLETED**
- **Outcome:** All testable, non-equivalent mutants have been killed. The remaining survivors are deemed untestable or equivalent due to the dual-validation design or changes to unreachable defensive code/logging statements.

### 2. Code Cleanup & Final Verification
- **Status:** **COMPLETED**
- **Summary:** All modules have undergone extensive mutation testing and static analysis. The codebase is now considered stable and fully verified against current testing standards. All subsequent work will focus on the Future Roadmap items.
- **Final Verification Activities:**
  - **`trading/technical_analysis.py`:** Completed full mutation testing and passed all static analysis checks (`black`, `flake8`, `mypy`, `bandit`) after adding new tests to kill all testable mutants.
  - **`trading/signal_analyzer.py`:** Completed full mutation testing and passed all static analysis checks.
  - **General:** Resolved all `flake8` line-length errors and configured `bandit` to ignore `B101` (assert_used) to align with project standards.
  - **Logging:** Added an `INFO` level log for the raw API response in `get_public_candles` and removed a stray `print` statement to improve debugging visibility.

---

## III. Current Tasks & Future Roadmap

This section outlines the immediate next steps and high-level goals for future development.

### 1. Current Tasks

*   [X] **Project Structure Refactoring:** Refactored the project into a standard `src` layout for better organization and packaging.
    *   [X] Created a `src` directory.
    *   [X] Moved the `trading` package and `main.py` into `src`.
    *   [X] Updated `pyproject.toml` to support the `src` layout.
    *   [ ] Update all imports to be relative to the new `src` layout.
*   [ ] **Re-implement Retry Logic:** Re-implement the API call retry logic in `coinbase_client.py` with an exponential backoff strategy and ensure all tests pass.

### 2. Future Roadmap

*   [X] **Test Suite Refactoring:** Consolidated test helpers and fixtures into `tests/conftest.py` to reduce duplication.
*   [ ] **Final Code Review:** After the file structure refactoring is complete, conduct a final high-level review of the entire codebase.
*   [ ] **New Features & Enhancements:** Enhance the bot with new strategies, indicators, or performance optimizations.

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

### 3. Final Stabilization and Regression Fixes
*   **[X] Final Static Analysis:** Completed a full round of `flake8` and `bandit` checks, fixing all remaining linting errors and security warnings related to temporary directory usage.
*   **[X] Regression Testing:** Identified and fixed several test regressions that appeared after major commits.
    *   Resolved `TypeError` in `tests/test_main.py` related to `pytest` fixtures in `unittest` classes by switching to the `tempfile` module.
    *   Fixed `AttributeError` in `tests/test_persistence.py` by correcting fixture usage in test method signatures.
    *   Corrected `AssertionError` in `test_run_bot_success` by fixing mock argument order and assertions.
*   **[X] Codebase Stability:** Confirmed the codebase is stable, with all 277 tests passing and all static analysis tools running clean.