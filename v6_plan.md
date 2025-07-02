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

### 2. Project Cleanup
- **Status:** **COMPLETED**
- **Summary:** Performed a comprehensive cleanup of the project repository.
    *   Consolidated `ROADMAP.md` and `cdp_sdk_reference.md` into this plan.
    *   Deleted the original `ROADMAP.md` and `cdp_sdk_reference.md` files.
    *   Removed temporary and generated files, including `.coverage`, `.mutmut-cache`, `.report.json`, and all `__pycache__` directories.
    *   Reviewed and updated `.gitignore` to prevent generated files and sensitive data from being tracked.

### 3. Code Cleanup & Final Verification
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
    *   [X] Update all imports to be relative to the new `src` layout.

### 2. Future Roadmap

*   [X] **Test Suite Refactoring:** Consolidated test helpers and fixtures into `tests/conftest.py` to reduce duplication.
*   [ ] **Final Code Review:** After the file structure refactoring is complete, conduct a final high-level review of the entire codebase.
*   [ ] **New Features & Enhancements:** Enhance the bot with new strategies, indicators, or performance optimizations.

### 3. Detailed Future Roadmap

This section outlines potential future features and improvements for the trading bot, building upon the stable v6 foundation.

#### Phase 1: Enhanced Strategy & Risk Management

The immediate next steps should focus on making the trading strategy more robust and adding critical risk management features.

- **Implement Stop-Loss Orders:** After a successful buy, automatically place a stop-loss order at a configurable percentage below the buy price to limit potential losses.
- **Add More Technical Indicators:** Integrate additional indicators like MACD (Moving Average Convergence Divergence) and Bollinger Bands. This will allow for the creation of more sophisticated trading signals.
- **Dynamic Strategy Selection:** Refactor the trading logic to allow users to select from multiple predefined strategies in `config.py`. This would enable switching between an `RSI_Strategy` and a `MACD_Strategy` without code changes.
- **Trailing Stop-Loss:** For more advanced risk management, implement trailing stop-losses that automatically adjust upwards as the price increases, locking in profits.

#### Phase 2: Analytics & Performance Tracking

To properly evaluate the bot's effectiveness, we need better tools for tracking its performance.

- **Upgrade to Database Persistence:** Transition from flat text files to a more robust SQLite database. This would store a full history of all trades, orders, and bot activity, enabling complex queries and analysis.
- **Performance Analytics Module:** Create a new module (`analytics.py`) that can read from the database and calculate key performance indicators (KPIs):
  - Total Profit & Loss (P&L)
  - P&L per trading pair
  - Win/Loss Ratio
  - Sharpe Ratio
- **Generate Reports:** Add functionality to generate simple daily or weekly performance reports in text or HTML format.

#### Phase 3: Usability & Monitoring

Improve the user experience and provide better tools for real-time monitoring.

- **Notification Service:** Integrate with a service like Telegram, Discord, or email to send real-time alerts for:
  - Successful buy/sell orders
  - Critical errors or API failures
  - Daily performance summaries
- **Web Dashboard (Advanced):** For a more polished solution, develop a simple, read-only web dashboard using a lightweight framework like Flask or Dash. The dashboard could visualize:
  - Current open positions
  - Recent trade history
  - Live P&L
  - Bot status and logs

#### Phase 4: Advanced Capabilities

These are long-term goals that would significantly expand the bot's capabilities.

- **Backtesting Engine:** This is a crucial feature for any serious trading system. A backtester would allow for simulating trading strategies on historical market data to evaluate their effectiveness and optimize parameters before risking real capital.
- **Multi-Exchange Support:** Refactor the `coinbase_client.py` module to use a generic `ExchangeClient` abstract base class. This would allow for implementing clients for other exchanges (e.g., Binance, Kraken) that conform to the same interface, making the bot exchange-agnostic.
- **Machine Learning Integration:** As a research-oriented goal, explore the use of machine learning models to forecast price movements or identify optimal entry/exit points, potentially as an additional signal for the existing strategies.

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

---

## Appendix: Comprehensive CDP SDK Python Reference

