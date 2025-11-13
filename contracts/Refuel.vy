#pragma version ^0.4.3

"""
@title FXSwap Refuel Contract (Blueprint)
@notice Handles refueling of FXSwap pools by withdrawing LP tokens and re-adding them as donations
@dev This contract is designed to be deployed as a blueprint for efficient factory deployment
"""

from ethereum.ercs import IERC20

# Interfaces
interface IFXSwapPool:
    def balances(i: uint256) -> uint256: view
    def totalSupply() -> uint256: view
    def coins(i: uint256) -> address: view
    def remove_liquidity(
        amount: uint256,
        min_amounts: uint256[2],
        receiver: address
    ) -> uint256[2]: nonpayable
    def add_liquidity(
        amounts: uint256[2],
        min_mint_amount: uint256,
        receiver: address,
        donation: bool
    ) -> uint256: nonpayable
    def calc_token_amount(amounts: uint256[2], is_deposit: bool) -> uint256: view

# Events
event Initialized:
    owner: indexed(address)
    timestamp: uint256

event PoolSet:
    pool: indexed(address)
    timestamp: uint256

event RefuelAmountSet:
    amount: uint256
    timestamp: uint256

event ThresholdSet:
    threshold: uint256
    timestamp: uint256

event Refueled:
    lp_amount: uint256
    token0_amount: uint256
    token1_amount: uint256
    donated_lp: uint256
    fee_amount: uint256
    timestamp: uint256

event FeePaid:
    recipient: indexed(address)
    amount: uint256
    timestamp: uint256

event OwnershipTransferred:
    previous_owner: indexed(address)
    new_owner: indexed(address)

# State variables
initialized: public(bool)
owner: public(address)
pool: public(address)
refuel_lp_amount: public(uint256)  # LP token amount to refuel (not USD based)
donation_share_threshold: public(uint256)  # Threshold for donation share (in basis points, e.g., 9500 = 95%)
fee_bps: public(uint256)  # Fee in basis points (e.g., 500 = 5%)
fee_recipient: public(address)  # Address to receive fees

# Constants
PRECISION: constant(uint256) = 10000  # Basis points precision (100% = 10000)
DEFAULT_THRESHOLD: constant(uint256) = 9500  # Default: 95%
DEFAULT_FEE_BPS: constant(uint256) = 500  # Default fee: 5%

@deploy
def __init__():
    """
    @notice Blueprint constructor - does minimal initialization
    @dev Actual initialization happens via initialize() function
    """
    # Blueprint contracts should not initialize state in __init__
    # This allows the factory to deploy multiple instances efficiently
    pass

@external
def initialize(owner_address: address, fee_recipient_address: address):
    """
    @notice Initialize the contract (called by factory after deployment)
    @param owner_address Address of the contract owner
    @param fee_recipient_address Address to receive fees (can be factory or other address)
    @dev Can only be called once
    """
    assert not self.initialized, "Already initialized"
    assert owner_address != empty(address), "Invalid owner address"
    assert fee_recipient_address != empty(address), "Invalid fee recipient address"

    self.initialized = True
    self.owner = owner_address
    self.donation_share_threshold = DEFAULT_THRESHOLD
    self.fee_bps = DEFAULT_FEE_BPS
    self.fee_recipient = fee_recipient_address

    log Initialized(owner=owner_address, timestamp=block.timestamp)

@external
def set_pool(new_pool: address):
    """
    @notice Set the FXSwap pool address
    @param new_pool Address of the FXSwap pool contract
    """
    assert self.initialized, "Not initialized"
    assert msg.sender == self.owner, "Only owner"
    assert new_pool != empty(address), "Invalid pool address"

    self.pool = new_pool
    log PoolSet(pool=new_pool, timestamp=block.timestamp)

@external
def set_refuel_amount(lp_amount: uint256):
    """
    @notice Set the LP token amount to use for refueling
    @param lp_amount Amount of LP tokens (not USD based)
    """
    assert self.initialized, "Not initialized"
    assert msg.sender == self.owner, "Only owner"
    assert lp_amount > 0, "Amount must be positive"

    self.refuel_lp_amount = lp_amount
    log RefuelAmountSet(amount=lp_amount, timestamp=block.timestamp)

@external
def set_donation_threshold(threshold: uint256):
    """
    @notice Set the donation share threshold (in basis points)
    @param threshold Minimum donation share required (e.g., 9500 = 95%)
    """
    assert self.initialized, "Not initialized"
    assert msg.sender == self.owner, "Only owner"
    assert threshold <= PRECISION, "Threshold cannot exceed 100%"

    self.donation_share_threshold = threshold
    log ThresholdSet(threshold=threshold, timestamp=block.timestamp)

