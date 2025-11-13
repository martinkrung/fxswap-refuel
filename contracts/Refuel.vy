#pragma version ^0.4.3

"""
@title FXSwap Refuel Contract
@notice Handles refueling of FXSwap pools by withdrawing LP tokens and re-adding them as donations
@dev This contract manages LP token-based refueling with donation share threshold checks
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
    timestamp: uint256

event OwnershipTransferred:
    previous_owner: indexed(address)
    new_owner: indexed(address)

# State variables
owner: public(address)
pool: public(address)
refuel_lp_amount: public(uint256)  # LP token amount to refuel (not USD based)
donation_share_threshold: public(uint256)  # Threshold for donation share (in basis points, e.g., 9500 = 95%)

# Constants
PRECISION: constant(uint256) = 10000  # Basis points precision (100% = 10000)

@deploy
def __init__():
    """
    @notice Contract constructor
    """
    self.owner = msg.sender
    self.donation_share_threshold = 9500  # Default: 95% (donations must be at least 95% of minted LP)

@external
def set_pool(new_pool: address):
    """
    @notice Set the FXSwap pool address
    @param new_pool Address of the FXSwap pool contract
    """
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
    assert msg.sender == self.owner, "Only owner"
    assert threshold <= PRECISION, "Threshold cannot exceed 100%"

    self.donation_share_threshold = threshold
    log ThresholdSet(threshold=threshold, timestamp=block.timestamp)

@external
def refuel() -> uint256:
    """
    @notice Execute the refuel operation
    @dev Withdraws LP tokens from pool and re-adds them as donation
    @return The amount of LP tokens donated
    """
    assert self.pool != empty(address), "Pool not set"
    assert self.refuel_lp_amount > 0, "Refuel amount not set"

    # Get LP token contract
    lp_token: IERC20 = IERC20(self.pool)

    # Check this contract has enough LP tokens
    lp_balance: uint256 = staticcall lp_token.balanceOf(self)
    assert lp_balance >= self.refuel_lp_amount, "Insufficient LP tokens"

    # Step 1: Remove liquidity to get underlying tokens
    pool: IFXSwapPool = IFXSwapPool(self.pool)
    min_amounts: uint256[2] = [0, 0]  # No slippage protection for simplicity

    token_amounts: uint256[2] = extcall pool.remove_liquidity(
        self.refuel_lp_amount,
        min_amounts,
        self
    )

    # Step 2: Calculate expected LP tokens from re-adding (with donation)
    calc_lp_donated: uint256 = staticcall pool.calc_token_amount(token_amounts, True)

    # Step 3: Check donation share threshold
    # donation_share = calc_lp_donated / refuel_lp_amount
    # We want: (calc_lp_donated * PRECISION) / refuel_lp_amount >= donation_share_threshold
    donation_share: uint256 = (calc_lp_donated * PRECISION) // self.refuel_lp_amount
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
        timestamp=block.timestamp
    )

    return donated_lp

@external
def withdraw_lp_tokens(amount: uint256):
    """
    @notice Withdraw LP tokens from the contract
    @param amount Amount of LP tokens to withdraw
    """
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
    assert msg.sender == self.owner, "Only owner"
    success: bool = extcall IERC20(token).transfer(msg.sender, amount)
    assert success, "Transfer failed"

@external
def transfer_ownership(new_owner: address):
    """
    @notice Transfer ownership of the contract
    @param new_owner Address of the new owner
    """
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
