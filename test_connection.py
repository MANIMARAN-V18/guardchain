import os
import requests
from dotenv import load_dotenv

# Load the API key from .env file
load_dotenv()
API_KEY = os.getenv("ETHERSCAN_API_KEY")

# A well-known Ethereum wallet address (Vitalik Buterin's public address)
# We use this because it definitely has transactions - good for testing
WALLET_ADDRESS = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"

url = "https://api.etherscan.io/v2/api"
params = {
    "chainid": 1,          # 1 = Ethereum Mainnet
    "module": "account",
    "action": "txlist",
    "address": WALLET_ADDRESS,
    "startblock": 0,
    "endblock": 99999999,
    "page": 1,
    "offset": 5,            # only fetch 5 transactions for this test
    "sort": "desc",
    "apikey": API_KEY
}

response = requests.get(url, params=params)
data = response.json()

print("Status:", data.get("status"))
print("Message:", data.get("message"))
print("Number of transactions fetched:", len(data.get("result", [])))