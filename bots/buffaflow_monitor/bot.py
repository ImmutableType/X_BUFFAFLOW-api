import os
import requests
import tweepy
from datetime import datetime, timedelta
import json

# Configuration
CONTRACT_ADDRESS = "0xc8654a7a4bd671d4ceac6096a92a3170fa3b4798"
FLOW_RPC_URL = "https://mainnet.evm.nodes.onflow.org"
MIN_TRADE_AMOUNT = 1000  # 1,000 tokens
OPENSEA_COLLECTION = "moonbuffaflow"

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
        
        # Look back ~1 hour of blocks (assuming ~3 second blocks)
        from_block = current_block - 20000
        
        print(f"DEBUG: Current block: {current_block}")
        print(f"DEBUG: Looking from block {from_block} to latest")
        
        # Transfer event signature: Transfer(address,address,uint256)
        transfer_topic = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
        
        # Get logs for Transfer events
        payload = {
            "jsonrpc": "2.0",
            "method": "eth_getLogs",
            "params": [{
                "address": CONTRACT_ADDRESS,
                "topics": [transfer_topic],
                "fromBlock": hex(from_block),
                "toBlock": "latest"
            }],
            "id": 2
        }
        
        response = requests.post(FLOW_RPC_URL, json=payload)
        logs = response.json().get('result', [])
        
        print(f"DEBUG: Total raw logs found: {len(logs)}")
        
        significant_trades = []
        for i, log in enumerate(logs):
            # Parse transfer amount (18 decimals)
            amount_hex = log['data']
            amount_wei = int(amount_hex, 16)
            amount_tokens = amount_wei / (10 ** 18)
            
            # Parse from/to addresses
            from_addr = '0x' + log['topics'][1][26:]
            to_addr = '0x' + log['topics'][2][26:]
            
            print(f"DEBUG: Log {i}: {amount_tokens} tokens, from {from_addr[:10]}... to {to_addr[:10]}...")
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
                        'block': log['blockNumber']
                    })
                    print(f"DEBUG: ✅ Added trade: {amount_tokens} tokens")
                else:
                    print(f"DEBUG: ❌ Skipped mint/burn transaction")
            else:
                print(f"DEBUG: ❌ Below threshold: {amount_tokens} < {MIN_TRADE_AMOUNT}")
        
        print(f"DEBUG: Final significant trades: {len(significant_trades)}")
        return significant_trades
    except Exception as e:
        print(f"Error fetching transfers: {e}")
        return []

def get_opensea_activity():
    """Get recent OpenSea activity for MoonBuffaFLOW collection"""
    try:
        # OpenSea v1 API (no key required)
        url = f"https://api.opensea.io/api/v1/events"
        params = {
            'collection_slug': OPENSEA_COLLECTION,
            'event_type': 'successful',
            'only_opensea': 'false',
            'offset': 0,
            'limit': 20
        }
        
        headers = {
            'Accept': 'application/json',
            'User-Agent': 'MoonBuffaFLOW-Bot/1.0'
        }
        
        response = requests.get(url, params=params, headers=headers)
        if response.status_code == 200:
            data = response.json()
            # Filter for recent events (last hour)
            one_hour_ago = datetime.now() - timedelta(hours=1)
            recent_events = []
            
            for event in data.get('asset_events', []):
                if event.get('created_date'):
                    event_time = datetime.fromisoformat(event['created_date'].replace('Z', '+00:00'))
                    if event_time > one_hour_ago:
                        recent_events.append(event)
            
            return recent_events
        else:
            print(f"OpenSea API error: {response.status_code}")
            return []
    except Exception as e:
        print(f"Error fetching OpenSea activity: {e}")
        return []

def format_trade_message(trade):
    """Format a token trade into a tweet message"""
    amount = int(trade['amount'])
    amount_str = f"{amount:,}"
    
    if amount >= 100000:
        return f"🐃 You've been Herd! 🐋 LIBERTY STAMPEDE! {amount_str} $BUFFAFLOW tokens thundering across the range!\n\nWhen giants roam the open range, the whole ecosystem feels it!\n\n\n🎵 Oh, give me a home, where the $BUFFAFLOW roam... 🎵"
    elif amount >= 20000:
        return f"🐃 You've been Herd! FREEDOM migration! {amount_str} $BUFFAFLOW tokens roaming to new territory!\n\nThe bulls are charging across the open range on Flow EVM\n\n\n🎵 Oh, give me a home, where the $BUFFAFLOW roam... 🎵"
    elif amount >= 5000:
        return f"🐃 You've been Herd! ROAMING across the range! {amount_str} $BUFFAFLOW tokens on the move!\n\nSomeone's claiming more territory in the open range\n\n\n🎵 Oh, give me a home, where the $BUFFAFLOW roam... 🎵"
    else:
        return f"🐃 You've been Herd! {amount_str} $BUFFAFLOW tokens are roaming the open range!\n\nThe herd finds new pastures on Flow EVM\n\n\n🎵 Oh, give me a home, where the $BUFFAFLOW roam... 🎵"

def format_opensea_message(event):
    """Format an OpenSea event into a tweet message"""
    try:
        token_id = event.get('asset', {}).get('token_id', 'Unknown')
        event_type = event.get('event_type')
        
        # Try to get price information
        payment_token = event.get('payment_token', {})
        total_price = event.get('total_price')
        
        if total_price and payment_token:
            decimals = payment_token.get('decimals', 18)
            symbol = payment_token.get('symbol', 'FLOW')
            price = int(total_price) / (10 ** decimals)
            price_str = f"{price:.3f} {symbol}".rstrip('0').rstrip('.')
        else:
            price_str = "Unknown price"
        
        if event_type == 'successful':
            return f"💰 SOLD! MoonBuffaFLOW #{token_id} just sold for {price_str}! 🎉\n\n@opensea #MoonBuffaFLOW #FlowNFT"
        else:
            return f"🔔 MoonBuffaFLOW #{token_id} activity on @opensea! #MoonBuffaFLOW #FlowNFT"
    except Exception as e:
        print(f"Error formatting OpenSea message: {e}")
        return f"🔔 New MoonBuffaFLOW activity on @opensea! #MoonBuffaFLOW #FlowNFT"

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
        
        # Post about trades (limit to 2 per run to avoid spam)
        for trade in trades[:2]:
            if tweets_posted >= 3:  # Max 3 tweets per run
                break
                
            message = format_trade_message(trade)
            print(f"DEBUG: Generated message: {message}")
            
            if post_tweet(message):
                tweets_posted += 1
                # Wait between tweets to avoid rate limits
                import time
                time.sleep(10)
        
        # Check for OpenSea activity
        opensea_events = get_opensea_activity()
        print(f"Found {len(opensea_events)} OpenSea events")
        
        # Post about OpenSea activity (limit to remaining tweet slots)
        remaining_tweets = 3 - tweets_posted
        for event in opensea_events[:remaining_tweets]:
            if tweets_posted >= 3:
                break
                
            message = format_opensea_message(event)
            if post_tweet(message):
                tweets_posted += 1
                import time
                time.sleep(10)
        
        if tweets_posted == 0:
            print("ℹ️ No significant activity found in the last hour")
        else:
            print(f"✅ Posted {tweets_posted} tweets about MoonBuffaFLOW activity")
            
    except Exception as e:
        print(f"Error in main function: {e}")

if __name__ == "__main__":
    main()