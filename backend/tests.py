##### tests.py #####
"""
Script to test the DCP AI API:
    python tests.py company <company_name>
    python tests.py founder <founder_name>
"""

import requests
import sys
import time
import logging
from typing import Optional

# Base API URL
BASE_URL = "http://127.0.0.1:8000"

# Configure logging
logging.basicConfig(
    filename="test_results.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

def send_request(url: str, retries: int = 3, delay: float = 2.0) -> Optional[dict]:
    """
    Sends a GET request with retries in case of failure.
    
    :param url: API endpoint to call.
    :param retries: Number of times to retry in case of failure.
    :param delay: Delay (in seconds) between retries.
    :return: JSON response or None if request fails.
    """
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                logging.error(f"ERROR {response.status_code} on {url}: {response.text}")
        except requests.exceptions.RequestException as e:
            logging.error(f"Request failed: {e}")
        
        print(f"Retrying ({attempt+1}/{retries}) in {delay} seconds...")
        time.sleep(delay)

    return None  # Return None if all retries fail

def test_company_search(company_name: str, verbose: bool = False):
    """
    Tests the /companies/{company_name} endpoint.
    
    :param company_name: The name of the company to search.
    :param verbose: If True, prints full API response.
    """
    print(f"\nSearching for company: {company_name}")
    url = f"{BASE_URL}/companies/{company_name}"
    data = send_request(url)

    if data:
        print(f"Success! Found company: {data.get('name', 'Unknown')}")
        print(f"Duke Affiliation: {data.get('duke_affiliated', 'Unknown')}")
        print(f"Founders: {', '.join(data.get('founders', [])) or 'None'}")
        logging.info(f"Company Search - {company_name}: {data}")
        if verbose:
            print("\nFull Response:", data)
    else:
        print(f"ERROR: Company '{company_name}' not found or request failed.")

def test_founder_search(founder_name: str, verbose: bool = False):
    """
    Tests the /founders/{founder_name} endpoint.
    
    :param founder_name: The name of the founder to search.
    :param verbose: If True, prints full API response.
    """
    print(f"\nSearching for founder: {founder_name}")
    url = f"{BASE_URL}/founders/{founder_name}"
    data = send_request(url)

    if data:
        print(f"Success! Found founder: {data.get('name', 'Unknown')}")
        print(f"Duke Affiliation: {data.get('duke_affiliation', 'Unknown')}")
        print(f"Companies: {', '.join(data.get('companies', [])) or 'None'}")
        logging.info(f"Founder Search - {founder_name}: {data}")
        if verbose:
            print("\n Full Response:", data)
    else:
        print(f"ERROR: Founder '{founder_name}' not found or request failed.")

def main():
    """
    Entry point for running tests.
    Usage:
        python tests.py company <company_name>
        python tests.py founder <founder_name>
    """
    if len(sys.argv) < 3:
        print("Usage:")
        print("  python tests.py company <company_name>")
        print("  python tests.py founder <founder_name>")
        sys.exit(1)

    mode = sys.argv[1].lower()
    name = " ".join(sys.argv[2:])  # Support multi-word names

    if mode == "company":
        test_company_search(name, verbose=True)
    elif mode == "founder":
        test_founder_search(name, verbose=True)
    else:
        print(f"Unknown mode: {mode}. Use 'company' or 'founder'.")

if __name__ == "__main__":
    print("Running DCP AI API Tests...")
    main()
    print("\nAll tests completed!")
