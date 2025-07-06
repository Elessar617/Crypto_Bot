# Crypto Trading Bot in R

The trader’s mind is the weak link in any trading strategy or plan. Effective trading execution needs human inputs that run in the opposite direction to our instincts. We should buy when our reptile brain wants to sell. We should sell when our guts want us to buy more.

It is even more difficult to trade cryptocurrencies with a critical constitution. The young and emerging markets are flooded with “pump groups” that foster intense FOMO (fear of missing out) which drive prices sky-high before body-slamming them back down to earth. Many novice investors also trade on these markets, investors that possibly never entered a trade on the NYSE. On every trade, there is a maker and a taker, and shrewd crypto investors find it easy to take advantage of the novices flooding the space.

In order to detach my emotions from crypto trading and to take advantage of markets open 24/7, I decided to build a simple trading bot that would follow a simple strategy and execute trades as I slept.

Many “bot traders” as they are called, use the Python programming language to execute these trades. If you were to Google “crypto trading bot,” you would find links to Python code in various GitHub repositories.

I’m a data scientist, and R is my main tool. I searched for a decent tutorial on using the R language to build a trading bot but found nothing. I was set on building my own package to interface with the GDAX API when I found the package `rgdax`, which is an R wrapper for the GDAX API. The following is a guide to piecing together a trading bot that you can use to build your own strategies.

## The Strategy

In a nutshell, we will be trading the Ethereum–USD pair on the GDAX exchange through their API via the `rgdax` wrapper. I like trading this pair because Ethereum (ETH) is typically in a bullish stance, which allows this strategy to shine.

> **Note:** This is a super-simplistic strategy that will only make a few bucks in a bull market. For all intents and purposes, use this as a base for building your own strategy.

We will be buying when a combination of Relative Strength Index (RSI) indicators point to a temporarily oversold market, with the assumption that the bulls will once again push the prices up and we can gather profits.

Once we buy, the bot will enter three limit sell orders:

1. At 1% profit  
2. At 4% profit  
3. At 7% profit  

This allows us to quickly free up funds to enter another trade with the first two orders, and the 7% order bolsters our overall profitability.

## Software

We will be using **RStudio** and **Windows Task Scheduler** to execute our R code on a regular basis (every 10 minutes). You will need a GDAX account to send orders to, and a Gmail account to receive trade notifications.

## Our Process

### Part 1: Call Libraries and Build Functions

Begin by loading the necessary packages in R:

- **`rgdax`**: Interface to the GDAX API  
- **`mailR`**: Send email updates via Gmail  
- **`stringi`**: Parse numbers from JSON  
- **`TTR`**: Calculate technical indicators (e.g., RSI)

#### Function: `curr_bal_usd` & `curr_bal_eth`

These functions query your GDAX account for the most recent balance:

```r
curr_bal_usd <- function() { ... }
curr_bal_eth <- function() { ... }
```

#### Function: RSI

Pulls in the value of the most recent 14-period RSI using 15-minute candles:

```r
curr_rsi14_api <- function() { ... }
rsi14_api_less_one <- function() { ... }
# and so on...
```

#### Function: `bid` & `ask`

Retrieves the current bid and ask prices:

```r
bid <- function() { ... }
ask <- function() { ... }
```

#### Function: `usd_hold`, `eth_hold`, and `cancel_orders`

Manage open orders and cancel stale ones:

```r
usd_hold <- function() { ... }
eth_hold <- function() { ... }
cancel_orders <- function() { ... }
```

#### Function: `buy_exe`

Executes our limit buy orders in a loop until filled:

1. Calculate order size (minus a small buffer).  
2. Place a limit buy order at `bid()` price.  
3. Sleep 17 seconds, then check fill status.  
4. Cancel and retry if not filled.  

### Part 2: Store Variables

Cache RSI values in objects to speed up the loop and avoid API rate limits:

```r
curr_rsi14_api <- curr_rsi14_api()
Sys.sleep(2)
# and so on...
```

### Part 3: Trading Loop Executes

A verbal walkthrough:

1. If USD balance ≥ \$20, start.  
2. If current RSI ≥ 30, previous RSI ≤ 30, and at least one of the last three RSIs < 30 → buy.  
3. Save buy price to CSV for persistence.  
4. Send email notification of the buy.  
5. Print `"buy"` to the log.  
6. Sleep 3 seconds.  
7. Place tiered limit sell orders (1%, 4%, 7%).  

### Part 4: Automate with Windows Task Scheduler

1. Use the RStudio **add-in** to schedule the script.  
2. Modify the trigger in Task Scheduler for every 10 minutes (or preferred interval).  
3. Monitor via the script’s log file (`START LOG ENTRY` / `END LOG ENTRY` markers).

## Make It Your Own

- Modify strategy parameters or add new technical indicators (e.g., MACD, Bollinger Bands).  
- Integrate neural networks via the **TensorFlow/Keras** R package for pattern recognition.  
- **Warning**: Markets aren’t a game—don’t risk more than you can afford to lose.
