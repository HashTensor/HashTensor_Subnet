# Bittensor Kaspa GPU Validator

A modular validator for a Bittensor subnet that tracks GPU miners from a Kaspa mining pool using Prometheus metrics and pluggable hotkey <-> worker mapping sources.

## Features
- Periodically fetches miner metrics from a Prometheus endpoint (Kaspa Stratum Bridge)
- Maintains a mapping of Bittensor hotkeys to Kaspa worker names (pluggable sources: REST, JSON, EVM, GitHub)
- Computes normalized ratings per hotkey based on real-time metrics
- Sends ratings to Bittensor via Yuma Consensus
- Modular, extensible, and testable design

## Project Structure
```
src/
  metrics.py         # Prometheus client and parser
  mapping.py         # Hotkey <-> worker mapping management
  rating.py          # Rating computation logic
  validator.py       # Main validation logic
  config.py          # Config loader (YAML/JSON)
  main.py            # Async entry point with scheduler and CLI
  interfaces/
    rest.py          # REST API mapping source
    github.py        # GitHub mapping source
    evm.py           # EVM contract mapping source
    json_file.py     # JSON file mapping source

tests/               # Placeholder unit tests
requirements.txt     # Python dependencies
README.md            # Project overview
```

## Quick Start
1. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
2. Prepare a config file (YAML or JSON).
3. Run the validator:
   ```sh
   python -m src.main --config path/to/config.yaml
   ```

## License
MIT 

## Database Initialization

To initialize the SQLite database schema for hotkey <-> worker mapping, run:

```python
from src.interfaces.sqlite import metadata, engine
metadata.create_all(engine)
```

## Running the FastAPI Server

Start the FastAPI app (e.g. with uvicorn):

```sh
uvicorn src.main:app --reload
```

## Requirements
- Python 3.8+
- See requirements.txt for dependencies (includes FastAPI and SQLAlchemy) 