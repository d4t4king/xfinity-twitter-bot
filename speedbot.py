#!/usr/bin/env python3
"""Run a speed test and notify X if download performance is well below advertised speed."""

import argparse
import json
import os
import subprocess
import sys
from typing import Any, Dict, Optional

MIN_DROP_PERCENT_DEFAULT = 25
CONFIG_DEFAULT_PATH = "config.json"


def load_json_config(path: str) -> Dict[str, Any]:
    """Load a JSON configuration file if it exists."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Configuration file not found: {path}")

    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Speed test X poster: post if download speed is 25% or more below advertised."
    )
    parser.add_argument("--config", default=CONFIG_DEFAULT_PATH, help="Path to JSON config file.")
    parser.add_argument("--x-username", help="Developer X username (for config compatibility).")
    parser.add_argument("--x-password", help="Developer X password (for config compatibility).")
    parser.add_argument("--x-handle", help="X account handle used for posting or mention.")
    parser.add_argument("--isp-name", help="ISP display name.")
    parser.add_argument("--isp-handle", help="ISP X account handle to tag.")
    parser.add_argument("--advertised-download-mbps", type=float, help="Advertised download speed in Mbps.")
    parser.add_argument("--advertised-upload-mbps", type=float, help="Advertised upload speed in Mbps.")
    parser.add_argument("--x-consumer-key", help="X API consumer key.")
    parser.add_argument("--x-consumer-secret", help="X API consumer secret.")
    parser.add_argument("--x-access-token", help="X API access token.")
    parser.add_argument("--x-access-secret", help="X API access token secret.")
    parser.add_argument("--x-bearer-token", help="X API bearer token (optional for tweepy Client).")
    parser.add_argument(
        "--min-drop-percent",
        type=float,
        default=MIN_DROP_PERCENT_DEFAULT,
        help="Minimum download drop percent to trigger a post.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Do not actually post to X; print the tweet instead.")
    return parser.parse_args()


def resolve_config(args: argparse.Namespace) -> Dict[str, Any]:
    config = {}
    if args.config:
        try:
            config = load_json_config(args.config)
        except FileNotFoundError:
            if args.config != CONFIG_DEFAULT_PATH:
                raise
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Invalid JSON in {args.config}: {exc}") from exc

    merged = {
        "x_username": args.x_username or config.get("x_username"),
        "x_password": args.x_password or config.get("x_password"),
        "x_handle": args.x_handle or config.get("x_handle"),
        "isp_name": args.isp_name or config.get("isp_name"),
        "isp_handle": args.isp_handle or config.get("isp_handle"),
        "advertised_download_mbps": args.advertised_download_mbps or config.get("advertised_download_mbps"),
        "advertised_upload_mbps": args.advertised_upload_mbps or config.get("advertised_upload_mbps"),
        "x_consumer_key": args.x_consumer_key or config.get("x_consumer_key"),
        "x_consumer_secret": args.x_consumer_secret or config.get("x_consumer_secret"),
        "x_access_token": args.x_access_token or config.get("x_access_token"),
        "x_access_secret": args.x_access_secret or config.get("x_access_secret"),
        "x_bearer_token": args.x_bearer_token or config.get("x_bearer_token"),
        "min_drop_percent": args.min_drop_percent,
        "dry_run": args.dry_run,
    }
    return merged


def bits_per_second_to_mbps(bits: float) -> float:
    return bits / 1_000_000.0


def run_speedtest() -> Dict[str, Optional[float]]:
    try:
        import speedtest

        tester = speedtest.Speedtest()
        tester.get_best_server()
        download_bps = tester.download()
        upload_bps = None
        try:
            upload_bps = tester.upload(pre_allocate=False)
        except Exception:
            upload_bps = None

        return {
            "download_mbps": bits_per_second_to_mbps(download_bps),
            "upload_mbps": bits_per_second_to_mbps(upload_bps) if upload_bps else None,
        }
    except ImportError:
        pass

    try:
        completed = subprocess.run(
            ["speedtest", "--accept-license", "--accept-gdpr", "--format=json"],
            capture_output=True,
            text=True,
            check=True,
        )
        payload = json.loads(completed.stdout)
        return {
            "download_mbps": bits_per_second_to_mbps(payload["download"]),
            "upload_mbps": bits_per_second_to_mbps(payload.get("upload")) if payload.get("upload") else None,
        }
    except FileNotFoundError as exc:
        raise RuntimeError(
            "speedtest-cli is not installed and Ookla speedtest CLI was not found in PATH. "
            "Install speedtest-cli or Ookla speedtest and retry."
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"Speed test command failed: {exc.stderr.strip() or exc.stdout.strip()}"
        ) from exc


def build_snarky_message(
    isp_name: str,
    isp_handle: Optional[str],
    advertised_download: float,
    actual_download: float,
    advertised_upload: Optional[float],
    actual_upload: Optional[float],
) -> str:
    isp_mention = isp_handle or isp_name
    headline = (
        f"Hey {isp_mention}, you advertise {advertised_download:.0f} Mbps down "
        f"but delivered only {actual_download:.1f} Mbps."
    )
    if advertised_upload and actual_upload is not None:
        headline += (
            f" Upload was {actual_upload:.1f} Mbps vs advertised {advertised_upload:.0f} Mbps."
        )
    punchline = "This is NOT the service you sell."
    return f"{headline} {punchline}"


def validate_post_credentials(config: Dict[str, Any]) -> bool:
    return bool(
        config.get("x_consumer_key")
        and config.get("x_consumer_secret")
        and config.get("x_access_token")
        and config.get("x_access_secret")
    )


def post_to_x(tweet_text: str, config: Dict[str, Any]) -> None:
    try:
        import tweepy
    except ImportError as exc:
        raise RuntimeError(
            "Tweepy is required to post to X. Install dependencies from requirements.txt."
        ) from exc

    if not validate_post_credentials(config):
        raise RuntimeError(
            "Missing X API credentials. Provide x_consumer_key, x_consumer_secret, "
            "x_access_token and x_access_secret via config or command line."
        )

    client = tweepy.Client(
        consumer_key=config["x_consumer_key"],
        consumer_secret=config["x_consumer_secret"],
        access_token=config["x_access_token"],
        access_token_secret=config["x_access_secret"],
        bearer_token=config.get("x_bearer_token"),
        wait_on_rate_limit=True,
    )
    response = client.create_tweet(text=tweet_text)
    if getattr(response, "errors", None):
        raise RuntimeError(f"X publish failed: {response.errors}")


def main() -> int:
    args = parse_args()
    config = resolve_config(args)

    if config["advertised_download_mbps"] is None:
        raise RuntimeError("Advertised download speed is required via config or command line.")

    isp_name = config.get("isp_name") or "Your ISP"
    advertised_download = float(config["advertised_download_mbps"])
    advertised_upload = (
        float(config["advertised_upload_mbps"]) if config.get("advertised_upload_mbps") else None
    )

    print("Running speed test...")
    results = run_speedtest()
    actual_download = results["download_mbps"]
    actual_upload = results.get("upload_mbps")
    print(
        f"Measured download: {actual_download:.1f} Mbps",
        f"Measured upload: {actual_upload:.1f} Mbps" if actual_upload is not None else "Upload test unavailable",
    )

    drop_percent = 100.0 - (actual_download / advertised_download * 100.0)
    print(f"Advertised download: {advertised_download:.0f} Mbps")
    print(f"Download drop: {drop_percent:.1f}%")

    if drop_percent < config["min_drop_percent"]:
        print(
            f"No post required: download is not {config['min_drop_percent']}% or more below advertised."
        )
        return 0

    tweet_text = build_snarky_message(
        isp_name=isp_name,
        isp_handle=config.get("isp_handle"),
        advertised_download=advertised_download,
        actual_download=actual_download,
        advertised_upload=advertised_upload,
        actual_upload=actual_upload,
    )

    if config["dry_run"]:
        print("Dry run mode enabled. Tweet content:")
        print(tweet_text)
        return 0

    print("Posting to X...")
    post_to_x(tweet_text, config)
    print("Posted successfully.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
