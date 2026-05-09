# X Speed Test Bot

A small Python script that runs an internet speed test and posts a snarky X update when download performance is 25% or more below the advertised speed.

## Files

- `speedbot.py` - main bot script
- `config.example.json` - sample configuration file
- `requirements.txt` - Python dependencies

## Installation

1. Create a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install the dependencies:

   ```bash
   pip install -r requirements.txt
   ```

## Configuration

You can provide values in a JSON config file and/or via command-line arguments. CLI arguments override values in the config file.

Example config file:

```json
{
  "x_username": "your_x_username",
  "x_password": "your_x_password",
  "x_handle": "@your_x_handle",
  "isp_name": "Example ISP",
  "isp_handle": "@ExampleISP",
  "advertised_download_mbps": 500,
  "advertised_upload_mbps": 50,
  "x_consumer_key": "YOUR_CONSUMER_KEY",
  "x_consumer_secret": "YOUR_CONSUMER_SECRET",
  "x_access_token": "YOUR_ACCESS_TOKEN",
  "x_access_secret": "YOUR_ACCESS_SECRET"
}
```

> Note: X no longer supports direct username/password authentication through the API. You still may include `x_username` and `x_password` for compatibility, but actual posting requires X API credentials.

## Usage

Run with a config file:

```bash
python speedbot.py --config config.json
```

Override values on the command line:

```bash
python speedbot.py --config config.json --advertised-download-mbps 500 --x-handle @mydevhandle --x-access-token ABC --x-access-secret XYZ
```

Dry-run mode (prints the tweet instead of posting):

```bash
python speedbot.py --config config.json --dry-run
```

## What it does

- Runs a speed test using the `speedtest-cli` Python library if available, or the Ookla CLI fallback.
- Compares the measured download speed against the advertised download speed.
- If download performance is 25% or more below advertised, constructs a snarky post and publishes it to X.

## Notes

- `advertised_upload_mbps` is optional. If provided, the script will include upload performance in the generated message.
- X posting requires valid API credentials: `x_consumer_key`, `x_consumer_secret`, `x_access_token`, and `x_access_secret`.
