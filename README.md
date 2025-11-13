# FXSwap Refuel

Automated LP token refueling for FXSwap pools with configurable fees.

## Features

- **LP Token Based** - Set refuel amounts in LP tokens (not USD)
- **Fee Mechanism** - 5% fee (500 bps) on refuel operations
- **Factory Pattern** - Deploy multiple Refuel instances efficiently
- **Multi-Chain** - Base, Ethereum, Arbitrum, Optimism support
- **Donation Threshold** - Safety check prevents unfavorable refuels (default 95%)

## Quick Start

```bash
# Install
./install.sh

# Test
pytest tests/test_refuel.py -v

# Deploy to Base
python scripts/deploy.py --chain base

# Verify
python scripts/verify.py --deployment deployments/deployment_base_latest.yaml
```

## Setup

```bash
# 1. Configure environment
cp .env.example .env
nano .env  # Add ALCHEMY_API_KEY and BASESCAN_API_KEY

# 2. Activate environment
source .venv/bin/activate
export $(cat .env | xargs)
```

## Deploy

```bash
# Deploy blueprint + factory
python scripts/deploy.py --chain base

# Deploy to testnet
python scripts/deploy.py --chain base-sepolia

# Other chains
python scripts/deploy.py --chain ethereum
python scripts/deploy.py --chain arbitrum
```

## Usage

### Python (via boa)

```python
import boa

# Load factory (after deployment)
factory = boa.load_partial("contracts/RefuelFactory.vy").at(FACTORY_ADDRESS)

# Deploy Refuel instance
refuel_addr = factory.deploy_refuel_simple(OWNER_ADDRESS)
refuel = boa.load_partial("contracts/Refuel.vy").at(refuel_addr)

# Configure
refuel.set_pool(POOL_ADDRESS)
refuel.set_refuel_amount(10 * 10**18)  # 10 LP tokens

# Send LP tokens to contract
lp_token.transfer(refuel.address, 10 * 10**18)

# Execute refuel (takes 5% fee)
donated = refuel.refuel()
```

### Web3

```python
from web3 import Web3

w3 = Web3(Web3.HTTPProvider(RPC_URL))
factory = w3.eth.contract(address=FACTORY_ADDR, abi=FACTORY_ABI)

# Deploy instance
tx = factory.functions.deploy_refuel_simple(owner).build_transaction({...})
```

## Contracts

### Refuel.vy (Blueprint)

- `initialize(owner, fee_recipient)` - Init after factory deployment
- `set_pool(pool)` - Set FXSwap pool
- `set_refuel_amount(amount)` - Set LP amount
- `refuel()` - Execute refuel with fee
- `calculate_donation_share()` - Preview donation (view)

### RefuelFactory.vy

- `deploy_refuel(owner, fee_recipient)` - Deploy instance
- `deploy_refuel_simple(owner)` - Deploy (factory = fee recipient)
- `withdraw_fees(token, recipient, amount)` - Withdraw collected fees
- `update_blueprint(new_blueprint)` - Update blueprint

## Fee Flow

```
Refuel: 10 LP tokens
   ↓
Fee: 0.5 LP → Fee Recipient (5%)
   ↓
Remaining: 9.5 LP
   ↓
Withdraw from pool → Get underlying tokens
   ↓
Re-add as donation → LP minted to 0x0 (burned)
```

## Environment

```bash
# RPC (pick one)
ALCHEMY_API_KEY=...                    # Recommended
BASE_RPC_URL=https://mainnet.base.org  # Alternative

# Verification
BASESCAN_API_KEY=...
ETHERSCAN_API_KEY=...
```

## Chains

- `base` - Base Mainnet
- `base-sepolia` - Base Testnet
- `ethereum` - Ethereum Mainnet
- `sepolia` - Sepolia Testnet
- `arbitrum` - Arbitrum One
- `optimism` - Optimism

Edit `scripts/chains.yaml` to add more chains.

## Deployment Logs

Saved to `deployments/deployment_<chain>_<timestamp>.yaml`:

```yaml
deployment_info:
  chain: "base"
  deployer: "0x..."

contracts:
  refuel_blueprint:
    address: "0x..."
  refuel_factory:
    address: "0x..."

verification:
  refuel_factory:
    status: "success"
```

## Project Structure

```
contracts/
├── Refuel.vy            # Refuel contract (blueprint)
├── RefuelFactory.vy     # Factory contract
└── README.md

scripts/
├── deploy.py            # Deployment script
├── verify.py            # Verification script
├── chains.yaml          # Chain config
└── README.md

tests/
├── test_refuel.py       # Contract tests
├── test_factory.py      # Factory tests
└── requirements.txt

deployments/             # YAML logs
```

## Python Script (Original)

```bash
# Activate environment
source .venv/bin/activate
source .env_ethereum

# Run Python refuel script
python scripts/refuel_any_pool.py
```

## Security

- ✓ Owner-only admin functions
- ✓ Initialized flag prevents re-init
- ✓ Donation threshold validation
- ⚠ No slippage protection (min_amounts = [0, 0])

## Development

```bash
# Compile
vyper contracts/Refuel.vy
vyper contracts/RefuelFactory.vy

# Test
pytest tests/ -v

# Add test
pytest tests/test_factory.py::TestFactoryDeployment -v
```

## License

Use at your own risk.
