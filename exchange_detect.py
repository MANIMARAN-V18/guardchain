import os
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("ETHERSCAN_API_KEY")
BASE_URL = "https://api.etherscan.io/v2/api"


# Known exchange wallet addresses (a small starter list for demo purposes)
# In a real system, this would come from a larger threat-intel database
KNOWN_EXCHANGES = {
    "0xdfd5293d8e347dfe59e90efd55b2956a1343963d": "Binance 16",
    "0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be": "Binance (Exchange)",
    "0x28c6c06298d514db089934071355e5743bf21d60": "Binance 14",
    "0x21a31ee1afc51d94c2efccaa2092ad1028285549": "Binance 15",
    "0x503828976d22510aad0201ac7ec88293211d23da": "Coinbase 1",
    "0xddfabcdc4d8ffc6d5beaf154f18b778f892a0740": "Coinbase 2",
}


def is_known_exchange(address):
    """Check if this address matches our known exchange list."""
    return KNOWN_EXCHANGES.get(address.lower())


def count_unique_senders(address, sample_size=50):
    """
    Look at recent incoming transactions to this address.
    Count how many DIFFERENT wallets sent money to it.
    A high number suggests this is likely an exchange deposit wallet.
    """
    params = {
        "chainid": 1,
        "module": "account",
        "action": "txlist",
        "address": address,
        "startblock": 0,
        "endblock": 99999999,
        "page": 1,
        "offset": sample_size,
        "sort": "desc",
        "apikey": API_KEY
    }
    response = requests.get(BASE_URL, params=params)
    data = response.json()

    if data.get("status") != "1":
        return 0

    txs = data.get("result", [])
    incoming = [tx for tx in txs if tx["to"].lower() == address.lower()]
    unique_senders = set(tx["from"].lower() for tx in incoming)

    return len(unique_senders)


def looks_like_exchange(address, threshold=15):
    """
    Returns True if this wallet has many unique senders in a small sample,
    suggesting it's likely an exchange deposit address rather than a personal wallet.
    """
    unique_count = count_unique_senders(address)
    return unique_count >= threshold, unique_count
def check_exchange(address):
    """
    Master function: checks known list first (more reliable),
    falls back to heuristic if not in the known list.
    Returns a dict with the verdict and reasoning.
    """
    label = is_known_exchange(address)
    if label:
        return {
            "is_exchange": True,
            "method": "known_label",
            "label": label
        }

    is_exchange, count = looks_like_exchange(address)
    return {
        "is_exchange": is_exchange,
        "method": "heuristic",
        "unique_senders": count
    }


if __name__ == "__main__":
    test_address = "0xDFd5293D8e347dFe59E90eFd55b2956a1343963d"
    result = check_exchange(test_address)
    print(result)