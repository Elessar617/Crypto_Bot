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
├── trading/
│   ├── __init__.py
│   ├── coinbase_client.py
│   ├── config.py
│   ├── logger.py
│   ├── order_calculator.py
│   ├── persistence.py
│   ├── signal_analyzer.py
│   ├── technical_analysis.py
│   └── trade_manager.py
├── tests/
│   ├── ...
├── pyproject.toml
├── requirements.txt
├── .gitignore
└── v6_plan.md
```

## IV. Historical Progress Log (Completed Development)

This section tracks the initial development progress of the Crypto Trading Bot v6.

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

---

## V. Post-Development Maintenance & Testing

This section outlines ongoing efforts to improve the project's structure, stability, and test coverage after the initial development phase.

### 1. Mutation Testing (`trading/coinbase_client.py`)

- **Objective:** Systematically kill all surviving mutants in the `trading/coinbase_client.py` module to ensure maximum test coverage and code robustness.
- **Status:** **COMPLETED**
- **Outcome:** 100% mutation coverage achieved. All 163 mutants were successfully killed by adding a comprehensive suite of targeted unit tests. The test suite now stands at 159 passing tests.

### 2. Active Refactoring Plan

This section outlines the current, active refactoring effort to improve the project's structure and stability.

#### a. Current Structure Analysis

Your current project has code split between `trading/` (a package) and the root directory, with an extensive `tests/` suite. This structure leads to import confusion, frequent test breakages after refactor, and constant “fixing” without forward progress.

#### b. Main Problems Identified

- **Split Codebase:** Core logic is divided between the `trading/` package and the project root.
- **Import Hell:** Refactoring breaks imports, leading to endless `ModuleNotFoundError` issues.
- **Mixed Import Styles:** Using both absolute and relative imports causes failures when running as a script vs. as a package.
- **Testing and Static Checks Fail:** Tools like pytest and mypy expect a consistent package structure.

#### c. The Refactor Plan

##### Step 1: Consolidate All Code into One Package
- Move all `.py` files for your core logic into `trading/`.
- Leave only entry points (like `main.py`), configuration, and documentation in the project root.

##### Step 2: Fix All Imports
- Use **only absolute imports** within your code and tests.
  **Example:**
  `from trading.coinbase_client import CoinbaseClient`
- Never use relative imports (`from .foo import bar`).

##### Step 3: Run Everything From the Project Root
- To run the bot: `python -m trading.main`
- To run tests: `pytest`

##### Step 4: Maintain Consistency
- New modules go in `trading/`, not in the root.
- Entry point (`main.py`) just launches the bot, all business logic stays in the package.
- Fix imports **everywhere** as you move modules.

##### Step 5: Version Control Your Changes
- Use git for every structural change.
- Commit small, logical steps so you can always revert if something breaks.

---

## VI. Post-Development Refinements & Testing

This section tracks improvements and testing conducted after the initial v6 development was completed.

*   **[X] Refactor `tests/test_persistence.py`:**
    *   Updated all tests to use the `PersistenceManager` class instead of legacy procedural functions.
    *   Corrected all mock patch targets to point to `PersistenceManager` methods.
    *   Fixed all method signatures in tests to match the class-based API, resolving `TypeError` exceptions.
    *   Added a `persistence_dir` argument to `PersistenceManager.__init__` to allow for isolated test execution.
    *   Corrected validation logic in `load_open_buy_order` and `update_sell_order_status_in_filled_trade` to ensure tests pass.
    *   Verified the entire test suite passes.

---

## VI. Post-Refactoring Cleanup and Verification

This section tracks the final steps to ensure the codebase is stable, clean, and fully verified after the major refactoring effort.

*   **[X] Fix All Failing Tests:** Addressed all test failures in `tests/test_coinbase_client.py` and `tests/test_main.py`. All 131 tests are now passing.
*   **[X] Run Static Analysis:** Performed and fixed all issues reported by `mypy`, `flake8`, and `bandit`.
*   **[X] Persistence Layer Refactor:** Completed a major refactoring of the persistence layer.
    *   Replaced the procedural `persistence.py` with a class-based `PersistenceManager`.
    *   Updated `TradeManager` to use the new `PersistenceManager` instance.
    *   Refactored the test suite in `tests/test_trade_manager.py` to mock the `PersistenceManager` class and align with the new architecture.
    *   Resolved all related test failures, ensuring the system is stable.
*   **[X] Smoke Test:** Successfully ran the bot in a live environment, fetching market data and executing the full trade cycle without runtime errors.

### 4. Summary Checklist & Progress

- **Step 1: Consolidate Code:** [X] All logic moved to `trading/`.
- **Step 2: Update Imports:** [X] All application and test imports updated to be absolute (`from trading...`).
- **Step 3: Commit Changes:** [X] Commit the refactoring work to version control.
- **Step 4: Run Bot (Smoke Test):** [X] Run the bot and validate it runs successfully in the live environment, fixing all runtime errors.
- **Step 5: Resolve Test Setup:** [X] Add `pyproject.toml` and install in editable mode to resolve `ModuleNotFoundError` during test collection.
- **Step 6: Final Verification:** [X] Run the full `pytest` suite and all static analysis tools (`mypy`, `flake8`, `bandit`) to confirm the codebase is stable and clean.

---

## VII. Future Roadmap & Advanced Testing

This section outlines potential future work, including advanced testing strategies and new features.

### 1. Advanced Testing Strategy

This phase moves beyond simple line coverage to a more sophisticated, risk-based approach. The goal is not just to test more, but to test smarter, focusing effort where it provides the most value and confidence.

#### Strategic Code Coverage
Instead of a uniform coverage target, we will apply a tiered approach based on module criticality.

*   **Tier 1: Critical Modules (>95% Coverage + Mutation Testing)**
    *   *Modules:* `coinbase_client.py`, `persistence.py`, `trading/` (all modules)
*   **Tier 2: High Importance (>85% Coverage)**
    *   *Modules:* `technical_analysis.py`, `main.py`
*   **Tier 3: Utility & Supporting (<85% Coverage Acceptable)**
    *   *Modules:* `config.py`, `logger.py`

#### Mutation Testing
To measure the *quality* and *effectiveness* of our tests, not just their quantity, we will introduce mutation testing.

*   **Goal:** Ensure that our test suite can detect small, intentionally introduced bugs (mutations).
*   **Tool:** We will use `mutmut` for Python.
*   **Next Steps:**
    *   [ ] **(CURRENT STEP)** Resume Mutation Testing: Restart `mutmut` on the refactored `coinbase_client.py` to get a new baseline score.
    *   [ ] Analyze surviving mutants and write targeted tests.
    *   [ ] Continue iterating until mutation score is satisfactory for Tier 1 modules.

### 2. Test Suite Refactoring
*   [ ] **Consolidate Test Helpers and Fixtures:**
    *   Identify common setup logic, mock objects, and test data.
    *   Create shared `pytest` fixtures in `tests/conftest.py` to remove duplication.
*   [ ] **Refactor for Testability:**
    *   Refactor modules like `logger.py` to make their configuration explicit and repeatable, simplifying tests.

### 3. New Features & Enhancements
*   [ ] Enhance the bot with new strategies or indicators.
*   [ ] Pursue performance optimizations or other code improvements.
*   [ ] Prepare the bot for a live production environment with robust deployment scripts.

### 4. Final Code Review

*   [ ] **Final Code Review:** After all advanced testing (including mutation testing) is complete, conduct a final review of the entire codebase for clarity, consistency, and adherence to design principles.