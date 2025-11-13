#!/usr/bin/env python3
"""
Contract verification script for Etherscan/Blockscout

Usage:
    python scripts/verify.py --deployment deployments/deployment_base_latest.yaml
    python scripts/verify.py --contract 0x... --chain base --name RefuelFactory
"""

import os
import sys
import yaml
import json
import time
import requests
from pathlib import Path
from typing import Dict, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class ContractVerifier:
    """Handles contract verification on Etherscan/Blockscout"""

    def __init__(self, chain_name: str):
        self.chain_name = chain_name

        # Load chain config
        config_file = PROJECT_ROOT / "scripts" / "chains.yaml"
        with open(config_file, "r") as f:
            config = yaml.safe_load(f)

        if chain_name not in config["chains"]:
            raise ValueError(f"Unknown chain: {chain_name}")

        self.chain_config = config["chains"][chain_name]
        self.api_url = self.chain_config["explorer_api_url"]

        # Get API key
        api_key_env = self.chain_config["explorer_api_key_env"]
        self.api_key = os.getenv(api_key_env)

        if not self.api_key:
            print(f"\n⚠ WARNING: {api_key_env} not set. Verification may fail.")
            print(f"   Set the API key in your environment variables")

    def get_contract_source(self, contract_name: str) -> str:
        """Get contract source code"""
        contract_file = PROJECT_ROOT / "contracts" / f"{contract_name}.vy"

        if not contract_file.exists():
            raise FileNotFoundError(f"Contract file not found: {contract_file}")

        with open(contract_file, "r") as f:
            return f.read()

    def verify_contract(
        self,
        contract_address: str,
        contract_name: str,
        constructor_args: Optional[str] = None,
        compiler_version: str = "v0.4.3+commit.bff19ea2",
    ) -> Dict:
        """Verify contract on Etherscan/Blockscout"""

        print(f"\n{'=' * 60}")
        print(f"VERIFYING: {contract_name}")
        print(f"{'=' * 60}")
        print(f"Address: {contract_address}")
        print(f"Chain: {self.chain_name}")
        print(f"Explorer: {self.chain_config['explorer_url']}")
        print(f"{'=' * 60}\n")

        # Get source code
        source_code = self.get_contract_source(contract_name)

        # Prepare verification data
        data = {
            "apikey": self.api_key or "",
            "module": "contract",
            "action": "verifysourcecode",
            "contractaddress": contract_address,
            "sourceCode": source_code,
            "codeformat": "solidity-single-file",  # Vyper uses same format
            "contractname": contract_name,
            "compilerversion": compiler_version,
            "optimizationUsed": "0",
        }

        if constructor_args:
            data["constructorArguements"] = constructor_args

        # Submit verification
        print("Submitting verification request...")

        try:
            response = requests.post(self.api_url, data=data)
            result = response.json()

            if result.get("status") == "1":
                guid = result.get("result")
                print(f"✓ Verification submitted. GUID: {guid}")

                # Check verification status
                return self.check_verification_status(guid, contract_address, contract_name)

            else:
                error_msg = result.get("result", "Unknown error")
                print(f"✗ Verification failed: {error_msg}")

                # Check if already verified
                if "already verified" in error_msg.lower():
                    print(f"✓ Contract is already verified")
                    return {
                        "status": "success",
                        "message": "Already verified",
                    }

                return {
                    "status": "failed",
                    "message": error_msg,
                }

        except Exception as e:
            print(f"✗ Verification request failed: {e}")
            return {
                "status": "error",
                "message": str(e),
            }

    def check_verification_status(
        self, guid: str, contract_address: str, contract_name: str, max_attempts: int = 10
    ) -> Dict:
        """Check verification status"""

        print("\nChecking verification status...")

        for attempt in range(max_attempts):
            time.sleep(3)  # Wait between checks

            try:
                params = {
                    "apikey": self.api_key or "",
                    "module": "contract",
                    "action": "checkverifystatus",
                    "guid": guid,
                }

                response = requests.get(self.api_url, params=params)
                result = response.json()

                if result.get("status") == "1":
                    if result.get("result") == "Pass - Verified":
                        explorer_url = f"{self.chain_config['explorer_url']}/address/{contract_address}#code"

                        print(f"\n✓ Verification successful!")
                        print(f"\nView on explorer:")
                        print(f"  {explorer_url}")

                        return {
                            "status": "success",
                            "message": "Verified",
                            "explorer_url": explorer_url,
                        }

                elif result.get("status") == "0":
                    # Check if it's still pending
                    if "Pending" in result.get("result", ""):
                        print(f"  Attempt {attempt + 1}/{max_attempts}: Still pending...")
                        continue
                    else:
                        # Verification failed
                        error_msg = result.get("result", "Unknown error")
                        print(f"\n✗ Verification failed: {error_msg}")

                        return {
                            "status": "failed",
                            "message": error_msg,
                        }

            except Exception as e:
                print(f"  Error checking status: {e}")

        # Timeout
        print(f"\n⚠ Verification timeout after {max_attempts} attempts")
        print(f"   Check status manually on explorer")

        return {
            "status": "timeout",
            "message": "Verification timed out",
        }

    def verify_from_deployment(self, deployment_file: Path) -> Dict:
        """Verify all contracts from deployment log"""

        print(f"\nLoading deployment from: {deployment_file}")

        with open(deployment_file, "r") as f:
            deployment = yaml.safe_load(f)

        chain_name = deployment["deployment_info"]["chain"]
        contracts = deployment["contracts"]

        print(f"\nChain: {chain_name}")
        print(f"Contracts to verify: {len(contracts)}")

        results = {}

        for contract_name, contract_info in contracts.items():
            address = contract_info["address"]
            contract_type = contract_info.get("contract_type", "")

            # Determine Vyper contract name
            if "blueprint" in contract_name.lower():
                vyper_name = "Refuel"
            elif "factory" in contract_name.lower():
                vyper_name = "RefuelFactory"

                # Get constructor args (blueprint address)
                blueprint_address = contract_info.get("blueprint_address", "")
                if blueprint_address:
                    # Encode constructor args
                    from eth_abi import encode

                    constructor_args = encode(["address"], [blueprint_address]).hex()
                else:
                    constructor_args = None
            else:
                print(f"\n⚠ Skipping unknown contract: {contract_name}")
                continue

            # Verify contract
            result = self.verify_contract(
                address,
                vyper_name,
                constructor_args=constructor_args if "factory" in contract_name.lower() else None,
            )

            results[contract_name] = result

            # Update deployment log with verification status
            deployment.setdefault("verification", {})[contract_name] = result

        # Save updated deployment log
        with open(deployment_file, "w") as f:
            yaml.dump(deployment, f, default_flow_style=False, sort_keys=False)

        print(f"\n✓ Updated deployment log: {deployment_file}")

        return results


