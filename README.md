# Crypto Trading Bot v6

## 1. Overview

This project is a sophisticated, event-driven cryptocurrency trading bot designed to execute trades on Coinbase based on a defined technical analysis strategy. It is built with a focus on modularity, testability, and robustness, adhering to professional software engineering standards, including the NASA Power of 10 Rules.

The bot operates by analyzing market data for specified trading pairs (e.g., ETH-USD), identifying trading opportunities based on the Relative Strength Index (RSI), and automatically executing buy and sell orders. Its design as a single-pass script makes it ideal for scheduled execution via tools like `cron`.

## 2. Core Features

- **Modular Architecture:** Code is logically separated into modules for API interaction, technical analysis, trading logic, configuration, persistence, and logging.
- **Configuration-Driven:** All trading parameters, API keys, and application settings are managed in a central `config.py` file.
- **RSI-Based Strategy:** Implements a proven trading strategy based on RSI indicators to identify oversold conditions for buying and tiered profit-taking for selling.
- **State Persistence:** The bot saves the state of open positions (i.e., the buy price) to the local filesystem, allowing it to manage sell orders across multiple runs.
- **Comprehensive Testing:** A full suite of unit tests written with `pytest` and `unittest.mock` ensures the reliability and correctness of each component.
- **Robust Logging:** A dedicated logging module provides detailed, configurable logging to both the console and log files for easy debugging and monitoring.
- **Adherence to Standards:** The codebase is compliant with `mypy` for type checking, `black` for formatting, `flake8` for linting, and `bandit` for security analysis.

## 3. Software Architecture

The bot is designed with a clean, decoupled architecture to enhance maintainability and scalability.

- `main.py`: The main entry point that orchestrates the bot's execution cycle.
- `config.py`: Centralized configuration for trading pairs, strategy parameters, and API credentials.
- `coinbase_client.py`: A dedicated client class that encapsulates all communication with the Coinbase Advanced Trade API.
- `technical_analysis.py`: Contains functions for calculating technical indicators like RSI.
- `trading_logic.py`: Implements the core decision-making logic for buying and selling.
- `persistence.py`: Manages reading and writing the bot's state to the filesystem.
- `logger.py`: Configures and provides a shared logger instance for the application.
- `tests/`: Contains all unit tests for the various modules.

## 4. Trading Strategy

The bot's strategy is designed to be cautious and systematic.

1.  **Buy Condition:** A buy signal is generated when the 14-period RSI on a 15-minute candle chart shows that an asset was recently oversold and is beginning to recover. Specifically:
    - The current RSI is >= 30.
    - The previous RSI was <= 30.
    - At least one of the three preceding RSI values was < 30.

2.  **Sell Condition:** After a successful buy order is filled, the bot immediately places three separate limit sell orders to take profit at tiered levels:
    - **Tier 1:** Sell 1/3 of the position at a 1% profit.
    - **Tier 2:** Sell 1/3 of the position at a 4% profit.
    - **Tier 3:** Sell the final 1/3 of the position at a 7% profit.

This strategy aims to capitalize on short-term momentum while securing gains systematically.

## 5. Installation and Setup

Follow these steps to set up and run the bot.

**Prerequisites:**
- Python 3.8+

**1. Clone the Repository:**
```bash
git clone <repository_url>
cd <repository_directory>
```

**2. Create a Virtual Environment:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**3. Install Dependencies:**
```bash
pip install -r requirements.txt
```

**4. Set Up Environment Variables:**
Create a `.env` file in the project root by copying the example file:
```bash
cp .env.example .env
```

Edit the `.env` file and add your Coinbase API Key and Secret:
```
API_KEY="your_coinbase_api_key"
API_SECRET="your_coinbase_api_secret"
```

## 6. Configuration

All trading parameters can be adjusted in `config.py`. Key settings include:

- `TRADING_PAIRS`: A list of products to trade (e.g., `['ETH-USD', 'BTC-USD']`).
- `QUOTE_CURRENCY_PER_TRADE`: The amount in the quote currency (e.g., USD) to use for each buy order.
- `RSI_PERIOD`, `RSI_OVERSOLD`: Parameters for the RSI calculation.
- `PROFIT_TIERS`: The percentage profit and position portion for the tiered sell orders.

## 7. How to Run the Bot

Once configured, you can run the bot with a single command:

```bash
python main.py
```

The bot will execute one full cycle: fetch data, check for signals, place orders, and then exit. For continuous operation, it should be scheduled to run at regular intervals (e.g., every 15 minutes) using a tool like `cron`.

**Example Cron Job:**

To run the bot every 15 minutes, add the following line to your crontab (`crontab -e`):

```
*/15 * * * * /path/to/your/project/.venv/bin/python /path/to/your/project/main.py >> /path/to/your/project/bot_data/cron.log 2>&1
```

## 8. Running the Test Suite

To ensure all components are working correctly, run the full test suite:

```bash
pytest
```

## 9. Disclaimer

Trading cryptocurrencies involves significant risk. This script is provided for educational purposes only and should not be used for live trading without thorough testing and a complete understanding of its operation and risks. The author is not responsible for any financial losses. Always use a sandbox or paper trading environment first.
