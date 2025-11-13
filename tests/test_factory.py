"""
Tests for the RefuelFactory and Refuel blueprint contracts
"""
import pytest
import boa


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

# Mock FXSwap Pool contract (same as before)
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
    self.totalSupply = 1000 * 10**18

@external
def remove_liquidity(amount: uint256, min_amounts: uint256[2], receiver: address) -> uint256[2]:
    token0_amount: uint256 = (self.balances[0] * amount) // self.totalSupply
    token1_amount: uint256 = (self.balances[1] * amount) // self.totalSupply

    self.balances[0] -= token0_amount
    self.balances[1] -= token1_amount
    self.totalSupply -= amount

    extcall IERC20(self.coins[0]).transfer(receiver, token0_amount)
    extcall IERC20(self.coins[1]).transfer(receiver, token1_amount)

    self.lp_balances[msg.sender] -= amount

    return [token0_amount, token1_amount]

@external
def add_liquidity(amounts: uint256[2], min_mint_amount: uint256, receiver: address, donation: bool) -> uint256:
    extcall IERC20(self.coins[0]).transferFrom(msg.sender, self, amounts[0])
    extcall IERC20(self.coins[1]).transferFrom(msg.sender, self, amounts[1])

    lp_amount: uint256 = self._calc_token_amount_internal(amounts, True)

    self.balances[0] += amounts[0]
    self.balances[1] += amounts[1]
    self.totalSupply += lp_amount

    if donation:
        self.lp_balances[empty(address)] += lp_amount
    else:
        self.lp_balances[receiver] += lp_amount

    return lp_amount

@internal
@view
def _calc_token_amount_internal(amounts: uint256[2], is_deposit: bool) -> uint256:
    if self.totalSupply == 0:
        return 0

    lp0: uint256 = 0
    lp1: uint256 = 0

    if self.balances[0] > 0:
        lp0 = (amounts[0] * self.totalSupply) // self.balances[0]
    if self.balances[1] > 0:
        lp1 = (amounts[1] * self.totalSupply) // self.balances[1]

    if is_deposit:
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
def factory_owner():
    return boa.env.generate_address()


@pytest.fixture
def refuel_owner():
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

    pool = boa.loads(MOCK_POOL, token0.address, token1.address, initial_balance0, initial_balance1)

    token0.mint(pool.address, initial_balance0)
    token1.mint(pool.address, initial_balance1)

    return pool


@pytest.fixture
def blueprint():
    """Deploy Refuel blueprint"""
    return boa.load("contracts/Refuel.vy")


@pytest.fixture
def factory(blueprint, factory_owner):
    """Deploy RefuelFactory"""
    with boa.env.prank(factory_owner):
        return boa.load("contracts/RefuelFactory.vy", blueprint.address)


class TestFactoryDeployment:
    """Test factory deployment and initialization"""

    def test_factory_owner(self, factory, factory_owner):
        """Test that factory owner is set correctly"""
        assert factory.owner() == factory_owner

    def test_factory_blueprint(self, factory, blueprint):
        """Test that blueprint is set correctly"""
        assert factory.blueprint() == blueprint.address

    def test_initial_deployment_count(self, factory):
        """Test that deployment count starts at zero"""
        assert factory.deployment_count() == 0


class TestRefuelDeployment:
    """Test Refuel contract deployment via factory"""

    def test_deploy_refuel_simple(self, factory, refuel_owner):
        """Test deploying Refuel contract with factory as fee recipient"""
        refuel_address = factory.deploy_refuel_simple(refuel_owner)

        assert refuel_address != "0x0000000000000000000000000000000000000000"
        assert factory.deployment_count() == 1
        assert factory.get_deployment(0) == refuel_address

    def test_deploy_refuel_custom_fee_recipient(self, factory, refuel_owner, user):
        """Test deploying Refuel contract with custom fee recipient"""
        refuel_address = factory.deploy_refuel(refuel_owner, user)

        assert refuel_address != "0x0000000000000000000000000000000000000000"

        # Load the deployed contract
        refuel = boa.load_partial("contracts/Refuel.vy").at(refuel_address)

        assert refuel.owner() == refuel_owner
        assert refuel.fee_recipient() == user
        assert refuel.initialized() == True

    def test_deploy_multiple_refuel_contracts(self, factory, refuel_owner, user):
        """Test deploying multiple Refuel contracts"""
        refuel1 = factory.deploy_refuel_simple(refuel_owner)
        refuel2 = factory.deploy_refuel(user, factory.address)

        assert refuel1 != refuel2
        assert factory.deployment_count() == 2
        assert factory.get_deployment(0) == refuel1
        assert factory.get_deployment(1) == refuel2