def main():
    """Main verification function"""
    import argparse

    parser = argparse.ArgumentParser(description="Verify FXSwap Refuel contracts")
    parser.add_argument(
        "--deployment",
        type=str,
        help="Path to deployment YAML file",
    )
    parser.add_argument(
        "--contract",
        type=str,
        help="Contract address to verify",
    )
    parser.add_argument(
        "--chain",
        type=str,
        help="Chain name (required if using --contract)",
    )
    parser.add_argument(
        "--name",
        type=str,
        help="Contract name (Refuel or RefuelFactory, required if using --contract)",
    )
    parser.add_argument(
        "--constructor-args",
        type=str,
        help="Constructor arguments (hex encoded)",
    )

    args = parser.parse_args()

    try:
        if args.deployment:
            # Verify from deployment file
            deployment_file = Path(args.deployment)

            if not deployment_file.exists():
                print(f"✗ Deployment file not found: {deployment_file}")
                sys.exit(1)

            with open(deployment_file, "r") as f:
                deployment = yaml.safe_load(f)

            chain_name = deployment["deployment_info"]["chain"]
            verifier = ContractVerifier(chain_name)
            results = verifier.verify_from_deployment(deployment_file)

            # Print summary
            print("\n" + "=" * 60)
            print("VERIFICATION SUMMARY")
            print("=" * 60)

            for contract_name, result in results.items():
                status = result["status"]
                emoji = "✓" if status == "success" else "✗" if status == "failed" else "⚠"
                print(f"{emoji} {contract_name}: {result['message']}")

            print("=" * 60)

        elif args.contract and args.chain and args.name:
            # Verify single contract
            verifier = ContractVerifier(args.chain)
            result = verifier.verify_contract(
                args.contract,
                args.name,
                constructor_args=args.constructor_args,
            )

            if result["status"] == "success":
                print("\n✓ Verification complete")
                sys.exit(0)
            else:
                print(f"\n✗ Verification failed: {result['message']}")
                sys.exit(1)

        else:
            parser.print_help()
            print("\n✗ Either --deployment or (--contract, --chain, --name) must be provided")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n✗ Verification cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Verification failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
