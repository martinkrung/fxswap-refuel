# Example contract how to refuel a pool with 5% TVL 

## Installation

Use our installation script to set up everything automatically:

```bash
chmod +x install.sh
./install.sh
```

## Usage

After installation, make sure your virtual environment is activated
and load the environment variables from .env_ethereum:

```bash
cp env_example .env_ethereum
```

```bash
source .venv/bin/activate
source .env_ethereum
```

run with:

```bash
scripts/refuel_zchf.py
```

Default is SIM, change in script to execute on-chain
```
#set to True to fork the network
#set to False to use the actual network
SIM = True
```
