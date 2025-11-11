#!/bin/bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install web3 eth-utils requests