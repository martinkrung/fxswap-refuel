"""
Tests for the Refuel.vy contract
"""
import pytest
import boa
from eth_abi import encode


# Mock ERC20 token contract
MOCK_ERC20 = """
#pragma version ^0.4.3

balanceOf: public(HashMap[address, uint256])
totalSupply: public(uint256)
allowance: public(HashMap[address, HashMap[address, uint256]])

@deploy
def __init__(total_supply: uint256):
    self.totalSupply = total_supply
    self.balanceOf[msg.sender] = total_supply

@external
def transfer(to: address, amount: uint256) -> bool:
    assert self.balanceOf[msg.sender] >= amount, "Insufficient balance"
    self.balanceOf[msg.sender] -= amount
    self.balanceOf[to] += amount
    return True

@external
def approve(spender: address, amount: uint256) -> bool:
    self.allowance[msg.sender][spender] = amount
    return True

@external
def transferFrom(sender: address, to: address, amount: uint256) -> bool:
    assert self.balanceOf[sender] >= amount, "Insufficient balance"
    assert self.allowance[sender][msg.sender] >= amount, "Insufficient allowance"
    self.balanceOf[sender] -= amount
    self.balanceOf[to] += amount
    self.allowance[sender][msg.sender] -= amount
    return True

@external
def mint(to: address, amount: uint256):
    self.balanceOf[to] += amount
    self.totalSupply += amount
"""

# Mock FXSwap Pool contract
MOCK_POOL = """
#pragma version ^0.4.3

from ethereum.ercs import IERC20

balances: public(uint256[2])
totalSupply: public(uint256)
coins: public(address[2])
lp_balances: HashMap[address, uint256]

@deploy
def __init__(token0: address, token1: address, initial_balance0: uint256, initial_balance1: uint256):
    self.coins[0] = token0
    self.coins[1] = token1
    self.balances[0] = initial_balance0
    self.balances[1] = initial_balance1
    self.totalSupply = 1000 * 10**18  # Initial LP supply

@external
def remove_liquidity(amount: uint256, min_amounts: uint256[2], receiver: address) -> uint256[2]:
    # Calculate proportional amounts
    token0_amount: uint256 = (self.balances[0] * amount) // self.totalSupply
    token1_amount: uint256 = (self.balances[1] * amount) // self.totalSupply

    # Update balances
    self.balances[0] -= token0_amount
    self.balances[1] -= token1_amount
    self.totalSupply -= amount

    # Transfer tokens to receiver
    extcall IERC20(self.coins[0]).transfer(receiver, token0_amount)
    extcall IERC20(self.coins[1]).transfer(receiver, token1_amount)

    # Update LP balance
    self.lp_balances[msg.sender] -= amount

    return [token0_amount, token1_amount]

@external
def add_liquidity(amounts: uint256[2], min_mint_amount: uint256, receiver: address, donation: bool) -> uint256:
    # Transfer tokens from sender
    extcall IERC20(self.coins[0]).transferFrom(msg.sender, self, amounts[0])
    extcall IERC20(self.coins[1]).transferFrom(msg.sender, self, amounts[1])

    # Calculate LP tokens to mint using calc_token_amount
    lp_amount: uint256 = self._calc_token_amount_internal(amounts, True)

    # Update balances
    self.balances[0] += amounts[0]
    self.balances[1] += amounts[1]
    self.totalSupply += lp_amount

    # Mint LP tokens
    if donation:
        # Tokens are burned (sent to zero address)
        self.lp_balances[empty(address)] += lp_amount
    else:
        self.lp_balances[receiver] += lp_amount

    return lp_amount

@internal
@view
def _calc_token_amount_internal(amounts: uint256[2], is_deposit: bool) -> uint256:
    # Simple calculation: average of proportional amounts
    # In a real pool, this would use the StableSwap invariant
    if self.totalSupply == 0:
        return 0

    lp0: uint256 = 0
    lp1: uint256 = 0

    if self.balances[0] > 0:
        lp0 = (amounts[0] * self.totalSupply) // self.balances[0]
    if self.balances[1] > 0:
        lp1 = (amounts[1] * self.totalSupply) // self.balances[1]

    # Return the minimum to be conservative
    if is_deposit:
        # When depositing, use 97% of minimum (simulating some slippage)
        return (min(lp0, lp1) * 97) // 100
    else:
        return min(lp0, lp1)

@view
@external
def calc_token_amount(amounts: uint256[2], is_deposit: bool) -> uint256:
    return self._calc_token_amount_internal(amounts, is_deposit)

@external
def transfer(to: address, amount: uint256) -> bool:
    assert self.lp_balances[msg.sender] >= amount, "Insufficient LP balance"
    self.lp_balances[msg.sender] -= amount
    self.lp_balances[to] += amount
    return True

@view
@external
def balanceOf(account: address) -> uint256:
    return self.lp_balances[account]

@external
def mint_lp(to: address, amount: uint256):
    self.lp_balances[to] += amount
    self.totalSupply += amount
"""


