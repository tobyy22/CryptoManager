import requests
import logging

COINGECKO_PRICE_URL = "https://api.coingecko.com/api/v3/simple/price"
COINGECKO_LIST_URL = "https://api.coingecko.com/api/v3/coins/list"


def is_coin_supported_in_coingecko(symbol: str) -> bool:
    try:
        response = requests.get(COINGECKO_LIST_URL)
        if response.status_code != 200:
            raise Exception("Failed to fetch coin list from CoinGecko")

        coin_list = response.json()
        coin_ids = {coin["id"] for coin in coin_list}

        return symbol.lower() in coin_ids

    except Exception as e:
        logging.error(f"Error checking coin existence: {e}")
        return False


def get_crypto_prices(symbols: list, currency: str = "usd") -> dict:
    symbols = ",".join(symbols)
    response = requests.get(
        COINGECKO_PRICE_URL, params={"ids": symbols, "vs_currencies": currency}
    )

    if response.status_code != 200:
        raise Exception("Failed to fetch prices from CoinGecko")

    logging.info(response.json())

    return response.json()
