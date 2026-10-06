"""Entry point with the same shape as the official hyperion-starter: `uv run main.py` or `python main.py`
starts the agent on port 8000 with POST /chat."""

from steward.app import main

if __name__ == "__main__":
    main()
