// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title FXSwap Refuel Factory (Mock for Interface Generation)
 * @notice Mock contract with all public function signatures - no logic implemented
 * @dev Use this to generate interfaces for scaffold-eth 2
 */
contract RefuelFactory {
    // Events
    event RefuelDeployed(
        address indexed refuel_contract,
        address indexed owner,
        address indexed fee_recipient,
        uint256 timestamp
    );
    event BlueprintUpdated(address old_blueprint, address indexed new_blueprint, uint256 timestamp);
    event OwnershipTransferred(address indexed previous_owner, address indexed new_owner);
    event FeesWithdrawn(
        address indexed token,
        address indexed recipient,
        uint256 amount,
        uint256 timestamp
    );

    // Public state variable getters
    function owner() public view returns (address) {
        return address(0);
    }

    function blueprint() public view returns (address) {
        return address(0);
    }

    function deployment_count() public view returns (uint256) {
        return 0;
    }

    function deployments(uint256 deployment_id) public view returns (address) {
        return address(0);
    }

    // External functions
    function deploy_refuel(address owner_address, address fee_recipient_address) public returns (address) {
        return address(0);
    }

    function deploy_refuel_simple(address owner_address) public returns (address) {
        return address(0);
    }

    function update_blueprint(address new_blueprint) public {
        // Mock - no logic
    }

    function withdraw_fees(address token, address recipient, uint256 amount) public {
        // Mock - no logic
    }

    function withdraw_all_fees(address token, address recipient) public {
        // Mock - no logic
    }

    function transfer_ownership(address new_owner) public {
        // Mock - no logic
    }

    function get_deployment(uint256 deployment_id) public view returns (address) {
        return address(0);
    }

    function get_fee_balance(address token) public view returns (uint256) {
        return 0;
    }
}
