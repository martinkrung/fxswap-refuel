#!/bin/bash

# install.sh - Installation script for FXSwap Refuel Contract dependencies

set -e  # Exit on error

echo "=========================================="
echo "FXSwap Refuel Contract - Dependency Setup"
echo "=========================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed. Please install Python 3.8 or later."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✓ Found Python $PYTHON_VERSION"

# Check if uv is available, otherwise use pip
if command -v uv &> /dev/null; then
    echo "✓ Using uv for package management"
    USE_UV=true

    # Create virtual environment with uv
    if [ ! -d ".venv" ]; then
        echo "Creating virtual environment with uv..."
        uv venv
        echo "✓ Virtual environment created"
    else
        echo "✓ Virtual environment already exists"
    fi

    # Activate virtual environment
    echo "Activating virtual environment..."
    source .venv/bin/activate

    # Install dependencies
    echo "Installing dependencies with uv..."
    uv pip install web3>=6.0.0 eth-utils>=2.0.0 eth-abi>=4.0.0 requests
    uv pip install vyper>=0.4.3
    uv pip install pytest>=7.4.0 titanoboa>=0.2.0

else
    echo "✓ Using pip for package management"
    USE_UV=false

    # Check if pip is installed
    if ! command -v pip &> /dev/null && ! command -v pip3 &> /dev/null; then
        echo "Error: pip is not installed. Please install pip."
        exit 1
    fi

    # Use pip3 if available, otherwise pip
    PIP_CMD="pip3"
    if ! command -v pip3 &> /dev/null; then
        PIP_CMD="pip"
    fi

    echo "✓ Found pip"

    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
        echo "✓ Virtual environment created"
    else
        echo "✓ Virtual environment already exists"
    fi

    # Activate virtual environment
    echo "Activating virtual environment..."
    source venv/bin/activate

    echo "✓ Virtual environment activated"
    echo ""

    # Upgrade pip
    echo "Upgrading pip..."
    python -m pip install --upgrade pip -q
    echo "✓ pip upgraded"
    echo ""

    # Install core dependencies
    echo "Installing core dependencies..."
    pip install -q vyper>=0.4.3
    pip install -q eth-abi>=4.0.0
    pip install -q eth-utils>=2.0.0
    pip install -q web3>=6.0.0
    pip install -q requests

    echo "✓ Core dependencies installed"
    echo ""

    # Install testing dependencies
    echo "Installing testing dependencies..."
    pip install -q pytest>=7.4.0
    pip install -q titanoboa>=0.2.0

    echo "✓ Testing dependencies installed"
fi

echo ""

# Verify installations
echo "Verifying installations..."
echo ""

# Check Vyper
VYPER_VERSION=$(vyper --version 2>&1 | head -n 1)
echo "  Vyper: $VYPER_VERSION"

# Check pytest
PYTEST_VERSION=$(pytest --version | head -n 1)
echo "  Pytest: $PYTEST_VERSION"

# Check web3
PYTHON_CMD="python -c"
WEB3_VERSION=$($PYTHON_CMD "import web3; print(f'web3.py {web3.__version__}')" 2>/dev/null || echo "web3.py installed")
echo "  $WEB3_VERSION"

# Check titanoboa
BOA_VERSION=$($PYTHON_CMD "import boa; print(f'titanoboa {boa.__version__}')" 2>/dev/null || echo "titanoboa installed")
echo "  $BOA_VERSION"

echo ""
echo "=========================================="
echo "✓ All dependencies installed successfully!"
echo "=========================================="
echo ""

if [ "$USE_UV" = true ]; then
    echo "To activate the virtual environment, run:"
    echo "  source .venv/bin/activate"
else
    echo "To activate the virtual environment, run:"
    echo "  source venv/bin/activate"
fi

echo ""
echo "To compile contracts, run:"
echo "  vyper contracts/Refuel.vy"
echo "  vyper contracts/RefuelFactory.vy"
echo ""
echo "To run tests, run:"
echo "  pytest tests/ -v"
echo ""
echo "To deactivate the virtual environment, run:"
echo "  deactivate"
echo ""