class TestRefuelFunctionality:
    """Test Refuel contract functionality when deployed via factory"""

    def test_initialize_prevents_reinitialization(self, factory, refuel_owner):
        """Test that initialized contracts cannot be reinitialized"""
        refuel_address = factory.deploy_refuel_simple(refuel_owner)
        refuel = boa.load_partial("contracts/Refuel.vy").at(refuel_address)

        with boa.reverts("Already initialized"):
            with boa.env.prank(refuel_owner):
                refuel.initialize(refuel_owner, factory.address)

    def test_refuel_with_fee(self, factory, refuel_owner, pool, token0, token1):
        """Test refuel operation with fee deduction"""
        # Deploy refuel contract
        refuel_address = factory.deploy_refuel_simple(refuel_owner)
        refuel = boa.load_partial("contracts/Refuel.vy").at(refuel_address)

        # Setup
        refuel_amount = 10 * 10**18

        with boa.env.prank(refuel_owner):
            refuel.set_pool(pool.address)
            refuel.set_refuel_amount(refuel_amount)
            refuel.set_donation_threshold(9000)  # Lower threshold for test

        # Give refuel contract LP tokens
        pool.mint_lp(refuel_address, refuel_amount)

        # Get initial factory balance
        initial_factory_balance = pool.balanceOf(factory.address)

        # Execute refuel
        with boa.env.prank(refuel_owner):
            donated_lp = refuel.refuel()

        # Check that fee was paid to factory
        expected_fee = (refuel_amount * 500) // 10000  # 5% fee
        assert pool.balanceOf(factory.address) == initial_factory_balance + expected_fee

        # Check that refuel happened
        assert donated_lp > 0


class TestFactoryFeeManagement:
    """Test factory fee collection and withdrawal"""

    def test_withdraw_fees(self, factory, factory_owner, pool, refuel_owner, user):
        """Test withdrawing fees from factory"""
        # Deploy and setup refuel contract
        refuel_address = factory.deploy_refuel_simple(refuel_owner)
        refuel = boa.load_partial("contracts/Refuel.vy").at(refuel_address)

        refuel_amount = 10 * 10**18

        with boa.env.prank(refuel_owner):
            refuel.set_pool(pool.address)
            refuel.set_refuel_amount(refuel_amount)
            refuel.set_donation_threshold(9000)

        # Give refuel contract LP tokens and execute refuel
        pool.mint_lp(refuel_address, refuel_amount)

        with boa.env.prank(refuel_owner):
            refuel.refuel()

        # Get factory fee balance
        factory_balance = factory.get_fee_balance(pool.address)
        assert factory_balance > 0

        # Withdraw fees
        initial_user_balance = pool.balanceOf(user)

        with boa.env.prank(factory_owner):
            factory.withdraw_all_fees(pool.address, user)

        # Check user received fees
        assert pool.balanceOf(user) == initial_user_balance + factory_balance
        assert factory.get_fee_balance(pool.address) == 0

    def test_withdraw_fees_unauthorized(self, factory, user, pool):
        """Test that non-owner cannot withdraw fees"""
        with boa.reverts("Only owner"):
            with boa.env.prank(user):
                factory.withdraw_fees(pool.address, user, 100)

    def test_withdraw_all_fees_unauthorized(self, factory, user, pool):
        """Test that non-owner cannot withdraw all fees"""
        with boa.reverts("Only owner"):
            with boa.env.prank(user):
                factory.withdraw_all_fees(pool.address, user)


class TestFactoryBlueprintUpdate:
    """Test blueprint update functionality"""

    def test_update_blueprint(self, factory, factory_owner):
        """Test updating blueprint address"""
        new_blueprint = boa.env.generate_address()

        with boa.env.prank(factory_owner):
            factory.update_blueprint(new_blueprint)

        assert factory.blueprint() == new_blueprint

    def test_update_blueprint_unauthorized(self, factory, user):
        """Test that non-owner cannot update blueprint"""
        new_blueprint = boa.env.generate_address()

        with boa.reverts("Only owner"):
            with boa.env.prank(user):
                factory.update_blueprint(new_blueprint)


class TestFactoryOwnership:
    """Test factory ownership transfer"""

    def test_transfer_ownership(self, factory, factory_owner, user):
        """Test transferring factory ownership"""
        with boa.env.prank(factory_owner):
            factory.transfer_ownership(user)

        assert factory.owner() == user

    def test_transfer_ownership_unauthorized(self, factory, user):
        """Test that non-owner cannot transfer ownership"""
        new_owner = boa.env.generate_address()

        with boa.reverts("Only owner"):
            with boa.env.prank(user):
                factory.transfer_ownership(new_owner)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