@external
def refuel() -> uint256:
    """
    @notice Execute the refuel operation with fee deduction
    @dev Withdraws LP tokens from pool, takes fee, and re-adds remaining as donation
    @return The amount of LP tokens donated (after fee)
    """
    assert self.initialized, "Not initialized"
    assert self.pool != empty(address), "Pool not set"
    assert self.refuel_lp_amount > 0, "Refuel amount not set"

    # Get LP token contract
    lp_token: IERC20 = IERC20(self.pool)

    # Check this contract has enough LP tokens
    lp_balance: uint256 = staticcall lp_token.balanceOf(self)
    assert lp_balance >= self.refuel_lp_amount, "Insufficient LP tokens"

    # Calculate fee amount from LP tokens
    fee_amount: uint256 = (self.refuel_lp_amount * self.fee_bps) // PRECISION
    lp_amount_after_fee: uint256 = self.refuel_lp_amount - fee_amount

    # Transfer fee to fee recipient
    if fee_amount > 0:
        success: bool = extcall lp_token.transfer(self.fee_recipient, fee_amount)
        assert success, "Fee transfer failed"
        log FeePaid(recipient=self.fee_recipient, amount=fee_amount, timestamp=block.timestamp)

    # Step 1: Remove liquidity to get underlying tokens (using amount after fee)
    pool: IFXSwapPool = IFXSwapPool(self.pool)
    min_amounts: uint256[2] = [0, 0]  # No slippage protection for simplicity

    token_amounts: uint256[2] = extcall pool.remove_liquidity(
        lp_amount_after_fee,
        min_amounts,
        self
    )

    # Step 2: Calculate expected LP tokens from re-adding (with donation)
    calc_lp_donated: uint256 = staticcall pool.calc_token_amount(token_amounts, True)

    # Step 3: Check donation share threshold
    # donation_share = calc_lp_donated / lp_amount_after_fee
    # We want: (calc_lp_donated * PRECISION) / lp_amount_after_fee >= donation_share_threshold
    donation_share: uint256 = (calc_lp_donated * PRECISION) // lp_amount_after_fee
    assert donation_share >= self.donation_share_threshold, "Donation share below threshold"

    # Step 4: Approve pool to spend tokens
    token0: address = staticcall pool.coins(0)
    token1: address = staticcall pool.coins(1)

    extcall IERC20(token0).approve(self.pool, token_amounts[0])
    extcall IERC20(token1).approve(self.pool, token_amounts[1])

    # Step 5: Add liquidity as donation (LP tokens minted to zero address)
    min_mint: uint256 = calc_lp_donated  # Expect at least what we calculated
    donated_lp: uint256 = extcall pool.add_liquidity(
        token_amounts,
        min_mint,
        empty(address),  # Receiver is zero address (burned)
        True  # donation = True
    )

    log Refueled(
        lp_amount=self.refuel_lp_amount,
        token0_amount=token_amounts[0],
        token1_amount=token_amounts[1],
        donated_lp=donated_lp,
        fee_amount=fee_amount,
        timestamp=block.timestamp
    )

    return donated_lp

@external
def withdraw_lp_tokens(amount: uint256):
    """
    @notice Withdraw LP tokens from the contract
    @param amount Amount of LP tokens to withdraw
    """
    assert self.initialized, "Not initialized"
    assert msg.sender == self.owner, "Only owner"
    assert self.pool != empty(address), "Pool not set"

    lp_token: IERC20 = IERC20(self.pool)
    success: bool = extcall lp_token.transfer(msg.sender, amount)
    assert success, "Transfer failed"

@external
def withdraw_tokens(token: address, amount: uint256):
    """
    @notice Withdraw any ERC20 tokens from the contract
    @param token Token address to withdraw
    @param amount Amount to withdraw
    """
    assert self.initialized, "Not initialized"
    assert msg.sender == self.owner, "Only owner"
    success: bool = extcall IERC20(token).transfer(msg.sender, amount)
    assert success, "Transfer failed"

@external
def transfer_ownership(new_owner: address):
    """
    @notice Transfer ownership of the contract
    @param new_owner Address of the new owner
    """
    assert self.initialized, "Not initialized"
    assert msg.sender == self.owner, "Only owner"
    assert new_owner != empty(address), "Invalid new owner"

    old_owner: address = self.owner
    self.owner = new_owner
    log OwnershipTransferred(previous_owner=old_owner, new_owner=new_owner)

@view
@external
def get_lp_balance() -> uint256:
    """
    @notice Get the LP token balance of this contract
    @return LP token balance
    """
    if self.pool == empty(address):
        return 0
    return staticcall IERC20(self.pool).balanceOf(self)

@view
@external
def calculate_donation_share() -> uint256:
    """
    @notice Calculate the current donation share (in basis points)
    @dev Returns the ratio of LP tokens that would be donated
    @return Donation share in basis points
    """
    assert self.pool != empty(address), "Pool not set"
    assert self.refuel_lp_amount > 0, "Refuel amount not set"

    pool: IFXSwapPool = IFXSwapPool(self.pool)

    # Get current pool state
    balance0: uint256 = staticcall pool.balances(0)
    balance1: uint256 = staticcall pool.balances(1)
    total_supply: uint256 = staticcall pool.totalSupply()

    # Calculate proportional token amounts
    token0_amount: uint256 = (balance0 * self.refuel_lp_amount) // total_supply
    token1_amount: uint256 = (balance1 * self.refuel_lp_amount) // total_supply

    # Calculate LP tokens that would be minted
    amounts: uint256[2] = [token0_amount, token1_amount]
    calc_lp: uint256 = staticcall pool.calc_token_amount(amounts, True)

    # Calculate donation share in basis points
    return (calc_lp * PRECISION) // self.refuel_lp_amount
