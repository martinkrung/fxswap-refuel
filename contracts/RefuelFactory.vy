#pragma version ^0.4.3

"""
@title FXSwap Refuel Factory
@notice Factory contract for deploying Refuel contract instances from a blueprint
@dev Allows efficient deployment of multiple Refuel contracts with customizable fee recipients
"""

from ethereum.ercs import IERC20

# Interface for the Refuel blueprint
interface IRefuel:
    def initialize(owner_address: address, fee_recipient_address: address): nonpayable
    def owner() -> address: view
    def fee_recipient() -> address: view

# Events
event RefuelDeployed:
    refuel_contract: indexed(address)
    owner: indexed(address)
    fee_recipient: indexed(address)
    timestamp: uint256

event BlueprintUpdated:
    old_blueprint: address
    new_blueprint: indexed(address)
    timestamp: uint256

event OwnershipTransferred:
    previous_owner: indexed(address)
    new_owner: indexed(address)

event FeesWithdrawn:
    token: indexed(address)
    recipient: indexed(address)
    amount: uint256
    timestamp: uint256

# State variables
owner: public(address)
blueprint: public(address)
deployment_count: public(uint256)
deployments: public(HashMap[uint256, address])  # deployment_id => refuel_contract_address

@deploy
def __init__(blueprint_address: address):
    """
    @notice Initialize the factory with a blueprint address
    @param blueprint_address Address of the deployed Refuel blueprint
    """
    assert blueprint_address != empty(address), "Invalid blueprint address"

    self.owner = msg.sender
    self.blueprint = blueprint_address
    self.deployment_count = 0

@internal
def _deploy_refuel_internal(owner_address: address, fee_recipient_address: address) -> address:
    """Internal function to deploy Refuel contract"""
    assert owner_address != empty(address), "Invalid owner address"

    # Use factory as fee recipient if zero address is provided
    actual_fee_recipient: address = fee_recipient_address
    if fee_recipient_address == empty(address):
        actual_fee_recipient = self

    # Deploy new Refuel contract from blueprint
    refuel_contract: address = create_from_blueprint(self.blueprint)

    # Initialize the deployed contract
    extcall IRefuel(refuel_contract).initialize(owner_address, actual_fee_recipient)

    # Store deployment
    self.deployments[self.deployment_count] = refuel_contract
    self.deployment_count += 1

    log RefuelDeployed(
        refuel_contract=refuel_contract,
        owner=owner_address,
        fee_recipient=actual_fee_recipient,
        timestamp=block.timestamp
    )

    return refuel_contract

@external
def deploy_refuel(owner_address: address, fee_recipient_address: address) -> address:
    """
    @notice Deploy a new Refuel contract instance from the blueprint
    @param owner_address Address that will own the deployed Refuel contract
    @param fee_recipient_address Address to receive fees (default: this factory)
    @return Address of the deployed Refuel contract
    """
    return self._deploy_refuel_internal(owner_address, fee_recipient_address)

@external
def deploy_refuel_simple(owner_address: address) -> address:
    """
    @notice Deploy a new Refuel contract with factory as fee recipient
    @param owner_address Address that will own the deployed Refuel contract
    @return Address of the deployed Refuel contract
    """
    return self._deploy_refuel_internal(owner_address, empty(address))

@external
def update_blueprint(new_blueprint: address):
    """
    @notice Update the blueprint address (owner only)
    @param new_blueprint Address of the new blueprint
    """
    assert msg.sender == self.owner, "Only owner"
    assert new_blueprint != empty(address), "Invalid blueprint address"

    old_blueprint: address = self.blueprint
    self.blueprint = new_blueprint

    log BlueprintUpdated(
        old_blueprint=old_blueprint,
        new_blueprint=new_blueprint,
        timestamp=block.timestamp
    )

@external
def withdraw_fees(token: address, recipient: address, amount: uint256):
    """
    @notice Withdraw collected fees (owner only)
    @param token Token address to withdraw (LP token or other ERC20)
    @param recipient Address to send the fees to
    @param amount Amount to withdraw
    @dev Factory owner can send collected fees to any address
    """
    assert msg.sender == self.owner, "Only owner"
    assert recipient != empty(address), "Invalid recipient"
    assert amount > 0, "Amount must be positive"

    success: bool = extcall IERC20(token).transfer(recipient, amount)
    assert success, "Transfer failed"

    log FeesWithdrawn(
        token=token,
        recipient=recipient,
        amount=amount,
        timestamp=block.timestamp
    )

@external
def withdraw_all_fees(token: address, recipient: address):
    """
    @notice Withdraw all collected fees for a token (owner only)
    @param token Token address to withdraw
    @param recipient Address to send the fees to
    """
    assert msg.sender == self.owner, "Only owner"
    assert recipient != empty(address), "Invalid recipient"

    balance: uint256 = staticcall IERC20(token).balanceOf(self)
    assert balance > 0, "No fees to withdraw"

    success: bool = extcall IERC20(token).transfer(recipient, balance)
    assert success, "Transfer failed"

    log FeesWithdrawn(
        token=token,
        recipient=recipient,
        amount=balance,
        timestamp=block.timestamp
    )

@external
def transfer_ownership(new_owner: address):
    """
    @notice Transfer ownership of the factory
    @param new_owner Address of the new owner
    """
    assert msg.sender == self.owner, "Only owner"
    assert new_owner != empty(address), "Invalid new owner"

    old_owner: address = self.owner
    self.owner = new_owner

    log OwnershipTransferred(previous_owner=old_owner, new_owner=new_owner)

@view
@external
def get_deployment(deployment_id: uint256) -> address:
    """
    @notice Get the address of a deployed Refuel contract
    @param deployment_id The deployment ID
    @return Address of the Refuel contract
    """
    return self.deployments[deployment_id]

@view
@external
def get_fee_balance(token: address) -> uint256:
    """
    @notice Get the fee balance for a specific token
    @param token Token address
    @return Balance of fees collected
    """
    return staticcall IERC20(token).balanceOf(self)
