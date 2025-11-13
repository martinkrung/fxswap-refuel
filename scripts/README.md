# Deployment and Verification Scripts

This directory contains scripts for deploying and verifying the FXSwap Refuel contracts on multiple chains.

## Quick Start

### 1. Install Dependencies

```bash
# Run the installation script
./install.sh

# Or manually install
pip install vyper>=0.4.3 titanoboa>=0.2.0 web3>=6.0.0 pyyaml requests eth-abi
```

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your API keys
nano .env

# Load environment variables
source .env  # or: export $(cat .env | xargs)
```

### 3. Deploy Contracts

```bash
# Deploy to Base Mainnet
python scripts/deploy.py --chain base

# Deploy to Base Sepolia (testnet)
python scripts/deploy.py --chain base-sepolia

# Deploy to other chains
python scripts/deploy.py --chain ethereum
python scripts/deploy.py --chain arbitrum
python scripts/deploy.py --chain optimism
```

### 4. Verify Contracts

```bash
# Verify using deployment log
python scripts/verify.py --deployment deployments/deployment_base_latest.yaml

# Or verify individual contract
python scripts/verify.py --contract 0x... --chain base --name RefuelFactory
```

## Scripts

### `deploy.py`

Deploys the Refuel blueprint and RefuelFactory contracts to any supported chain.

**Features:**
- Deploys both blueprint and factory contracts
- Logs deployment to YAML file
- Supports multiple chains (Base, Ethereum, Arbitrum, Optimism, etc.)
- Uses Alchemy or custom RPC endpoints
- Prompts for private key (never stores it)

**Usage:**

```bash
python scripts/deploy.py --chain <chain_name> [--skip-verification]
```

**Options:**
- `--chain`: Chain to deploy to (base, base-sepolia, ethereum, etc.)
- `--skip-verification`: Skip automatic verification after deployment

**Example:**

```bash
# Deploy to Base Mainnet
python scripts/deploy.py --chain base

# Deploy to Base Sepolia without verification
python scripts/deploy.py --chain base-sepolia --skip-verification
```

### `verify.py`

Verifies deployed contracts on Etherscan/Blockscout.

**Features:**
- Verifies contracts using deployment log
- Supports individual contract verification
- Handles constructor arguments automatically
- Updates deployment log with verification status

**Usage:**

```bash
# Verify from deployment log
python scripts/verify.py --deployment <path_to_deployment.yaml>

# Verify individual contract
python scripts/verify.py --contract <address> --chain <chain> --name <contract_name>
```

**Options:**
- `--deployment`: Path to deployment YAML file
- `--contract`: Contract address to verify
- `--chain`: Chain name (required with --contract)
- `--name`: Contract name (Refuel or RefuelFactory)
- `--constructor-args`: Hex-encoded constructor arguments

**Examples:**

```bash
# Verify from deployment log
python scripts/verify.py --deployment deployments/deployment_base_latest.yaml

# Verify factory contract manually
python scripts/verify.py --contract 0x... --chain base --name RefuelFactory

# Verify with constructor args
python scripts/verify.py --contract 0x... --chain base --name RefuelFactory --constructor-args 0x000...
```

### `chains.yaml`

Configuration file for supported chains.

**Supported Chains:**
- **Base Mainnet** (`base`)
- **Base Sepolia** (`base-sepolia`)
- **Ethereum Mainnet** (`ethereum`)
- **Sepolia Testnet** (`sepolia`)
- **Arbitrum One** (`arbitrum`)
- **Optimism** (`optimism`)

**Adding New Chains:**

Edit `scripts/chains.yaml` and add a new chain configuration:

```yaml
chains:
  your-chain:
    chain_id: 12345
    name: "Your Chain Name"
    rpc_env_var: "YOUR_CHAIN_RPC_URL"
    explorer_url: "https://explorer.yourchain.com"
    explorer_api_url: "https://api.explorer.yourchain.com/api"
    explorer_api_key_env: "YOUR_CHAIN_API_KEY"
    native_currency: "ETH"
