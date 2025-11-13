# FXSwap Refuel Contract

A Vyper smart contract for refueling FXSwap pools by withdrawing LP tokens and re-adding them as donations.

## Overview

This contract implements the same refuel logic from the Python script, but in a Vyper smart contract. It allows automated refueling of FXSwap pools based on LP token amounts (not USD values).

## Key Features

- **LP Token Based**: Set refuel amounts in LP tokens, not USD
- **Donation Threshold**: Ensures donation share meets minimum threshold before refueling
- **Pool Agnostic**: Can be configured to work with any FXSwap pool
- **Owner Controlled**: All sensitive operations restricted to contract owner

## Contract Functions

### Admin Functions

#### `set_pool(new_pool: address)`
Set the FXSwap pool address to interact with.
- **Access**: Owner only
- **Parameters**:
  - `new_pool`: Address of the FXSwap pool contract

#### `set_refuel_amount(lp_amount: uint256)`
Set the amount of LP tokens to use for refueling.
- **Access**: Owner only
- **Parameters**:
  - `lp_amount`: Amount of LP tokens (e.g., 1000000000000000000 for 1 LP token)

#### `set_donation_threshold(threshold: uint256)`
Set the minimum donation share threshold in basis points.
- **Access**: Owner only
- **Parameters**:
  - `threshold`: Minimum donation share (e.g., 9500 = 95%)
- **Default**: 9500 (95%)

### Core Functions

#### `refuel() -> uint256`
Execute the refuel operation.

**Process**:
1. Checks contract has enough LP tokens
2. Withdraws LP tokens from pool to get underlying tokens
3. Calculates expected LP tokens from re-adding as donation
4. Verifies donation share meets threshold
5. Re-adds tokens to pool with `donation=True` (LP tokens burned)

**Returns**: Amount of LP tokens donated

**Reverts if**:
- Pool not set
- Refuel amount not set
- Insufficient LP tokens in contract
- Donation share below threshold

### View Functions

#### `get_lp_balance() -> uint256`
Returns the LP token balance of this contract.

#### `calculate_donation_share() -> uint256`
Calculates the current donation share in basis points based on pool state and refuel amount.

**Returns**: Donation share (e.g., 9750 = 97.5%)

### Utility Functions

#### `withdraw_lp_tokens(amount: uint256)`
Withdraw LP tokens from the contract (owner only).

#### `withdraw_tokens(token: address, amount: uint256)`
Withdraw any ERC20 tokens from the contract (owner only).

#### `transfer_ownership(new_owner: address)`
Transfer contract ownership to a new address.

## How It Works

### Donation Share Calculation

The **donation share** represents how much value is donated back to the pool:

```
donation_share = (LP tokens to be minted / LP tokens withdrawn) * 100%
```

For example:
- Withdraw 1.0 LP token from pool → Get tokens worth 1.0 LP
- Re-add those tokens as donation → Pool mints 0.97 LP tokens (burned)
- Donation share = 0.97 / 1.0 = 97%

A donation share below 100% means some value is lost due to:
- Pool imbalance
- Slippage
- Price impact

### Threshold Check

The contract only allows refueling if the donation share meets the threshold:

```python
if donation_share >= donation_share_threshold:
    # Allow refueling
else:
    # Revert transaction
```

This protects against refueling when pool conditions are unfavorable.

## Usage Example

### 1. Deploy Contract
```python
from vyper import compile_code

# Deploy to network
refuel_contract = deploy_contract("Refuel.vy")
```

### 2. Configure Pool
```python
# Set the FXSwap pool address
refuel_contract.set_pool("0x1234...POOL_ADDRESS")
```

### 3. Set Refuel Amount
```python
# Set refuel amount to 1 LP token (18 decimals)
lp_amount = 1 * 10**18
refuel_contract.set_refuel_amount(lp_amount)
```

### 4. (Optional) Set Donation Threshold
```python
# Set threshold to 95% (9500 basis points)
refuel_contract.set_donation_threshold(9500)
```

### 5. Send LP Tokens to Contract
```python
# Transfer LP tokens to the contract
lp_token.transfer(refuel_contract.address, lp_amount)
```

### 6. Execute Refuel
```python
# Check current donation share
donation_share = refuel_contract.calculate_donation_share()
print(f"Current donation share: {donation_share / 100}%")

# Execute refuel if threshold is met
if donation_share >= 9500:
    tx = refuel_contract.refuel()
    print(f"Refueled! Donated LP: {tx.return_value}")
```

## State Variables

- `owner`: Contract owner address
- `pool`: FXSwap pool contract address
- `refuel_lp_amount`: LP token amount to use for refueling
- `donation_share_threshold`: Minimum donation share (basis points)

## Events

- `PoolSet`: Emitted when pool address is updated
- `RefuelAmountSet`: Emitted when refuel amount is updated
- `ThresholdSet`: Emitted when donation threshold is updated
- `Refueled`: Emitted when refuel operation completes
- `OwnershipTransferred`: Emitted when ownership is transferred

## Security Considerations

- All admin functions are owner-only
- Contract validates donation share before refueling
- Owner can withdraw any stuck tokens
- No slippage protection on liquidity operations (uses min_amounts = [0, 0])

## Compilation

Compile with Vyper 0.4.3 or later:

```bash
vyper contracts/Refuel.vy
```

**Note**: This contract uses Vyper 0.4.3 syntax with the following key features:
- `#pragma version ^0.4.3` version pragma
- `from ethereum.ercs import IERC20` for ERC20 interface imports
- Modern Vyper 0.4.x syntax and type system

## License

This contract is provided as-is. Use at your own risk.
