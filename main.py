import json
import requests
from datetime import datetime
import time
import sys

BTC_ADDRESS = "BTC ADDY"
DISCORD_WEBHOOK = "DISCORD WEBHOOK"
CHECK_INTERVAL = 60

seen_txs = {}


def get_btc_price():
    """
    Fetches current Bitcoin price in USD from CoinGecko API.
    Falls back to Coinpaprika if CoinGecko fails.
    
    Returns:
        float: Current BTC price in USD, or None if all APIs fail
    """
    try:
        resp = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd", timeout=5)
        return resp.json()['bitcoin']['usd']
    except:
        try:
            resp = requests.get("https://api.coinpaprika.com/v1/tickers/btc-bitcoin", timeout=5)
            return resp.json()['quotes']['USD']['price']
        except:
            return None


def get_address_data():
    """
    Fetches address information and recent transactions from mempool.space API.
    
    Returns:
        dict: Contains 'balance' (float) and 'transactions' (list), or None if fetch fails
    """
    try:
        url = f"https://mempool.space/api/address/{BTC_ADDRESS}"
        print(f"Fetching address info from: {url}")
        resp = requests.get(url, timeout=10)
        print(f"Address info response status: {resp.status_code}")
        
        if resp.status_code != 200:
            print(f"Failed to fetch address info: HTTP {resp.status_code}")
            return None
        
        addr_data = resp.json()
        
        url = f"https://mempool.space/api/address/{BTC_ADDRESS}/txs"
        print(f"Fetching transactions from: {url}")
        resp = requests.get(url, timeout=10)
        print(f"Transactions response status: {resp.status_code}")
        
        if resp.status_code != 200:
            print(f"Failed to fetch transactions: HTTP {resp.status_code}")
            return None
        
        txs = resp.json()
        print(f"Successfully fetched {len(txs)} transactions")
        
        chain_stats = addr_data.get('chain_stats', {})
        funded = chain_stats.get('funded_txo_sum', 0)
        spent = chain_stats.get('spent_txo_sum', 0)
        balance = (funded - spent) / 100000000
        
        print(f"Current balance: {balance:.8f} BTC")
        
        return {
            'balance': balance,
            'transactions': txs[:10]
        }
    except Exception as e:
        print(f"Error fetching address data: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_tx_details(txid):
    """
    Fetches detailed transaction information from mempool.space API.
    
    Args:
        txid (str): Transaction ID hash
        
    Returns:
        dict: Transaction details, or None if fetch fails
    """
    try:
        url = f"https://mempool.space/api/tx/{txid}"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        return None
    except Exception as e:
        print(f"Error fetching transaction details: {e}")
        return None


def determine_tx_type(tx_data):
    """
    Determines if a transaction is incoming, outgoing, or unknown relative to monitored address.
    
    Args:
        tx_data (dict): Transaction data from API
        
    Returns:
        str: 'incoming', 'outgoing', or 'unknown'
    """
    has_our_output = False
    has_our_input = False
    
    for vout in tx_data.get('vout', []):
        if vout.get('scriptpubkey_address') == BTC_ADDRESS:
            has_our_output = True
    
    for vin in tx_data.get('vin', []):
        prevout = vin.get('prevout', {})
        if prevout.get('scriptpubkey_address') == BTC_ADDRESS:
            has_our_input = True
    
    if has_our_output and not has_our_input:
        return "incoming"
    elif has_our_input:
        return "outgoing"
    
    return "unknown"


def send_discord_notif(tx_data, tx_type, is_confirmed, balance):
    """
    Sends a formatted Discord notification with transaction details.
    
    Args:
        tx_data (dict): Transaction data from API
        tx_type (str): 'incoming' or 'outgoing'
        is_confirmed (bool): Whether transaction is confirmed
        balance (float): Current address balance in BTC
    """
    if is_confirmed:
        color = 0x00ff00 if tx_type == "incoming" else 0xff4444
    else:
        color = 0xffa500
    
    btc_price = get_btc_price()
    
    amount_btc = 0
    if tx_type == "incoming":
        for vout in tx_data.get('vout', []):
            if vout.get('scriptpubkey_address') == BTC_ADDRESS:
                amount_btc += vout.get('value', 0) / 100000000
    else:
        for vout in tx_data.get('vout', []):
            if vout.get('scriptpubkey_address') != BTC_ADDRESS:
                amount_btc += vout.get('value', 0) / 100000000
    
    status = tx_data.get('status', {})
    confirmations = 0
    if status.get('confirmed'):
        try:
            tip_resp = requests.get("https://mempool.space/api/blocks/tip/height", timeout=5)
            current_height = int(tip_resp.text)
            block_height = status.get('block_height', 0)
            confirmations = current_height - block_height + 1
        except:
            confirmations = 1
    
    txid = tx_data.get('txid', 'N/A')
    fee = tx_data.get('fee', 0) / 100000000
    
    embed = {
        "title": f"{'✅ CONFIRMED' if is_confirmed else '⏳ UNCONFIRMED'} BTC Transaction",
        "color": color,
        "timestamp": datetime.now().isoformat(),
        "fields": []
    }
    
    embed["fields"].append({
        "name": "Type",
        "value": f"**{tx_type.upper()}**",
        "inline": True
    })
    
    amount_str = f"**{amount_btc:.8f} BTC**"
    if btc_price:
        usd_value = amount_btc * btc_price
        amount_str += f"\n≈ ${usd_value:,.2f} USD"
    
    embed["fields"].append({
        "name": "Amount",
        "value": amount_str,
        "inline": True
    })
    
    conf_emoji = "✅" if confirmations >= 6 else "⏳"
    embed["fields"].append({
        "name": f"{conf_emoji} Confirmations",
        "value": f"**{confirmations}**",
        "inline": True
    })
    
    tx_link = f"[View on Explorer](https://mempool.space/tx/{txid})"
    embed["fields"].append({
        "name": "Transaction Hash",
        "value": tx_link,
        "inline": False
    })
    
    if tx_type == "incoming":
        from_addrs = []
        for vin in tx_data.get('vin', []):
            addr = vin.get('prevout', {}).get('scriptpubkey_address')
            if addr and addr != BTC_ADDRESS:
                from_addrs.append(addr)
        
        from_addrs = list(set(from_addrs))[:3]
        if from_addrs:
            from_str = '\n'.join([f"`{addr[:20]}...{addr[-10:]}`" for addr in from_addrs])
            embed["fields"].append({
                "name": "From",
                "value": from_str,
                "inline": False
            })
    else:
        to_addrs = []
        for vout in tx_data.get('vout', []):
            addr = vout.get('scriptpubkey_address')
            if addr and addr != BTC_ADDRESS:
                to_addrs.append(addr)
        
        to_addrs = list(set(to_addrs))[:3]
        if to_addrs:
            to_str = '\n'.join([f"`{addr[:20]}...{addr[-10:]}`" for addr in to_addrs])
            embed["fields"].append({
                "name": "To",
                "value": to_str,
                "inline": False
            })
    
    if balance is not None:
        balance_str = f"**{balance:.8f} BTC**"
        if btc_price:
            balance_usd = balance * btc_price
            balance_str += f"\n≈ ${balance_usd:,.2f} USD"
        
        embed["fields"].append({
            "name": "Current Balance",
            "value": balance_str,
            "inline": False
        })
    
    block_time = status.get('block_time')
    if block_time:
        embed["fields"].append({
            "name": "Time",
            "value": f"<t:{block_time}:R>",
            "inline": True
        })
    
    if fee > 0:
        fee_str = f"**{fee:.8f} BTC**"
        if btc_price:
            fee_usd = fee * btc_price
            fee_str += f"\n≈ ${fee_usd:.2f} USD"
        
        embed["fields"].append({
            "name": "Fee",
            "value": fee_str,
            "inline": True
        })
    
    embed["footer"] = {
        "text": f"Monitoring {BTC_ADDRESS[:15]}...{BTC_ADDRESS[-10:]}"
    }
    
    payload = {
        "content": "@everyone",
        "embeds": [embed]
    }
    
    try:
        resp = requests.post(DISCORD_WEBHOOK, json=payload, timeout=10)
        if resp.status_code == 204:
            print(f"Notification sent: {txid[:16]}...")
        else:
            print(f"Failed to send notification: {resp.status_code}")
    except Exception as e:
        print(f"Error sending notification: {e}")


def check_transactions():
    """
    Checks for new transactions and sends notifications for untracked transactions.
    Updates confirmation status for previously seen unconfirmed transactions.
    """
    global seen_txs
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Checking for transactions...")
    
    addr_data = get_address_data()
    if not addr_data:
        print("Could not fetch address data - retrying next cycle")
        return
    
    balance = addr_data['balance']
    transactions = addr_data['transactions']
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Found {len(transactions)} recent transactions")
    
    for tx in transactions:
        txid = tx.get('txid')
        if not txid:
            continue
        
        is_confirmed = tx.get('status', {}).get('confirmed', False)
        
        if txid in seen_txs:
            old_confirmed = seen_txs[txid]
            if not old_confirmed and is_confirmed:
                print(f"Transaction confirmed: {txid[:16]}...")
                
                tx_full = get_tx_details(txid)
                if tx_full:
                    tx_type = determine_tx_type(tx_full)
                    if tx_type != "unknown":
                        send_discord_notif(tx_full, tx_type, True, balance)
                        seen_txs[txid] = True
            continue
        
        print(f"New transaction detected: {txid[:16]}...")
        
        tx_full = get_tx_details(txid)
        if not tx_full:
            print(f"Could not fetch full details for {txid[:16]}")
            continue
        
        tx_type = determine_tx_type(tx_full)
        if tx_type == "unknown":
            print(f"Transaction doesn't involve monitored address")
            continue
        
        print(f"Type: {tx_type}, Confirmed: {is_confirmed}")
        
        send_discord_notif(tx_full, tx_type, is_confirmed, balance)
        
        seen_txs[txid] = is_confirmed


def test_mode():
    """
    Test mode that displays last 3 transactions and optionally sends them to Discord.
    Useful for verifying configuration before running continuous monitoring.
    """
    print("TEST MODE - Showing last 3 transactions")
    print(f"Address: {BTC_ADDRESS}")
    print("-" * 60)
    
    print("\nFetching address information...")
    addr_data = get_address_data()
    
    if not addr_data:
        print("Could not fetch address data!")
        return
    
    balance = addr_data['balance']
    transactions = addr_data['transactions']
    
    btc_price = get_btc_price()
    
    print("\nADDRESS DETAILS:")
    print(f"   Balance: {balance:.8f} BTC", end="")
    if btc_price:
        print(f" (≈ ${balance * btc_price:,.2f} USD)")
    else:
        print()
    print(f"   Total Transactions: {len(transactions)} (showing last 3)")
    print(f"   Address: {BTC_ADDRESS}")
    
    print("\nLAST 3 TRANSACTIONS:\n")
    
    for i, tx in enumerate(transactions[:3], 1):
        txid = tx.get('txid')
        if not txid:
            continue
        
        print(f"{'='*60}")
        print(f"Transaction #{i}")
        print(f"{'='*60}")
        
        tx_full = get_tx_details(txid)
        if not tx_full:
            print(f"Could not fetch details for {txid}")
            continue
        
        tx_type = determine_tx_type(tx_full)
        
        amount_btc = 0
        if tx_type == "incoming":
            for vout in tx_full.get('vout', []):
                if vout.get('scriptpubkey_address') == BTC_ADDRESS:
                    amount_btc += vout.get('value', 0) / 100000000
        elif tx_type == "outgoing":
            for vout in tx_full.get('vout', []):
                if vout.get('scriptpubkey_address') != BTC_ADDRESS:
                    amount_btc += vout.get('value', 0) / 100000000
        
        status = tx_full.get('status', {})
        is_confirmed = status.get('confirmed', False)
        confirmations = 0
        if is_confirmed:
            try:
                tip_resp = requests.get("https://mempool.space/api/blocks/tip/height", timeout=5)
                current_height = int(tip_resp.text)
                block_height = status.get('block_height', 0)
                confirmations = current_height - block_height + 1
            except:
                confirmations = 1
        
        fee = tx_full.get('fee', 0) / 100000000
        
        print(f"TXID: {txid}")
        print(f"Type: {tx_type.upper()}")
        print(f"Amount: {amount_btc:.8f} BTC", end="")
        if btc_price:
            print(f" (≈ ${amount_btc * btc_price:,.2f} USD)")
        else:
            print()
        
        print(f"Status: {'CONFIRMED' if is_confirmed else 'UNCONFIRMED'}")
        print(f"Confirmations: {confirmations}")
        
        if fee > 0:
            print(f"Fee: {fee:.8f} BTC", end="")
            if btc_price:
                print(f" (≈ ${fee * btc_price:.2f} USD)")
            else:
                print()
        
        if tx_type == "incoming":
            from_addrs = []
            for vin in tx_full.get('vin', []):
                addr = vin.get('prevout', {}).get('scriptpubkey_address')
                if addr and addr != BTC_ADDRESS:
                    from_addrs.append(addr)
            
            from_addrs = list(set(from_addrs))[:3]
            if from_addrs:
                print(f"From:")
                for addr in from_addrs:
                    print(f"   {addr}")
        elif tx_type == "outgoing":
            to_addrs = []
            for vout in tx_full.get('vout', []):
                addr = vout.get('scriptpubkey_address')
                if addr and addr != BTC_ADDRESS:
                    to_addrs.append(addr)
            
            to_addrs = list(set(to_addrs))[:3]
            if to_addrs:
                print(f"To:")
                for addr in to_addrs:
                    print(f"   {addr}")
        
        block_time = status.get('block_time')
        if block_time:
            dt = datetime.fromtimestamp(block_time)
            print(f"Time: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
        
        print(f"Explorer: https://mempool.space/tx/{txid}")
        print()
    
    print("\n" + "="*60)
    choice = input("\nSend these last 3 transactions to Discord for testing? (y/n): ").lower().strip()
    
    if choice == 'y':
        print("\nSending test notifications to Discord...\n")
        
        for i, tx in enumerate(transactions[:3], 1):
            txid = tx.get('txid')
            if not txid:
                continue
            
            tx_full = get_tx_details(txid)
            if not tx_full:
                continue
            
            tx_type = determine_tx_type(tx_full)
            if tx_type == "unknown":
                continue
            
            is_confirmed = tx_full.get('status', {}).get('confirmed', False)
            
            print(f"   Sending transaction #{i}...", end=" ")
            send_discord_notif(tx_full, tx_type, is_confirmed, balance)
            time.sleep(1)
        
        print("\nTest notifications sent!")
    else:
        print("\nSkipped sending test notifications")
    
    print("\nTest mode complete!")


def main():
    """
    Main monitoring loop. Continuously checks for new transactions at specified intervals.
    Initializes by loading existing transactions to avoid duplicate notifications on startup.
    """
    global seen_txs
    
    print("Starting BTC Transaction Monitor...")
    print(f"Address: {BTC_ADDRESS}")
    print(f"Webhook: {DISCORD_WEBHOOK[:50]}...")
    print(f"Interval: {CHECK_INTERVAL} seconds")
    print("-" * 60)
    
    startup_embed = {
        "title": "BTC Monitor Started",
        "description": f"Monitoring address:\n`{BTC_ADDRESS}`\n\nChecking every **{CHECK_INTERVAL} seconds**",
        "color": 0xf7931a,
        "timestamp": datetime.now().isoformat(),
        "footer": {"text": "Monitor active - waiting for transactions..."}
    }
    
    try:
        resp = requests.post(DISCORD_WEBHOOK, json={"content": "@everyone", "embeds": [startup_embed]}, timeout=10)
        if resp.status_code == 204:
            print("Startup notification sent!")
        else:
            print(f"Startup notification failed: {resp.status_code}")
    except Exception as e:
        print(f"Could not send startup notification: {e}")
    
    print("\nLoading existing transactions (won't notify for these)...")
    initial_data = get_address_data()
    if initial_data and initial_data.get('transactions'):
        loaded_count = 0
        for tx in initial_data['transactions']:
            txid = tx.get('txid')
            if txid:
                is_confirmed = tx.get('status', {}).get('confirmed', False)
                seen_txs[txid] = is_confirmed
                loaded_count += 1
        print(f"Loaded {loaded_count} existing transactions - these won't trigger notifications")
    else:
        print("Could not load existing transactions - ALL transactions will notify on first run!")
        print("This is normal if the address has no history or API is down")
    
    print("\nStarting monitoring loop...")
    print("Only NEW transactions from this point forward will notify!\n")
    
    while True:
        try:
            check_transactions()
            time.sleep(CHECK_INTERVAL)
        except KeyboardInterrupt:
            print("\nShutting down...")
            
            shutdown_embed = {
                "title": "BTC Monitor Stopped",
                "description": "Monitor manually stopped",
                "color": 0xe74c3c,
                "timestamp": datetime.now().isoformat()
            }
            
            try:
                requests.post(DISCORD_WEBHOOK, json={"embeds": [shutdown_embed]}, timeout=5)
            except:
                pass
            
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        test_mode()
    elif len(sys.argv) > 1 and sys.argv[1] == "--debug":
        print("DEBUG MODE - Testing API connectivity")
        print(f"Address: {BTC_ADDRESS}")
        print("-" * 60)
        
        print("\n1. Testing mempool.space API...")
        try:
            import requests
            resp = requests.get(f"https://mempool.space/api/address/{BTC_ADDRESS}", timeout=10)
            print(f"   Status: {resp.status_code}")
            if resp.status_code == 200:
                print("   ✓ API is accessible")
                data = resp.json()
                chain_stats = data.get('chain_stats', {})
                print(f"   Funded: {chain_stats.get('funded_txo_sum', 0)} sats")
                print(f"   Spent: {chain_stats.get('spent_txo_sum', 0)} sats")
                balance = (chain_stats.get('funded_txo_sum', 0) - chain_stats.get('spent_txo_sum', 0)) / 100000000
                print(f"   Balance: {balance:.8f} BTC")
            else:
                print(f"   ✗ API returned error: {resp.status_code}")
        except Exception as e:
            print(f"   ✗ Error: {e}")
        
        print("\n2. Testing transaction fetch...")
        try:
            resp = requests.get(f"https://mempool.space/api/address/{BTC_ADDRESS}/txs", timeout=10)
            print(f"   Status: {resp.status_code}")
            if resp.status_code == 200:
                txs = resp.json()
                print(f"   ✓ Found {len(txs)} transactions")
                if txs:
                    print(f"\n   Last transaction:")
                    print(f"   TXID: {txs[0].get('txid')}")
                    print(f"   Confirmed: {txs[0].get('status', {}).get('confirmed', False)}")
            else:
                print(f"   ✗ API returned error: {resp.status_code}")
        except Exception as e:
            print(f"   ✗ Error: {e}")
        
        print("\n3. Testing Discord webhook...")
        try:
            test_payload = {
                "content": "Test message from BTC monitor debug mode"
            }
            resp = requests.post(DISCORD_WEBHOOK, json=test_payload, timeout=10)
            print(f"   Status: {resp.status_code}")
            if resp.status_code == 204:
                print("   ✓ Discord webhook is working!")
            else:
                print(f"   ✗ Webhook returned error: {resp.status_code}")
        except Exception as e:
            print(f"   ✗ Error: {e}")
        
        print("\nDebug complete!")
    else:
        main()