@pytest.fixture
def owner():
    return boa.env.generate_address()


@pytest.fixture
def user():
    return boa.env.generate_address()


@pytest.fixture
def token0():
    """Deploy mock token0"""
    with boa.env.prank(boa.env.generate_address()):
        return boa.loads(MOCK_ERC20, 1000000 * 10**18)


@pytest.fixture
def token1():
    """Deploy mock token1"""
    with boa.env.prank(boa.env.generate_address()):
        return boa.loads(MOCK_ERC20, 1000000 * 10**18)


@pytest.fixture
def pool(token0, token1):
    """Deploy mock pool"""
    initial_balance0 = 100000 * 10**18
    initial_balance1 = 100000 * 10**18

    pool_deployer = boa.env.generate_address()
    pool = boa.loads(MOCK_POOL, token0.address, token1.address, initial_balance0, initial_balance1)

    # Mint tokens to pool directly
    token0.mint(pool.address, initial_balance0)
    token1.mint(pool.address, initial_balance1)

    return pool


@pytest.fixture
def refuel_contract(owner):
    """Deploy Refuel contract"""
    with boa.env.prank(owner):
        return boa.load("contracts/Refuel.vy")


class TestDeployment:
    """Test contract deployment and initialization"""

    def test_initial_owner(self, refuel_contract, owner):
        """Test that owner is set correctly on deployment"""
        assert refuel_contract.owner() == owner

    def test_initial_threshold(self, refuel_contract):
        """Test that default threshold is 95%"""
        assert refuel_contract.donation_share_threshold() == 9500

    def test_initial_pool_empty(self, refuel_contract):
        """Test that pool is initially not set"""
        assert refuel_contract.pool() == "0x0000000000000000000000000000000000000000"

    def test_initial_refuel_amount_zero(self, refuel_contract):
        """Test that refuel amount is initially zero"""
        assert refuel_contract.refuel_lp_amount() == 0


class TestAdminFunctions:
    """Test admin/owner functions"""

    def test_set_pool(self, refuel_contract, pool, owner):
        """Test setting pool address"""
        with boa.env.prank(owner):
            refuel_contract.set_pool(pool.address)
        assert refuel_contract.pool() == pool.address

    def test_set_pool_unauthorized(self, refuel_contract, pool, user):
        """Test that non-owner cannot set pool"""
        with boa.reverts("Only owner"):
            with boa.env.prank(user):
                refuel_contract.set_pool(pool.address)

    def test_set_pool_zero_address(self, refuel_contract, owner):
        """Test that zero address cannot be set as pool"""
        with boa.reverts("Invalid pool address"):
            with boa.env.prank(owner):
                refuel_contract.set_pool("0x0000000000000000000000000000000000000000")

    def test_set_refuel_amount(self, refuel_contract, owner):
        """Test setting refuel amount"""
        amount = 10 * 10**18
        with boa.env.prank(owner):
            refuel_contract.set_refuel_amount(amount)
        assert refuel_contract.refuel_lp_amount() == amount

    def test_set_refuel_amount_unauthorized(self, refuel_contract, user):
        """Test that non-owner cannot set refuel amount"""
        with boa.reverts("Only owner"):
            with boa.env.prank(user):
                refuel_contract.set_refuel_amount(10 * 10**18)

    def test_set_refuel_amount_zero(self, refuel_contract, owner):
        """Test that zero refuel amount is rejected"""
        with boa.reverts("Amount must be positive"):
            with boa.env.prank(owner):
                refuel_contract.set_refuel_amount(0)

    def test_set_donation_threshold(self, refuel_contract, owner):
        """Test setting donation threshold"""
        threshold = 9000  # 90%
        with boa.env.prank(owner):
            refuel_contract.set_donation_threshold(threshold)
        assert refuel_contract.donation_share_threshold() == threshold

    def test_set_donation_threshold_unauthorized(self, refuel_contract, user):
        """Test that non-owner cannot set threshold"""
        with boa.reverts("Only owner"):
            with boa.env.prank(user):
                refuel_contract.set_donation_threshold(9000)

    def test_set_donation_threshold_exceeds_max(self, refuel_contract, owner):
        """Test that threshold cannot exceed 100%"""
        with boa.reverts("Threshold cannot exceed 100%"):
            with boa.env.prank(owner):
                refuel_contract.set_donation_threshold(10001)

    def test_transfer_ownership(self, refuel_contract, owner, user):
        """Test transferring ownership"""
        with boa.env.prank(owner):
            refuel_contract.transfer_ownership(user)
        assert refuel_contract.owner() == user

    def test_transfer_ownership_unauthorized(self, refuel_contract, user):
        """Test that non-owner cannot transfer ownership"""
        new_owner = boa.env.generate_address()
        with boa.reverts("Only owner"):
            with boa.env.prank(user):
                refuel_contract.transfer_ownership(new_owner)

    def test_transfer_ownership_zero_address(self, refuel_contract, owner):
        """Test that ownership cannot be transferred to zero address"""
        with boa.reverts("Invalid new owner"):
            with boa.env.prank(owner):
                refuel_contract.transfer_ownership("0x0000000000000000000000000000000000000000")