## Table of Contents
1. [Installation and Configuration](#installation-and-configuration)
2. [Wallet Management](#wallet-management)
3. [Address Operations](#address-operations)
4. [Transfers](#transfers)
5. [Trades](#trades)
6. [Smart Contract Interactions](#smart-contract-interactions)
7. [Token Deployments](#token-deployments)
8. [Message Signing](#message-signing)
9. [Faucet Operations](#faucet-operations)
10. [Balance Operations](#balance-operations)
11. [Transaction Status](#transaction-status)

## Installation and Configuration

### Installation

Install the CDP SDK using pip.

```bash
pip install cdp-sdk
```

### Importing the SDK

Import all components from the CDP SDK.

```python
from cdp import *
```

### Configuring the SDK

Configure the SDK with your API key credentials.

```python
Cdp.configure(api_key_name: str, api_key_private_key: str) -> None
```

- `api_key_name`: Your API key name
- `api_key_private_key`: Your API key's private key

Example:
```python
api_key_name = "Your API key name"
api_key_private_key = "Your API key's private key"
Cdp.configure(api_key_name, api_key_private_key)
```

Alternatively, configure from a JSON file.

```python
Cdp.configure_from_json(json_file_path: str) -> None
```

- `json_file_path`: Path to the JSON file containing your API key

Example:
```python
Cdp.configure_from_json("~/Downloads/cdp_api_key.json")
```

## Wallet Management

### Creating a Wallet

Create a new wallet on the default network (Base Sepolia testnet).

```python
Wallet.create(network_id: str = "base-sepolia") -> Wallet
```

- `network_id`: Optional network identifier (default is "base-sepolia")

Example:
```python
wallet = Wallet.create()
```

Create a wallet on Base Mainnet.

```python
Wallet.create(network_id: str = "base-mainnet") -> Wallet
```

Example:
```python
mainnet_wallet = Wallet.create(network_id="base-mainnet")
```

### Accessing Wallet Addresses

Get the default address of a wallet.

```python
wallet.default_address -> Address
```

Example:
```python
address = wallet.default_address
```

Create an additional address in the wallet.

```python
wallet.create_address() -> Address
```

Example:
```python
new_address = wallet.create_address()
```

List all addresses in the wallet.

```python
wallet.addresses -> List[Address]
```

Example:
```python
all_addresses = wallet.addresses
```

### Exporting and Importing Wallets

Export wallet data for persistence.

```python
wallet.export_data() -> WalletData
```

Example:
```python
wallet_data = wallet.export_data()
```

Save wallet seed to a file (for development only).

```python
wallet.save_seed(file_path: str, encrypt: bool = False) -> None
```

- `file_path`: Path to save the seed file
- `encrypt`: Whether to encrypt the seed (default is False)

Example:
```python
wallet.save_seed("my_seed.json", encrypt=True)
```

Import a previously exported wallet.

```python
Wallet.import_data(wallet_data: WalletData) -> Wallet
```

- `wallet_data`: Previously exported WalletData object

Example:
```python
imported_wallet = Wallet.import_data(wallet_data)
```

Fetch a wallet by ID.

```python
Wallet.fetch(wallet_id: str) -> Wallet
```

- `wallet_id`: ID of the wallet to fetch

Example:
```python
fetched_wallet = Wallet.fetch(wallet_id)
```

Load a saved wallet seed.

```python
wallet.load_seed(file_path: str) -> None
```

- `file_path`: Path to the saved seed file

Example:
```python
fetched_wallet.load_seed("my_seed.json")
```

## Address Operations

### Creating External Addresses

Create an External Address object.

```python
ExternalAddress(network_id: str, address: str) -> ExternalAddress
```

- `network_id`: Network identifier
- `address`: Address string

Example:
```python
external_address = ExternalAddress("base-sepolia", "0x123456789abcdef...")
```

### Viewing Address IDs

Get the hexadecimal string representation of an address.

```python
address.address_id -> str
```

Example:
```python
address_id = address.address_id
```

### Listing Address Historical Balances

View historical balances of an asset for an address.

```python
address.historical_balances(asset_id: str) -> List[Dict]
```

- `asset_id`: Asset identifier (e.g., "eth", "usdc")

Example:
```python
historical_balances = address.historical_balances("usdc")
```

### Listing Address Transactions

View all transactions for a specific address.

```python
address.transactions() -> List[Transaction]
```

Example:
```python
transactions = address.transactions()
```

## Transfers

### Performing a Transfer

Transfer an asset from one wallet to another.

```python
wallet.transfer(amount: Union[int, float, Decimal], asset_id: str, destination: Union[str, Address, Wallet], gasless: bool = False) -> Transfer
```

- `amount`: Amount to transfer
- `asset_id`: Asset identifier (e.g., "eth", "usdc")
- `destination`: Recipient's address, wallet, or ENS/Basename
- `gasless`: Whether to perform a gasless transfer (only for USDC, EURC, cbBTC on Base Mainnet)

Example:
```python
transfer = wallet.transfer(0.00001, "eth", another_wallet)
transfer.wait()
```

### Gasless Transfer

Perform a gasless transfer of USDC on Base Mainnet.

```python
mainnet_wallet.transfer(amount: Union[int, float, Decimal], asset_id: str, destination: Union[str, Address, Wallet], gasless: bool = True) -> Transfer
```

Example:
```python
gasless_transfer = mainnet_wallet.transfer(0.000001, "usdc", another_wallet, gasless=True)
gasless_transfer.wait()
```

### Transfer to ENS or Basename

Transfer assets to an ENS or Basename address.

```python
wallet.transfer(amount: Union[int, float, Decimal], asset_id: str, destination: str) -> Transfer
```

Example:
```python
ens_transfer = wallet.transfer(0.00001, "eth", "my-ens-name.base.eth")
ens_transfer.wait()
```

## Trades

### Performing a Trade

Trade one asset for another on Base Mainnet.

```python
wallet.trade(amount: Union[int, float, Decimal], from_asset_id: str, to_asset_id: str) -> Trade
```

- `amount`: Amount of the source asset to trade
- `from_asset_id`: Source asset identifier
- `to_asset_id`: Destination asset identifier

Example:
```python
trade = mainnet_wallet.trade(0.00001, "eth", "usdc")
trade.wait()
```

### Trading Full Balance

Trade the full balance of one asset for another.

```python
wallet.trade(amount: Union[int, float, Decimal], from_asset_id: str, to_asset_id: str) -> Trade
```

Example:
```python
trade2 = mainnet_wallet.trade(mainnet_wallet.balance("usdc"), "usdc", "weth")
trade2.wait()
```

## Smart Contract Interactions

### Invoking a Contract

Invoke a smart contract method.

```python
wallet.invoke_contract(contract_address: str, method: str, args: Dict[str, Any], abi: Optional[List[Dict]] = None) -> Invocation
```

- `contract_address`: Address of the smart contract
- `method`: Name of the method to invoke
- `args`: Arguments for the method
- `abi`: Optional ABI if not using a standard interface (ERC-20, ERC-721, ERC-1155)

Example (ERC-721 NFT transfer):
```python
invocation = wallet.invoke_contract(
    contract_address="0xYourNFTContractAddress",
    method="transferFrom",
    args={"from": "0xFrom", "to": "0xmyEthereumAddress", "tokenId": "1000"}
).wait()
```

Example (Arbitrary contract):
```python
abi = [
    {
        "inputs": [
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "value", "type": "uint256"}
        ],
        "name": "transfer",
        "outputs": [{"internalType": "uint256", "name": '', "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

invocation = wallet.invoke_contract(
    contract_address="0xYourContract",
    abi=abi,
    method="transfer",
    args={"to": "0xRecipient", "value": "1000"}
).wait()
```

## Token Deployments

### Deploying ERC-20 Token

Deploy an ERC-20 token contract.

```python
wallet.deploy_token(name: str, symbol: str, initial_supply: int) -> DeployedContract
```

- `name`: Name of the token
- `symbol`: Symbol of the token
- `initial_supply`: Initial token supply

Example:
```python
deployed_contract = wallet.deploy_token("ExampleCoin", "EXAM", 100000)
deployed_contract.wait()
```