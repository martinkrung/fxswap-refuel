#!/usr/bin/env python3
"""
Deployment script for FXSwap Refuel contracts

Usage:
    python scripts/deploy.py --chain base --network mainnet
    python scripts/deploy.py --chain base-sepolia --network testnet
"""

import os
import sys
import yaml
import json
import getpass
from datetime import datetime
from pathlib import Path

import boa
from eth_account import Account
from web3 import Web3


# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class DeploymentLogger:
    """Handles deployment logging to YAML"""

    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.log_dir.mkdir(exist_ok=True, parents=True)

        self.deployment_data = {
            "deployment_info": {
                "timestamp": datetime.utcnow().isoformat(),
                "deployer": None,
                "chain": None,
                "chain_id": None,
            },
            "contracts": {},
            "verification": {},
        }

    def set_chain_info(self, chain_name: str, chain_id: int, deployer: str):
        """Set chain and deployer information"""
        self.deployment_data["deployment_info"]["chain"] = chain_name
        self.deployment_data["deployment_info"]["chain_id"] = chain_id
        self.deployment_data["deployment_info"]["deployer"] = deployer

    def log_contract(self, contract_name: str, address: str, tx_hash: str = None, **kwargs):
        """Log a deployed contract"""
        self.deployment_data["contracts"][contract_name] = {
            "address": address,
            "tx_hash": tx_hash,
            **kwargs,
        }

    def log_verification(self, contract_name: str, status: str, **kwargs):
        """Log verification status"""
        self.deployment_data["verification"][contract_name] = {
            "status": status,
            **kwargs,
        }

    def save(self):
        """Save deployment log to YAML"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        chain = self.deployment_data["deployment_info"]["chain"]
        filename = f"deployment_{chain}_{timestamp}.yaml"

        log_file = self.log_dir / filename
        latest_file = self.log_dir / f"deployment_{chain}_latest.yaml"

        with open(log_file, "w") as f:
            yaml.dump(self.deployment_data, f, default_flow_style=False, sort_keys=False)

        # Also save as latest
        with open(latest_file, "w") as f:
            yaml.dump(self.deployment_data, f, default_flow_style=False, sort_keys=False)

        print(f"\n✓ Deployment log saved to: {log_file}")
        print(f"✓ Latest deployment: {latest_file}")

        return log_file


class ChainConfig:
    """Chain configuration loader"""

    def __init__(self, config_file: Path):
        with open(config_file, "r") as f:
            self.config = yaml.safe_load(f)

    def get_chain(self, chain_name: str):
        """Get chain configuration"""
        if chain_name not in self.config["chains"]:
            raise ValueError(f"Unknown chain: {chain_name}")

        return self.config["chains"][chain_name]

    def get_rpc_url(self, chain_name: str):
        """Get RPC URL for chain"""
        chain = self.get_chain(chain_name)

        # Try Alchemy first if API key is set
        alchemy_key = os.getenv("ALCHEMY_API_KEY")
        if alchemy_key and chain_name in self.config.get("alchemy_rpcs", {}):
            return self.config["alchemy_rpcs"][chain_name] + alchemy_key

        # Fall back to env var
        rpc_env_var = chain["rpc_env_var"]
        rpc_url = os.getenv(rpc_env_var)

        if not rpc_url:
            raise ValueError(
                f"RPC URL not found. Set {rpc_env_var} or ALCHEMY_API_KEY environment variable"
            )

        return rpc_url


def get_private_key():
    """Get deployer private key from CLI input"""
    print("\n" + "=" * 60)
    print("DEPLOYER PRIVATE KEY")
    print("=" * 60)
    print("Enter your private key (input will be hidden)")
    print("WARNING: Make sure you're in a secure environment")
    print("=" * 60)

    private_key = getpass.getpass("Private Key: ")

    # Validate private key format
    if not private_key.startswith("0x"):
        private_key = "0x" + private_key

    try:
        account = Account.from_key(private_key)
        print(f"\n✓ Deployer address: {account.address}")
        return private_key
    except Exception as e:
        print(f"\n✗ Invalid private key: {e}")
        sys.exit(1)


def deploy_contracts(chain_name: str, private_key: str, logger: DeploymentLogger):
    """Deploy all contracts"""

    # Load chain config
    config_file = PROJECT_ROOT / "scripts" / "chains.yaml"
    chain_config = ChainConfig(config_file)

    chain = chain_config.get_chain(chain_name)
    rpc_url = chain_config.get_rpc_url(chain_name)

    print(f"\n{'=' * 60}")
    print(f"DEPLOYMENT TO {chain['name'].upper()}")
    print(f"{'=' * 60}")
    print(f"Chain ID: {chain['chain_id']}")
    print(f"Explorer: {chain['explorer_url']}")
    print(f"RPC URL: {rpc_url[:50]}...")
    print(f"{'=' * 60}\n")

    # Setup boa with network
    account = Account.from_key(private_key)
    boa.set_network_env(rpc_url)
    boa.env.add_account(account, force_eoa=True)

    # Set chain info in logger
    logger.set_chain_info(chain_name, chain["chain_id"], account.address)

    # Get deployer balance
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    balance = w3.eth.get_balance(account.address)
    balance_eth = w3.from_wei(balance, "ether")

    print(f"Deployer: {account.address}")
    print(f"Balance: {balance_eth:.4f} {chain['native_currency']}")

    if balance == 0:
        print("\n✗ ERROR: Deployer has zero balance!")
        sys.exit(1)

    print("\n" + "-" * 60)

    # Step 1: Deploy Refuel blueprint
    print("\n[1/2] Deploying Refuel blueprint...")
    blueprint = boa.load("contracts/Refuel.vy")
    print(f"✓ Refuel blueprint deployed: {blueprint.address}")

    logger.log_contract(
        "refuel_blueprint",
        blueprint.address,
        contract_type="blueprint",
        vyper_version="0.4.3",
    )

    # Step 2: Deploy Factory
    print("\n[2/2] Deploying RefuelFactory...")
    factory = boa.load("contracts/RefuelFactory.vy", blueprint.address)
    print(f"✓ RefuelFactory deployed: {factory.address}")

    logger.log_contract(
        "refuel_factory",
        factory.address,
        blueprint_address=blueprint.address,
        contract_type="factory",
        vyper_version="0.4.3",
    )

    print("\n" + "-" * 60)
    print("\n✓ DEPLOYMENT COMPLETE!")
    print(f"\nRefuel Blueprint: {blueprint.address}")
    print(f"RefuelFactory: {factory.address}")

    return {
        "blueprint": blueprint,
        "factory": factory,
        "chain": chain,
    }


def main():
    """Main deployment function"""
    import argparse

    parser = argparse.ArgumentParser(description="Deploy FXSwap Refuel contracts")
    parser.add_argument(
        "--chain",
        type=str,
        default="base",
        help="Chain to deploy to (base, base-sepolia, ethereum, etc.)",
    )
    parser.add_argument(
        "--skip-verification",
        action="store_true",
        help="Skip contract verification",
    )
    args = parser.parse_args()

    # Initialize logger
    log_dir = PROJECT_ROOT / "deployments"
    logger = DeploymentLogger(log_dir)

    try:
        # Get private key
        private_key = get_private_key()

        # Deploy contracts
        deployment = deploy_contracts(args.chain, private_key, logger)

        # Save deployment log
        log_file = logger.save()

        # Print next steps
        print("\n" + "=" * 60)
        print("NEXT STEPS")
        print("=" * 60)

        if not args.skip_verification:
            print("\n1. Verify contracts:")
            print(f"   python scripts/verify.py --deployment {log_file}")

        print("\n2. Deploy a Refuel instance:")
        print(f"   Factory address: {deployment['factory'].address}")
        print(f"   Call: factory.deploy_refuel(owner_address, fee_recipient)")

        print("\n3. Explorer links:")
        print(
            f"   Factory: {deployment['chain']['explorer_url']}/address/{deployment['factory'].address}"
        )
        print(
            f"   Blueprint: {deployment['chain']['explorer_url']}/address/{deployment['blueprint'].address}"
        )

        print("\n" + "=" * 60)

    except KeyboardInterrupt:
        print("\n\n✗ Deployment cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Deployment failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
