import os
from json import dumps
from coinbase.rest import RESTClient
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Load API keys from environment variables
API_KEY = os.getenv("COINBASE_API_KEY")
API_SECRET = os.getenv("COINBASE_API_SECRET")


def test_api_connection():
    """
    Initializes the Coinbase REST client and fetches account data to test API
    connectivity.
    """
    print("--- Attempting to connect to Coinbase API ---")

    # 1. Validate that API keys are set
    if not API_KEY or "YOUR_API_KEY_HERE" in API_KEY:
        print("\nERROR: COINBASE_API_KEY is not set in the .env file.")
        print("Please paste your credentials into the .env file and try again.")
        return

    print("API keys loaded from .env file.")

    try:
        # 2. Initialize the client
        client = RESTClient(api_key=API_KEY, api_secret=API_SECRET)
        print("RESTClient initialized successfully.")

        # 3. Make the API call to get accounts
        print("Fetching accounts...\n")
        accounts_response = client.get_accounts()

        # 4. Print the successful response
        print("--- SUCCESS: Connection to Coinbase API is working! ---")
        print("API Response:")
        # Use the built-in to_dict() method for clean printing
        print(dumps(accounts_response.to_dict(), indent=2))

    except Exception as e:
        # 5. Handle and print any errors
        print("\n--- FAILURE: An error occurred while connecting to the API. ---")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Details: {e}")
        print("\nPlease check the following:")
        print("  - Are your API keys correct and active?")
        print("  - Do the keys have the required permissions ('wallet:accounts:read')?")
        print("  - Is your internet connection working?")


if __name__ == "__main__":
    test_api_connection()
