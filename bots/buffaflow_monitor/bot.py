import os
import requests
import tweepy
from datetime import datetime
import json

# Configuration
CONTRACT_ADDRESS = "0xc8654A7a4BD671D4cEac6096A92a3170FA3b4798"
FLOW_RPC_URL = "https://mainnet.evm.nodes.onflow.org"
MIN_TRADE_AMOUNT = 1000  # 1,000 tokens

def get_recent_transfers():
    """Get recent $BUFFAFLOW transfers from Flow EVM"""
    try:
        # Get current block number
        payload = {
            "jsonrpc": "2.0",
            "method": "eth_blockNumber",
            "params": [],
            "id": 1
        }
        response = requests.post(FLOW_RPC_URL, json=payload)
        current_block = int(response.json()['result'], 16)
        
        # Monitor last hour of activity (back to production monitoring)
        from_block = current_block - 1200  # ~1 hour back (3 second blocks)
        
        print(f"DEBUG: Current block: {current_block}")
        print(f"DEBUG: Looking from block {from_block} to latest")
        
        # Get ALL events from contract (no topic filtering)
        payload = {
            "jsonrpc": "2.0",
            "method": "eth_getLogs",
            "params": [{
                "address": CONTRACT_ADDRESS,
                "fromBlock": hex(from_block),
                "toBlock": "latest"
            }],
            "id": 2
        }
        
        response = requests.post(FLOW_RPC_URL, json=payload)
        logs = response.json().get('result', [])
        
        print(f"DEBUG: ALL events found: {len(logs)}")
        
        # Standard Transfer event signature
        transfer_topic = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
        # ERC-404 specific event signature (found in your transaction)
        erc404_transfer_topic = "0xe59fdd36d0d223c0c7d996db7ad796880f45e1936cb0bb7ac102e7082e031487"
        
        significant_trades = []
        
        # Process all events and look for Transfer-like patterns
        for i, log in enumerate(logs):
            try:
                topics = log.get('topics', [])
                data = log.get('data', '')
                
                # Check for EITHER standard Transfer OR ERC-404 transfer
                if len(topics) >= 3 and (topics[0] == transfer_topic or topics[0] == erc404_transfer_topic):
                    event_type = 'ERC-20' if topics[0] == transfer_topic else 'ERC-404'
                    print(f"DEBUG: Found Transfer event {i} (type: {event_type})")
                    
                    # Parse transfer amount (18 decimals)
                    if data and data != '0x':
                        amount_hex = data
                        amount_wei = int(amount_hex, 16)
                        amount_tokens = amount_wei / (10 ** 18)
                        
                        # Parse from/to addresses
                        from_addr = '0x' + topics[1][26:] if len(topics) > 1 else 'unknown'
                        to_addr = '0x' + topics[2][26:] if len(topics) > 2 else 'unknown'
                        
                        print(f"DEBUG: Transfer {i}: {amount_tokens} tokens, from {from_addr[:10]}... to {to_addr[:10]}...")
                        print(f"DEBUG: Above threshold? {amount_tokens >= MIN_TRADE_AMOUNT}")
                        print(f"DEBUG: Not mint/burn? {from_addr != '0x0000000000000000000000000000000000000000' and to_addr != '0x0000000000000000000000000000000000000000'}")
                        
                        # Only include trades above threshold
                        if amount_tokens >= MIN_TRADE_AMOUNT:
                            # Skip mint/burn transactions
                            if from_addr != '0x0000000000000000000000000000000000000000' and to_addr != '0x0000000000000000000000000000000000000000':
                                significant_trades.append({
                                    'amount': amount_tokens,
                                    'from': from_addr,
                                    'to': to_addr,
                                    'tx_hash': log['transactionHash'],
                                    'block': log['blockNumber'],
                                    'type': event_type
                                })
                                print(f"DEBUG: ✅ Added trade: {amount_tokens} tokens ({event_type})")
                            else:
                                print(f"DEBUG: ❌ Skipped mint/burn transaction")
                        else:
                            print(f"DEBUG: ❌ Below threshold: {amount_tokens} < {MIN_TRADE_AMOUNT}")
                    
            except Exception as e:
                print(f"DEBUG: Error processing log {i}: {e}")
                continue
        
        print(f"DEBUG: Final significant trades: {len(significant_trades)}")
        return significant_trades
        
    except Exception as e:
        print(f"Error fetching transfers: {e}")
        return []

def format_trade_message(trade):
    """Format a token trade into a tweet message with tier variations"""
    amount = int(trade['amount'])
    amount_str = f"{amount:,}"
    
    if amount >= 100000:
        return f"🐃 MoonBuffaFLOW BOT: 🐋 LIBERTY STAMPEDE! {amount_str} $BUFFAFLOW tokens bought\n\nWhen giants roam the open range for @immutable_type\n\n🎵 Oh, give me a home, where the $BUFFAFLOW roam... 🎵"
    elif amount >= 20000:
        return f"🐃 MoonBuffaFLOW BOT: FREEDOM migration! {amount_str} $BUFFAFLOW tokens bought\n\nThe bulls charge across the range for @immutable_type\n\n🎵 Oh, give me a home, where the $BUFFAFLOW roam... 🎵"
    elif amount >= 5000:
        return f"🐃 MoonBuffaFLOW BOT: Big stampede! {amount_str} $BUFFAFLOW tokens bought\n\nSomeone's claiming territory for @immutable_type\n\n🎵 Oh, give me a home, where the $BUFFAFLOW roam... 🎵"
    else:
        return f"🐃 MoonBuffaFLOW BOT: {amount_str} $BUFFAFLOW tokens bought\n\nThe herd roams for @immutable_type\n\n🎵 Oh, give me a home, where the $BUFFAFLOW roam... 🎵"

def post_tweet(tweet_text):
    """Post tweet using the same mechanism as the horoscope bot"""
    client = tweepy.Client(
        consumer_key=os.getenv('TWITTER_API_KEY'),
        consumer_secret=os.getenv('TWITTER_API_SECRET'),
        access_token=os.getenv('TWITTER_ACCESS_TOKEN'),
        access_token_secret=os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
    )
    
    try:
        print(f"DEBUG: About to post tweet: {tweet_text}")
        client.create_tweet(text=tweet_text)
        print(f"Tweet posted successfully: {tweet_text[:50]}...")
        return True
    except Exception as e:
        print(f"Error posting tweet: {e}")
        return False

def main():
    try:
        print("🔍 Monitoring MoonBuffaFLOW activity...")
        print(f"DEBUG: Contract address: {CONTRACT_ADDRESS}")
        print(f"DEBUG: Min trade amount: {MIN_TRADE_AMOUNT}")
        print(f"DEBUG: Current time: {datetime.now()}")
        
        # Check for token trades
        trades = get_recent_transfers()
        print(f"Found {len(trades)} significant trades")
        
        tweets_posted = 0
        
        # Post about trades (limit to 3 per run)
        for trade in trades[:3]:
            message = format_trade_message(trade)
            print(f"DEBUG: Generated message: {message}")
            
            if post_tweet(message):
                tweets_posted += 1
                # Wait between tweets to avoid rate limits
                import time
                time.sleep(10)
        
        if tweets_posted == 0:
            print("ℹ️ No significant $BUFFAFLOW activity found in the search window")
        else:
            print(f"✅ Posted {tweets_posted} tweets about $BUFFAFLOW activity")
            
    except Exception as e:
        print(f"Error in main function: {e}")

if __name__ == "__main__":
    main()