```

## Environment Variables

### Required for Deployment

**Option 1: Alchemy (Recommended)**
```bash
ALCHEMY_API_KEY=your_alchemy_api_key
```

**Option 2: Custom RPC URLs**
```bash
BASE_RPC_URL=https://mainnet.base.org
ETHEREUM_RPC_URL=https://eth.llamarpc.com
# ... etc
```

### Required for Verification

```bash
BASESCAN_API_KEY=your_basescan_api_key
ETHERSCAN_API_KEY=your_etherscan_api_key
ARBISCAN_API_KEY=your_arbiscan_api_key
OPTIMISTIC_ETHERSCAN_API_KEY=your_optimistic_etherscan_api_key
```

### Getting API Keys

**Alchemy:**
1. Sign up at https://www.alchemy.com
2. Create a new app
3. Copy the API key

**Basescan/Etherscan:**
1. Sign up at https://basescan.org or https://etherscan.io
2. Go to API Keys section
3. Create a new API key
4. Copy the key

## Deployment Logs

Deployment logs are saved in YAML format to the `deployments/` directory.

**File Naming:**
- `deployment_<chain>_<timestamp>.yaml` - Timestamped log
- `deployment_<chain>_latest.yaml` - Latest deployment (symlink)

**Log Structure:**

```yaml
deployment_info:
  timestamp: "2024-01-15T10:30:00"
  deployer: "0x..."
  chain: "base"
  chain_id: 8453

contracts:
  refuel_blueprint:
    address: "0x..."
    contract_type: "blueprint"
    vyper_version: "0.4.3"

  refuel_factory:
    address: "0x..."
    blueprint_address: "0x..."
    contract_type: "factory"
    vyper_version: "0.4.3"

verification:
  refuel_blueprint:
    status: "success"
    message: "Verified"
    explorer_url: "https://basescan.org/address/0x...#code"

  refuel_factory:
    status: "success"
    message: "Verified"
    explorer_url: "https://basescan.org/address/0x...#code"
```

## Security Best Practices

### Private Key Management

1. **Never commit private keys** to version control
2. **Use environment variables** for sensitive data
3. **Input private key via CLI** when deploying (script prompts securely)
4. **Use hardware wallets** when possible
5. **Test on testnets first** before mainnet deployment

### Pre-Deployment Checklist

- [ ] Environment variables are set correctly
- [ ] Private key has sufficient balance for gas
- [ ] Contracts are compiled without errors
- [ ] Tests are passing
- [ ] Deploying to correct chain
- [ ] Double-check contract parameters

## Troubleshooting

### Deployment Fails

**Issue:** "RPC URL not found"
- **Solution:** Set `ALCHEMY_API_KEY` or chain-specific RPC URL in `.env`

**Issue:** "Deployer has zero balance"
- **Solution:** Fund the deployer address with native currency

**Issue:** "Invalid private key"
- **Solution:** Check private key format (should start with 0x)

### Verification Fails

**Issue:** "API key not set"
- **Solution:** Set the appropriate `*SCAN_API_KEY` in `.env`

**Issue:** "Verification timeout"
- **Solution:** Check verification status manually on block explorer
- The contract may still be verifying in the background

**Issue:** "Already verified"
- **Solution:** This is normal if re-running verification
- Check the explorer to confirm

## Example Workflow

### Deploy to Base Mainnet

```bash
# 1. Set up environment
cp .env.example .env
# Edit .env with your API keys
nano .env

# 2. Load environment
export $(cat .env | xargs)

# 3. Deploy contracts
python scripts/deploy.py --chain base

# When prompted, enter your private key
# Private Key: ****************************************

# 4. Verify contracts
python scripts/verify.py --deployment deployments/deployment_base_latest.yaml

# 5. Check deployment log
cat deployments/deployment_base_latest.yaml
```

### Deploy Refuel Instance

After deploying the factory, deploy a Refuel instance:

```python
from web3 import Web3
from eth_account import Account
import yaml

# Load deployment
with open("deployments/deployment_base_latest.yaml") as f:
    deployment = yaml.safe_load(f)

factory_address = deployment["contracts"]["refuel_factory"]["address"]

# Connect to Web3
w3 = Web3(Web3.HTTPProvider(RPC_URL))
account = Account.from_key(PRIVATE_KEY)

# Load factory ABI (from compiled contract)
factory = w3.eth.contract(address=factory_address, abi=FACTORY_ABI)

# Deploy Refuel instance
tx = factory.functions.deploy_refuel_simple(account.address).build_transaction({
    "from": account.address,
    "nonce": w3.eth.get_transaction_count(account.address),
})

signed_tx = account.sign_transaction(tx)
tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)

print(f"Refuel instance deployment tx: {tx_hash.hex()}")
```

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the deployment logs in `deployments/`
3. Open an issue on GitHub
