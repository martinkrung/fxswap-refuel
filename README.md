# Tool to refuel a pool with desired amount of USD/APR per Year

## What is this

This is a script which withdraws a defined amount of LP tokens from a pool and re-adds the amount as refuel.
Users are prompted for a USD amount, which is then used to calculate the needed share.
The address needs unstaked LP tokens from the pool to be used in refueling.

## Preview

```
Pool address: 0x1C53971800C111a32B7889177C56E3488cfe0BE0
Pool name: USDC/EURC A50-5
Token 0 address: 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913
Token 1 address: 0x60a3E35Cc302bFA44Cb288Bc5a4F316Fdb1adb42
Token 0: USD Coin (6 decimals)
Token 1: EURC (6 decimals)
USD Coin is USDC, using price: $1.00
Calculated EURC price from pool last_price: $1.159377 per EURC
Current balance(0): 5379.604449 USD Coin
Current balance(1): 4033.971517 EURC
Current totalSupply: 4669.981405437919 LP tokens
Current pool value: $10056.50 USD
  - USD Coin: 5379.60 USD (at $1.000000 per USD Coin)
  - EURC: 4676.89 USD (at $1.159377 per EURC)

Value of 1 LP token (1.0 LP):
  - 1.15195415 USD Coin = $1.151954
  - 0.86380890 EURC = $1.001480
Total: $2.153434 per 1 LP token

Enter USD value you want to refuel: 1

Target LP tokens for $1.00 USD: 0.46437456
Calculated LP tokens from withdrawing: 0.46436934956285525

Token amounts from withdrawing 0.46436934956285525 LP tokens:
  token0_amount: 0.534938 USD Coin
  token1_amount: 0.40113 EURC

Total refuel value: 1.00 USD
  - USD Coin: 0.53 USD (at $1.000000 per USD Coin)
  - EURC: 0.47 USD (at $1.159377 per EURC)

Estimated APR from this refuel (assuming steady spend, 1 refuel / 7d): 0.5185% per year
  Formula: APR = (refuel_total_value_usd * 365 / 7) / total_pool_value_usd
  Where: refuel_total_value_usd = 1.00, total_pool_value_usd = 10056.50

USD required to maintain this refuel rate for 1 year: $52.14

Verification - LP tokens from re-adding:
  Expected LP tokens: 0.46436934956285525
  Target LP tokens: 0.46436934956285525
  Difference: -1 LP tokens

Withdrawing from pool to get refuel tokens...
Loading account from: /home/m/.accounts/yourfilename.json
Password: 
Account loaded: 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913
Chain: 8453, Deployer: 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913, Balance: 0.002

Token balances before withdrawal:
  USD Coin: 1.026497
  EURC: 0.841139
Estimated gas for withdrawal: 106570
Sending withdrawal transaction...
Withdrawal transaction hash: a...
Waiting for withdrawal transaction receipt...
✓ Withdrawal successful! Tokens received.
Waiting 10 seconds before adding liquidity for refuel...

Actual token amounts received from withdrawal:
  USD Coin: 0.534932
  EURC: 0.401126

Transaction parameters (using actual received amounts):
  amounts: [0.53493200 USD Coin, 0.40112600 EURC]
  amounts (raw): [534932, 401126]
  min_mint_amount: 0.46436471 LP tokens
  receiver: 0x0000000000000000000000000000000000000000
  donation: True

Preparing add_liquidity transaction...
Using nonce: 380 (withdrawal used nonce 379)
Estimated gas: 190626

Sending transaction...
Transaction hash: c....
Waiting for transaction receipt...
✓ Transaction successful!
Block number: 38041949
Gas used: 187967
```


## Installation

Use our installation script to set up everything automatically:

```bash
chmod +x install.sh
./install.sh
```

## Usage

After installation, make sure your virtual environment is activated
and load the environment variables from .env_ethereum:

```bash
cp env_example .env_ethereum
```

```bash
source .venv/bin/activate
source .env_ethereum
```

config:

add your pool to the config/fxswap.json and adjust index in the code 
or set the pool address it directly in the code. (line 95-102)


run with:

```bash
scripts/refule_any_pool.py
```
