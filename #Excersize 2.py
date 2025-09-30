# Excersize 2.2
import requests
import json
import logging
from time import sleep

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_cat_fact():
    """
    Fetches a single random cat fact from catfact.ninja API.
    Returns:
        str: The cat fact, or None if an error occurs.
    """
    url = "https://catfact.ninja/fact"
    
    try:
        response = requests.get(url, timeout=5)  # timeout for network issues
        response.raise_for_status()  # Raises HTTPError for bad responses
        data = response.json()
        return data.get('fact')
    
    except requests.exceptions.HTTPError as http_err:
        logging.error(f"HTTP error occurred: {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        logging.error(f"Connection error occurred: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        logging.error(f"Timeout error occurred: {timeout_err}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
    
    return None

def get_multiple_cat_facts(n=5):
    """
    Fetches multiple cat facts and returns them as a list.
    Args:
        n (int): Number of cat facts to fetch.
    Returns:
        list: List of cat facts.
    """
    facts = []
    for i in range(n):
        fact = get_cat_fact()
        if fact:
            logging.info(f"Fetched fact {i+1}: {fact}")
            facts.append(fact)
        else:
            logging.warning(f"Failed to fetch fact {i+1}")
        sleep(1)  # polite delay to avoid spamming API
    return facts

def save_facts_to_json(facts, filename="cat_facts.json"):
    """
    Saves the list of cat facts to a JSON file.
    """
    try:
        with open(filename, "w") as f:
            json.dump(facts, f, indent=4)
        logging.info(f"Cat facts saved to {filename}")
    except Exception as e:
        logging.error(f"Failed to save cat facts: {e}")

def load_facts_from_json(filename="cat_facts.json"):
    """
    Loads cat facts from a JSON file.
    Returns:
        list: List of cat facts, or an empty list if error occurs.
    """
    try:
        with open(filename, "r") as f:
            facts = json.load(f)
        logging.info(f"Loaded {len(facts)} cat facts from {filename}")
        return facts
    except Exception as e:
        logging.error(f"Failed to load cat facts: {e}")
        return []

# Main execution
if __name__ == "__main__":
    # Step 1: Fetch and save facts
    cat_facts = get_multiple_cat_facts(5)
    save_facts_to_json(cat_facts)

    # Step 2: Open/read facts from JSON
    loaded_facts = load_facts_from_json()
    print("\nCat facts from JSON file:")
    for i, fact in enumerate(loaded_facts, 1):
        print(f"{i}. {fact}")


# Excersize 2.3
import requests
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_public_holidays(country_code="US", year=2024):
    """
    Get public holidays for a specific country and year
    Uses Nager.Date API (free, no key required)
    """
    url = f"https://date.nager.at/api/v3/PublicHolidays/{year}/{country_code}"
    
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()  # Raises an exception for bad status codes
        
        holidays = response.json()
        return holidays
    
    except requests.exceptions.RequestException as e:
        logging.error(f"Request failed for {country_code}: {e}")
        return None

def extract_names_and_dates(holidays):
    """
    Extract only the 'name' and 'date' of each holiday.
    """
    return [{'name': h['name'], 'date': h['date']} for h in holidays]

def summarize_holiday_counts(countries, year=2024):
    """
    Get holidays for multiple countries and summarize counts.
    """
    summary = {}
    for country in countries:
        holidays = get_public_holidays(country, year)
        if holidays:
            holidays_info = extract_names_and_dates(holidays)
            summary[country] = {
                'count': len(holidays_info),
                'holidays': holidays_info
            }
            logging.info(f"{country} has {len(holidays_info)} public holidays in {year}")
        else:
            summary[country] = {'count': 0, 'holidays': []}
            logging.warning(f"No data for {country}")
    return summary

# Test with 3 countries
countries_to_test = ['US', 'CA', 'GB']
holiday_summary = summarize_holiday_counts(countries_to_test, 2024)

# Print results
for country, data in holiday_summary.items():
    print(f"\n{country} ({data['count']} holidays):")
    for h in data['holidays']:
        print(f"{h['date']}: {h['name']}")
