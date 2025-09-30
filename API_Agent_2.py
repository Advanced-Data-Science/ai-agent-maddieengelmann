"""
Spotify Data Collection AI Agent

This agent collects Spotify artist and track data using client credentials flow.
It includes:
- Configuration management (env vars and JSON config)
- Intelligent collection (search + artist details)
- Data quality assessment (basic field checks)
- Adaptive delay strategy (backoff on failures)
- Respectful collection (API rate limit handling + logging)

Prepare a config file with collection_params like max requests, delay, and targets.
"""

import os
import requests
import base64
import json
import time
import logging
import platform
import sys
from datetime import datetime

class SpotifyAIDataAgent:
    def __init__(self, config_file="config.json"):
        self.config = self.load_config(config_file)
        self.setup_logging()
        self.token = None
        self.token_expiry = None
        self.collected_artists = []
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'quality_passed': 0
        }
        self.delay = self.config.get("collection_settings", {}).get("min_delay_seconds", 1.0)

        # Load client ID and secret from config first, then env vars
        self.client_id = self.config.get("client_id") or os.getenv("SPOTIFY_CLIENT_ID")
        self.client_secret = self.config.get("client_secret") or os.getenv("SPOTIFY_CLIENT_SECRET")

        if not self.client_id or not self.client_secret:
            raise ValueError("Missing Spotify CLIENT_ID or CLIENT_SECRET in config.json or environment.")

    def load_config(self, config_file):
        try:
            with open(config_file, "r") as f:
                return json.load(f)
        except Exception as e:
            raise FileNotFoundError(f"Could not load config {config_file}: {e}")

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s]: %(message)s',
            handlers=[
                logging.FileHandler("spotify_agent.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def get_access_token(self):
        token_url = "https://accounts.spotify.com/api/token"
        auth_str = f"{self.client_id}:{self.client_secret}"
        b64_auth_str = base64.b64encode(auth_str.encode()).decode()

        headers = {
            "Authorization": f"Basic {b64_auth_str}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {"grant_type": "client_credentials"}

        try:
            response = requests.post(token_url, headers=headers, data=data)
            response.raise_for_status()
            token_data = response.json()
            self.token = token_data["access_token"]
            self.token_expiry = datetime.now().timestamp() + token_data["expires_in"]
            self.logger.info("Obtained new Spotify Access Token.")
        except Exception as e:
            self.logger.error(f"Failed to obtain access token: {e}")
            raise

    def ensure_token_valid(self):
        if self.token is None or datetime.now().timestamp() > self.token_expiry - 60:
            self.get_access_token()

    def search_artist(self, artist_name):
        self.ensure_token_valid()
        search_url = "https://api.spotify.com/v1/search"
        headers = {"Authorization": f"Bearer {self.token}"}
        params = {"q": artist_name, "type": "artist", "limit": 1}

        try:
            response = requests.get(search_url, headers=headers, params=params)
            self.stats['total_requests'] += 1
            response.raise_for_status()
            self.stats['successful_requests'] += 1

            data = response.json()
            items = data.get("artists", {}).get("items", [])
            if not items:
                self.logger.warning(f"No artist found for query '{artist_name}'")
                self.stats['failed_requests'] += 1
                return None

            return items[0]

        except Exception as e:
            self.logger.error(f"Error searching artist '{artist_name}': {e}")
            self.stats['failed_requests'] += 1
            self.adapt_delay()
            return None

    def get_artist_details(self, artist_id):
        self.ensure_token_valid()
        artist_url = f"https://api.spotify.com/v1/artists/{artist_id}"
        headers = {"Authorization": f"Bearer {self.token}"}

        try:
            response = requests.get(artist_url, headers=headers)
            self.stats['total_requests'] += 1
            response.raise_for_status()
            self.stats['successful_requests'] += 1
            return response.json()
        except Exception as e:
            self.logger.error(f"Error getting artist details for id '{artist_id}': {e}")
            self.stats['failed_requests'] += 1
            self.adapt_delay()
            return None

    def assess_data_quality(self, artist_data):
        return bool(
            artist_data
            and artist_data.get("name")
            and artist_data.get("genres")
            and len(artist_data.get("genres")) > 0
        )

    def adapt_delay(self):
        self.delay = min(self.delay * 2, 10)
        self.logger.warning(f"Increasing delay to {self.delay} seconds due to API errors.")
        time.sleep(self.delay)

    def respectful_delay(self):
        import random
        jitter = random.uniform(0.8, 1.2)
        actual_delay = self.delay * jitter
        self.logger.info(f"Sleeping for {actual_delay:.2f} seconds before next request.")
        time.sleep(actual_delay)
        if self.delay > self.config.get("collection_settings", {}).get("min_delay_seconds", 1.0):
            self.delay = max(
                self.delay * 0.9,
                self.config["collection_settings"]["min_delay_seconds"]
            )

    def run(self):
        self.logger.info("Spotify AI Data Agent started.")
        self.logger.info(f"Access token: {self.token}")
        artist_names = self.config.get("artists_to_search", [])
        self.logger.info(f"Config keys: {list(self.config.keys())}")
        if not artist_names:
            self.logger.info(f"----- artist empty")
        for artist_name in artist_names:
            self.logger.info(f"Processing artist: {artist_name}")
            artist_basic = self.search_artist(artist_name)
            if not artist_basic:
                self.logger.info(f"Processing artist empty: {artist_name}")
                continue

            artist_id = artist_basic.get("id")
            artist_details = self.get_artist_details(artist_id)
            if not artist_details:
                continue

            if self.assess_data_quality(artist_details):
                self.collected_artists.append({
                    "id": artist_id,
                    "name": artist_details.get("name"),
                    "genres": artist_details.get("genres"),
                    "spotify_url": artist_details.get("external_urls", {}).get("spotify"),
                    "popularity": artist_details.get("popularity"),
                    "followers": artist_details.get("followers", {}).get("total")
                })
                self.stats['quality_passed'] += 1
                self.logger.info(f"Collected data for artist {artist_name}")
            else:
                self.logger.warning(f"Data quality check failed for artist {artist_name}")

            self.respectful_delay()

        self.logger.info("Data collection complete.")
        self.save_data()
        self.generate_report()
        self.save_metadata()  # NEW metadata output

    def save_data(self):
        output_dir = self.config.get("data_paths", {}).get("raw_data", ".")
        filename = f"spotify_artists_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(output_dir, filename)
        os.makedirs(output_dir, exist_ok=True)

        with open(filepath, "w") as f:
            json.dump(self.collected_artists, f, indent=2)

        self.logger.info(f"Saved collected artist data to {filepath}")

    def generate_report(self):
        output_dir = self.config.get("data_paths", {}).get("reports", ".")
        os.makedirs(output_dir, exist_ok=True)
        report_file = os.path.join(output_dir, "collection_report.txt")

        total = self.stats['total_requests']
        success = self.stats['successful_requests']
        failed = self.stats['failed_requests']
        quality = self.stats['quality_passed']

        with open(report_file, "w") as f:
            f.write("Spotify AI Data Collection Report\n")
            f.write(f"Date: {datetime.now().isoformat()}\n\n")
            f.write(f"Total API Requests: {total}\n")
            f.write(f"Successful API Requests: {success}\n")
            f.write(f"Failed API Requests: {failed}\n")
            f.write(f"Artists Passed Quality Check: {quality}\n")
            f.write(f"Collected Artist Count: {len(self.collected_artists)}\n")

        self.logger.info(f"Generated collection report at {report_file}")

    def save_metadata(self):
        """Save metadata about this collection run into a JSON file."""
        output_dir = self.config.get("data_paths", {}).get("metadata", ".")
        os.makedirs(output_dir, exist_ok=True)

        metadata = {
            "run_time": datetime.now().isoformat(),
            "python_version": sys.version,
            "platform": platform.platform(),
            "config_used": {
                "artists_to_search": self.config.get("artists_to_search", []),
                "collection_settings": self.config.get("collection_settings", {}),
                "data_paths": self.config.get("data_paths", {}),
            },
            "stats": self.stats,
            "collected_count": len(self.collected_artists)
        }

        filename = f"metadata_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, "w") as f:
            json.dump(metadata, f, indent=2)

        self.logger.info(f"Saved metadata to {filepath}")


if __name__ == "__main__":
    agent = SpotifyAIDataAgent()
    agent.run()