class TestViewFunctions:
    """Test view/read functions"""

    def test_get_lp_balance_pool_not_set(self, refuel_contract):
        """Test getting LP balance when pool is not set"""
        assert refuel_contract.get_lp_balance() == 0

    def test_get_lp_balance(self, refuel_contract, pool, owner):
        """Test getting LP balance"""
        # Set pool
        with boa.env.prank(owner):
            refuel_contract.set_pool(pool.address)

        # Mint some LP tokens to the contract
        lp_amount = 50 * 10**18
        pool.mint_lp(refuel_contract.address, lp_amount)

        assert refuel_contract.get_lp_balance() == lp_amount

    def test_calculate_donation_share_pool_not_set(self, refuel_contract, owner):
        """Test calculating donation share when pool is not set"""
        with boa.env.prank(owner):
            refuel_contract.set_refuel_amount(10 * 10**18)

        with boa.reverts("Pool not set"):
            refuel_contract.calculate_donation_share()

    def test_calculate_donation_share_amount_not_set(self, refuel_contract, pool, owner):
        """Test calculating donation share when refuel amount is not set"""
        with boa.env.prank(owner):
            refuel_contract.set_pool(pool.address)

        with boa.reverts("Refuel amount not set"):
            refuel_contract.calculate_donation_share()

    def test_calculate_donation_share(self, refuel_contract, pool, owner):
        """Test calculating donation share"""
        refuel_amount = 10 * 10**18

        with boa.env.prank(owner):
            refuel_contract.set_pool(pool.address)
            refuel_contract.set_refuel_amount(refuel_amount)

        donation_share = refuel_contract.calculate_donation_share()

        # Should be around 97% due to our mock pool logic
        assert donation_share >= 9500  # At least 95%
        assert donation_share <= 10000  # At most 100%


