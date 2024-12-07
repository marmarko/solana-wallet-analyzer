from time import sleep
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
import logging
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create 'outputs' folder if it doesn't exist
outputs_folder = 'outputs'
os.makedirs(outputs_folder, exist_ok=True)

# Set up logging
DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
logging.basicConfig(level=logging.DEBUG if DEBUG else logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
TRANSACTION_HISTORY_API_URL = os.getenv('TRANSACTION_HISTORY_API_URL')
ALL_TOKENS_API_URL = os.getenv('ALL_TOKENS_API_URL')
WALLET_BALANCE_API_URL = os.getenv('WALLET_BALANCE_API_URL')
NETWORK = os.getenv('NETWORK')
ACCOUNT = os.getenv('ACCOUNT')
API_KEY = os.getenv('API_KEY')

# Solana Tracker
solana_tracker_api_key = os.getenv('SOLANA_TRACKER_API_KEY')
top_traders_api_url = 'https://data.solanatracker.io/top-traders/all/'
top_traders_for_token_api_url = 'https://data.solanatracker.io/top-traders/'
wallet_details_api_url = 'https://data.solanatracker.io/wallet/'
trending_tokens_api_url = 'https://data.solanatracker.io/tokens/trending/'
wallet_pnl_api_url = 'https://data.solanatracker.io/pnl/'
token_info_api_url = 'https://data.solanatracker.io/tokens/'
trades_api_url = 'https://data.solanatracker.io/trades/'

# Shyft
shyft_api_key = os.getenv('SHYFT_API_KEY')
transaction_history_api_url = "https://api.shyft.to/sol/v1/transaction/history"

# General
do_not_check_list = ["So11111111111111111111111111111111111111112","7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs","3NZ9JMVBmGAqocybic2c7LQCJScmgsAZ6vQqTDzcqmJh","Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB","JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN"]
winrate_min = os.getenv('WINRATE_MIN')
winrate_max = os.getenv('WINRATE_MAX')
roi_min = os.getenv('ROI_MIN')
invested_min = os.getenv('INVESTED_MIN')

# Files
potential_output_file = f'{outputs_folder}/potential_wallets.txt'
profitable_and_winning_output_file = f'{outputs_folder}/profitable_and_winning_wallets.txt'
profitable_and_winning_and_not_sniping_output_file = f'{outputs_folder}/profitable_and_winning_and_not_sniping_wallets.txt'

def get_token_info(api_url, api_key, token_address):
    headers = {
        'x-api-key': api_key
    }
    response = requests.get(api_url+f'{token_address}', headers=headers)
    response.raise_for_status()  # Raise an error for bad status codes
    return response.json()

def get_trending_tokens(api_url, api_key, timeframe='24h'):
    headers = {
        'x-api-key': api_key
    }
    response = requests.get(api_url+f'{timeframe}', headers=headers)
    response.raise_for_status()  # Raise an error for bad status codes
    return response.json()

def get_top_traders_for_token(api_url, api_key, token_address):
    headers = {
        'x-api-key': api_key
    }
    response = requests.get(api_url+f'{token_address}', headers=headers)
    response.raise_for_status()  # Raise an error for bad status codes
    return response.json()

def get_trades_for_token(api_url, api_key, token_address, cursor=None):
    headers = {
        'x-api-key': api_key
    }
    params = {
        'parseJupiter': True,
        'hideArb': True,
        'cursor': cursor
    }
    response = requests.get(api_url+f'{token_address}', params=params, headers=headers)
    response.raise_for_status()  # Raise an error for bad status codes
    return response.json()

def get_wallet_pnl(api_url, api_key, wallet_address):
    headers = {
        'x-api-key': api_key
    }
    params = {
        'showHistoricPnL': True,
        'hideDetails': True
    }
    response = requests.get(api_url+f'{wallet_address}', params=params, headers=headers)
    response.raise_for_status()  # Raise an error for bad status codes
    return response.json()

def get_wallet_data(api_url, api_key, page):
    headers = {
        'x-api-key': api_key
    }
    response = requests.get(api_url+f'{page}', headers=headers)
    response.raise_for_status()  # Raise an error for bad status codes
    return response.json()

def get_wallet_details(api_url, api_key, wallet_address):
    headers = {
        'x-api-key': api_key
    }
    response = requests.get(api_url+f'{wallet_address}', headers=headers)
    response.raise_for_status()  # Raise an error for bad status codes
    return response.json()

def filter_profitable_wallets(wallets):
    # Filter wallets with win rate over 50%
    return [
        wallet for wallet in wallets 
        if wallet.get('summary', {}).get('winPercentage') is not None 
        and wallet['summary']['winPercentage'] >= winrate_min 
        and wallet['summary']['winPercentage'] <= winrate_max
        and wallet['summary']['total'] > 0
        and (wallet['summary']['total'] / wallet['summary']['totalInvested']) > 0.80
    ]

def filter_profitable_top_wallets(wallets):
    # Filter wallets with win rate over 50%
    return [
        wallet['wallet'] for wallet in wallets 
        if wallet['total'] > 0 
        and wallet['total_invested'] > invested_min
        and (wallet['total'] / wallet['total_invested']) * 100 > roi_min
    ]

def save_to_txt(wallets, output_file):
    with open(output_file, "a") as f:
        for wallet in wallets:
            f.write(f"{wallet}\n")

def get_latest_transaction_signature(api_url, api_key, network, account):
    logger.debug(f"Fetching latest transaction for account: {account}")
    headers = {"x-api-key": api_key}
    params = {
        "network": network,
        "account": account,
        "tx_num": 1,
        "enable_raw": "true",
        "enable_events": "true"
    }
    response = requests.get(api_url, headers=headers, params=params)
    if response.status_code == 200:
        data = response.json()
        if data.get("result"):
            signature = data["result"][0]["signatures"][0]
            block_time = data["result"][0]["raw"]["blockTime"]
            logger.debug(f"Latest transaction signature: {signature}, block time: {block_time}")
            return signature, block_time
    logger.error("Failed to fetch the latest transaction")
    return None, None

def parse_transaction(tx):
    block_time = tx.get('raw', {}).get('blockTime')
    blocktime_utc = datetime.fromtimestamp(block_time, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S') if block_time else "N/A"
    signature = tx.get('signatures', ['N/A'])[0]
    slot = tx.get('raw', {}).get('slot', 'N/A')
    status = tx.get('status', 'N/A')
    compute_unit = tx.get('raw', {}).get('meta', {}).get('computeUnitsConsumed', 'N/A')
    fee = tx.get('raw', {}).get('meta', {}).get('fee', 'N/A')
   
    token_name = 'N/A'
    token_in = 'N/A'
    profit = 'N/A'
    if tx.get('actions') and len(tx['actions']) > 0:
        action = tx['actions'][0]
        token_in_info = action.get('info', {}).get('tokens_swapped', {}).get('in', {})
        token_name = token_in_info.get('symbol', 'N/A')
        token_in = token_in_info.get('amount', 'N/A')

        ###
        token_in_name = token_in_info.get('symbol', 'N/A')
        token_in_address = token_in_info.get('token_address', 'N/A')
        token_in_amount = token_in_info.get('amount', 'N/A')
        token_out_info = action.get('info', {}).get('tokens_swapped', {}).get('out', {})
        token_out_name = token_out_info.get('symbol', 'N/A')
        token_out_address = token_out_info.get('token_address', 'N/A')
        token_out_amount = token_out_info.get('amount', 'N/A')

        token_out = action.get('info', {}).get('tokens_swapped', {}).get('out', {}).get('amount', 'N/A')
        if token_in != 'N/A' and token_out != 'N/A':
            try:
                profit = float(token_out) - float(token_in)
            except ValueError:
                profit = 'N/A'
   
    memo = 'N/A'
    instructions = tx.get('raw', {}).get('transaction', {}).get('message', {}).get('instructions', [])
    for instruction in instructions:
        if instruction.get('parsed'):
            parsed = instruction['parsed']
            if isinstance(parsed, str) and parsed.strip():
                memo = parsed.strip()
                break
   
    # get all the buys
    type = 'N/A'
    if token_in_name == 'SOL':
        type = 'buy'
    elif token_in_name != 'SOL' and token_in_name != 'N/A':
        type = 'sell'

    return {"type": type, "blocktime_utc": blocktime_utc, "token_out_name": token_out_name, "token_out_address": token_out_address, "token_out_amount": token_out_amount, "token_in_name": token_in_name, "token_in_address": token_in_address, "token_in_amount": token_in_amount}

def fetch_and_parse_transactions(api_url, api_key, network, account, time_delta):
    latest_signature, latest_block_time = get_latest_transaction_signature(api_url, api_key, network, account)
    if not latest_signature:
        logger.error("Failed to fetch the latest transaction.")
        return []

    end_time = datetime.fromtimestamp(latest_block_time)
    start_time = end_time - time_delta if time_delta else datetime.min
    logger.debug(f"Fetching transactions from {start_time} to {end_time}")

    transactions = []
    before_tx_signature = latest_signature
    api_calls = 0   
    continue_fetching = True

    while continue_fetching:
        api_calls += 1
        logger.debug(f"API call #{api_calls}, before_tx_signature: {before_tx_signature}")
        params = {
            "network": network,
            "account": account,
            "tx_num": 100,
            "enable_raw": "true",
            "enable_events": "true",
            "before_tx_signature": before_tx_signature
        }
        response = requests.get(api_url, headers={"x-api-key": api_key}, params=params)
        
        if response.status_code != 200:
            logger.error(f"Error in API request: {response.status_code}, {response.text}")
            break

        data = response.json()
        batch = data.get("result", [])

        if not batch:
            logger.debug("No more transactions to fetch")
            break

        logger.debug(f"Fetched {len(batch)} transactions in this batch")

        batch_start_time = datetime.fromtimestamp(batch[-1]["raw"]["blockTime"])
        batch_end_time = datetime.fromtimestamp(batch[0]["raw"]["blockTime"])

        for tx in batch:
            tx_time = datetime.fromtimestamp(tx["raw"]["blockTime"])
            if start_time <= tx_time <= end_time:
                transactions.append(parse_transaction(tx))
            elif tx_time < start_time:
                continue_fetching = False
                break

        if continue_fetching and batch:
            before_tx_signature = batch[-1]["signatures"][0]
        else:
            break

        # Update progress
        progress_msg = f"\rAPI calls: {api_calls}, Parsed transactions from {batch_start_time} to {batch_end_time}"
        sys.stdout.write(progress_msg)
        sys.stdout.flush()

    print()  # New line after progress updates
    transactions.reverse()  # Reverse to get chronological order
    logger.info(f"Total API calls made: {api_calls}")
    logger.info(f"Total transactions fetched: {len(transactions)}")
    return transactions
  
def get_balance_sol(api_url, api_key, account, network="mainnet"):
    headers = {"x-api-key": api_key}
    params = {
        "network": network,
        "wallet": account
    }
    try:
        response = requests.get(api_url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                return data.get("result", [])
        logger.error("Failed to fetch all tokens")
        return []
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching sol balances: {e}")
        return []
    
def get_all_tokens(api_url, api_key, network, account):
    headers = {"x-api-key": api_key}
    params = {
        "network": network,
        "wallet": account
    }
    try:
        response = requests.get(api_url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                # only keep tokens with address EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v and So11111111111111111111111111111111111111112
                return [token for token in data.get("result", []) if token.get("address") in ["EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", "So11111111111111111111111111111111111111112"]]
        logger.error("Failed to fetch all tokens")

        return []
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching token balances: {e}")
        return []
    
if __name__ == "__main__":
    # get top trader wallets
    page = 1
    next_page = True

    while next_page:
        try:
            print(f"Fetching wallets (page {page})...")
            # Fetch wallet data from the API
            wallets = get_wallet_data(top_traders_api_url, solana_tracker_api_key, page)

            # Filter the wallets to include only profitable ones
            profitable_wallets = filter_profitable_wallets(wallets['wallets'])
            profitable_wallets_list = [item['wallet'] for item in profitable_wallets]

            print(f"Found {len(profitable_wallets_list)} profitable wallets")
            # Save the profitable wallets to a CSV file
            save_to_txt(profitable_wallets_list, potential_output_file)

            next_page = wallets['hasNext']
            page += 1

            # Sleep for 1 second to avoid rate limiting (free tier has a limit of 1 request per second)
            sleep(1)
        except Exception as e:
            print("Error fetching wallets")
            print(e)
    print(f"Top trader wallets saved\n")

    # get top traders for trending tokens   
    tokens = get_trending_tokens(trending_tokens_api_url, solana_tracker_api_key)

    for token in tokens[:1]:
        potential_wallets = []
        if token not in do_not_check_list:
            print(token['token']['name'], token['token']['mint'])

            try:
                wallets = get_top_traders_for_token(top_traders_for_token_api_url, solana_tracker_api_key, token['token']['mint'])
                profitable_wallets = filter_profitable_top_wallets(wallets)
                potential_wallets = potential_wallets + profitable_wallets
            except Exception as e:
                print("Error fetching top traders for token:", token['token']['mint'])
                print(e)

            # sleep for 1 second to avoid rate limiting
            sleep(1)
            
            # get trades for token
            cursor = None
            page = 1
            max_pages = 10
            next_page = True
            while next_page and page <= max_pages:
                try:
                    trades = get_trades_for_token(trades_api_url, solana_tracker_api_key, token['token']['mint'], cursor)
                    cursor = trades['nextCursor']
                    next_page = trades['hasNextPage']
                    page += 1

                    potential_wallets = potential_wallets + [trade['wallet'] for trade in trades['trades']]
                except Exception as e:
                    print("Error fetching trades for token:", token['token']['mint'])
                    print(e)
            
            # sleep for 1 second to avoid rate limiting
            sleep(1)
                    
            save_to_txt(set(potential_wallets), potential_output_file)

    # Potentially more wallets?
    # https://docs.birdeye.so/reference/get_trader-gainers-losers

    # read from output_file
    with open(potential_output_file, "r") as f:
        potential_wallets = f.read().splitlines()

    # rewrite the file with unique wallets
    with open(potential_output_file, "w") as f:
        for wallet in set(potential_wallets):
            f.write(f"{wallet}\n")

    # read from output_file
    with open(potential_output_file, "r") as f:
        potential_wallets = f.read().splitlines()

    # iterate over the wallets to test profitability
    for wallet in potential_wallets:
        print("Fetching PnL for wallet:", wallet)
        try:
            pnl = get_wallet_pnl(wallet_pnl_api_url, solana_tracker_api_key, wallet)
            if pnl.get('summary', {}).get('winPercentage') is not None:
                if pnl['summary']['winPercentage'] >= winrate_min and pnl['summary']['winPercentage'] <= winrate_max:
                        if pnl['summary']['total'] > 0 and pnl['summary']['totalInvested'] > invested_min:
                            if (pnl['summary']['total'] / pnl['summary']['totalInvested']) * 100 >= roi_min:
                                # save to text file
                                print("Wallet is profitable and winning:", wallet)
                                with open(profitable_and_winning_output_file, "a") as f:
                                    f.write(f"{wallet}\n")
            
            # sleep for 1 second to avoid rate limiting
            sleep(1)
        except Exception as e:
            print("Error fetching PnL for wallet:", wallet)
            print(e)

    # Check for minimum balance and avoid snipers (buy on launch)
    with open(profitable_and_winning_output_file, "r") as f:
        profitable_and_winning_wallets = f.read().splitlines()

    # rewrite the file with unique wallets
    with open(profitable_and_winning_output_file, "w") as f:
        for wallet in set(profitable_and_winning_wallets):
            f.write(f"{wallet}\n")

    # read from output_file
    with open(profitable_and_winning_output_file, "r") as f:
        profitable_and_winning_wallets = f.read().splitlines()

    # iterate over the wallets
    for wallet in set(profitable_and_winning_wallets):
        print("Fetching transactions wallet:", wallet)
        is_sniping = False
        has_minimum_balance = True

        # TODO: check for minimum balance
        # get_balance_sol(api_url, api_key, wallet)
        # TODO: Avoid frequent airdrops
        # TODO: Avoid multiple buys per token
        # TODO: Avoid scalpers (trade a lot in less than 2 min)
        # TODO: Minimum average holding time of 20 min
        # TODO: Don’t sell more than they buy
        # TODO: Trading 2-5 times a day

        try:
            transactions = fetch_and_parse_transactions(transaction_history_api_url, shyft_api_key, 'mainnet-beta', wallet, timedelta(days=7))

            if transactions:
                # get all the buy transactions
                buy_transactions = [tx for tx in transactions if tx['type'] == 'buy']

                # get unique token_out_address from the list
                tokens = set([tx['token_out_address'] for tx in buy_transactions])
                for token in tokens:
                    # get all the buy transactions for the token
                    token_buy_transactions = [tx for tx in buy_transactions if tx['token_out_address'] == token]

                    # sort the transactions by blocktime
                    token_buy_transactions = sorted(token_buy_transactions, key=lambda x: x['blocktime_utc'], reverse=False)
                    earliest_buy_transaction = datetime.strptime(token_buy_transactions[0]['blocktime_utc'], '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)

                    # get the token created time
                    token_info = get_token_info(token_info_api_url, solana_tracker_api_key, token)
                    token_pools = token_info['pools']
                    token_pools_created_at_values = [item.get('createdAt', 9999999999999) for item in token_pools]
                    token_created_at = datetime.fromtimestamp(min(token_pools_created_at_values) / 1000, tz=timezone.utc)

                    sniping_window = timedelta(minutes=1)                    
                    if abs(earliest_buy_transaction - token_created_at) <= sniping_window:
                        is_sniping = True
            else:
                print("No transactions found for wallet:", wallet)
        except Exception as e:
            print("Error fetching transactions for wallet:", wallet)
            print(e)

        if not is_sniping and has_minimum_balance:
            # save to text file
            print("Wallet is profitable and winning and not sniping:", wallet)
            with open(profitable_and_winning_and_not_sniping_output_file, "a") as f:
                f.write(f"{wallet}\n")

    print("Done!")
    