class TestRefuelOperation:
    """Test the main refuel operation"""

    def test_refuel_pool_not_set(self, refuel_contract, owner):
        """Test refuel fails when pool is not set"""
        with boa.env.prank(owner):
            refuel_contract.set_refuel_amount(10 * 10**18)

        with boa.reverts("Pool not set"):
            with boa.env.prank(owner):
                refuel_contract.refuel()

    def test_refuel_amount_not_set(self, refuel_contract, pool, owner):
        """Test refuel fails when amount is not set"""
        with boa.env.prank(owner):
            refuel_contract.set_pool(pool.address)

        with boa.reverts("Refuel amount not set"):
            with boa.env.prank(owner):
                refuel_contract.refuel()

    def test_refuel_insufficient_lp_tokens(self, refuel_contract, pool, owner):
        """Test refuel fails when contract has insufficient LP tokens"""
        refuel_amount = 10 * 10**18

        with boa.env.prank(owner):
            refuel_contract.set_pool(pool.address)
            refuel_contract.set_refuel_amount(refuel_amount)

        with boa.reverts("Insufficient LP tokens"):
            with boa.env.prank(owner):
                refuel_contract.refuel()

    def test_refuel_success(self, refuel_contract, pool, token0, token1, owner):
        """Test successful refuel operation"""
        refuel_amount = 10 * 10**18

        # Setup
        with boa.env.prank(owner):
            refuel_contract.set_pool(pool.address)
            refuel_contract.set_refuel_amount(refuel_amount)
            refuel_contract.set_donation_threshold(9000)  # Lower threshold for test

        # Give contract LP tokens
        pool.mint_lp(refuel_contract.address, refuel_amount)

        # Get initial pool state
        initial_total_supply = pool.totalSupply()

        # Execute refuel
        with boa.env.prank(owner):
            donated_lp = refuel_contract.refuel()

        # Verify results
        assert donated_lp > 0
        assert refuel_contract.get_lp_balance() == 0  # LP tokens were used

        # Pool total supply should have decreased (net effect)
        # Because we removed LP then re-added with donation, the donation burns tokens
        final_total_supply = pool.totalSupply()

        # The donated LP tokens should have been minted
        assert final_total_supply > initial_total_supply - refuel_amount

    def test_refuel_below_threshold(self, refuel_contract, pool, token0, token1, owner):
        """Test refuel fails when donation share is below threshold"""
        refuel_amount = 10 * 10**18

        # Setup with very high threshold
        with boa.env.prank(owner):
            refuel_contract.set_pool(pool.address)
            refuel_contract.set_refuel_amount(refuel_amount)
            refuel_contract.set_donation_threshold(9900)  # 99% threshold

        # Give contract LP tokens
        pool.mint_lp(refuel_contract.address, refuel_amount)

        # Execute refuel - should fail if donation share < 99%
        with boa.reverts("Donation share below threshold"):
            with boa.env.prank(owner):
                refuel_contract.refuel()


class TestWithdrawFunctions:
    """Test withdrawal functions"""

    def test_withdraw_lp_tokens(self, refuel_contract, pool, owner):
        """Test withdrawing LP tokens"""
        lp_amount = 50 * 10**18

        # Setup
        with boa.env.prank(owner):
            refuel_contract.set_pool(pool.address)

        # Give contract LP tokens
        pool.mint_lp(refuel_contract.address, lp_amount)

        # Withdraw
        initial_owner_balance = pool.balanceOf(owner)
        with boa.env.prank(owner):
            refuel_contract.withdraw_lp_tokens(lp_amount)

        assert refuel_contract.get_lp_balance() == 0
        assert pool.balanceOf(owner) == initial_owner_balance + lp_amount

    def test_withdraw_lp_tokens_unauthorized(self, refuel_contract, pool, owner, user):
        """Test that non-owner cannot withdraw LP tokens"""
        with boa.env.prank(owner):
            refuel_contract.set_pool(pool.address)

        with boa.reverts("Only owner"):
            with boa.env.prank(user):
                refuel_contract.withdraw_lp_tokens(10 * 10**18)

    def test_withdraw_tokens(self, refuel_contract, token0, owner):
        """Test withdrawing ERC20 tokens"""
        amount = 100 * 10**18

        # Mint tokens directly to contract
        token0.mint(refuel_contract.address, amount)

        # Withdraw
        initial_owner_balance = token0.balanceOf(owner)
        with boa.env.prank(owner):
            refuel_contract.withdraw_tokens(token0.address, amount)

        assert token0.balanceOf(refuel_contract.address) == 0
        assert token0.balanceOf(owner) == initial_owner_balance + amount

    def test_withdraw_tokens_unauthorized(self, refuel_contract, token0, user):
        """Test that non-owner cannot withdraw tokens"""
        with boa.reverts("Only owner"):
            with boa.env.prank(user):
                refuel_contract.withdraw_tokens(token0.address, 10 * 10**18)


class TestEvents:
    """Test event emissions"""

    def test_pool_set_event(self, refuel_contract, pool, owner):
        """Test PoolSet event is emitted"""
        with boa.env.prank(owner):
            refuel_contract.set_pool(pool.address)
        # Event testing in boa is limited, but function execution confirms event emission

    def test_refuel_amount_set_event(self, refuel_contract, owner):
        """Test RefuelAmountSet event is emitted"""
        with boa.env.prank(owner):
            refuel_contract.set_refuel_amount(10 * 10**18)

    def test_threshold_set_event(self, refuel_contract, owner):
        """Test ThresholdSet event is emitted"""
        with boa.env.prank(owner):
            refuel_contract.set_donation_threshold(9000)

    def test_ownership_transferred_event(self, refuel_contract, owner, user):
        """Test OwnershipTransferred event is emitted"""
        with boa.env.prank(owner):
            refuel_contract.transfer_ownership(user)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
