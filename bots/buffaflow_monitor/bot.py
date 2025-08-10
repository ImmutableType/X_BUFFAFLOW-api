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
        from_block = current_block - 1200
        
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
        
        significant_trades = []
        for log in logs:
            # Parse transfer amount (18 decimals)
            amount_hex = log['data']
            amount_wei = int(amount_hex, 16)
            amount_tokens = amount_wei / (10 ** 18)
            
            # Only include trades above threshold
            if amount_tokens >= MIN_TRADE_AMOUNT:
                # Parse from/to addresses
                from_addr = '0x' + log['topics'][1][26:]
                to_addr = '0x' + log['topics'][2][26:]
                
                # Skip mint/burn transactions
                if from_addr != '0x0000000000000000000000000000000000000000' and to_addr != '0x0000000000000000000000000000000000000000':
                    significant_trades.append({
                        'amount': amount_tokens,
                        'from': from_addr,
                        'to': to_addr,
                        'tx_hash': log['transactionHash']
                    })
        
        return significant_trades
    except Exception as e:
        print(f"Error fetching transfers: {e}")
        return []

def get_opensea_activity():
    """Get recent OpenSea activity for MoonBuffaFLOW collection"""
    try:
        # Get events from last hour
        one_hour_ago = int((datetime.now() - timedelta(hours=1)).timestamp())
        
        url = f"https://api.opensea.io/api/v2/events/collection/{OPENSEA_COLLECTION}"
        params = {
            'event_type': 'sale,listing,offer',
            'occurred_after': one_hour_ago,
            'limit': 20
        }
        
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            return data.get('asset_events', [])
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
    
    if amount >= 10000:
        return f"🐋 WHALE ALERT! {amount_str} $BUFFAFLOW tokens just traded! 🚀\n\n💎 Someone's making big moves! #MoonBuffaFLOW #FlowEVM"
    elif amount >= 5000:
        return f"🚀 BIG MOVE! {amount_str} $BUFFAFLOW tokens on the move! 📈\n\n💎 #MoonBuffaFLOW #FlowEVM"
    else:
        return f"💫 {amount_str} $BUFFAFLOW tokens just traded! 🔥\n\n#MoonBuffaFLOW #FlowEVM"

def format_opensea_message(event):
    """Format an OpenSea event into a tweet message"""
    try:
        token_id = event.get('nft', {}).get('identifier', 'Unknown')
        event_type = event.get('event_type')
        
        # Try to get price information
        payment = event.get('payment', {})
        if payment:
            quantity = payment.get('quantity', '0')
            symbol = payment.get('symbol', 'FLOW')
            decimals = payment.get('decimals', 18)
            
            # Convert to readable price
            price_wei = int(quantity) if quantity.isdigit() else 0
            price = price_wei / (10 ** decimals)
            price_str = f"{price:.3f} {symbol}".rstrip('0').rstrip('.')
        else:
            price_str = "Unknown price"
        
        if event_type == 'sale':
            return f"💰 SOLD! MoonBuffaFLOW #{token_id} just sold for {price_str}! 🎉\n\n@opensea #MoonBuffaFLOW #FlowNFT"
        elif event_type == 'listing':
            return f"📝 NEW LISTING! MoonBuffaFLOW #{token_id} listed for {price_str} ✨\n\n@opensea #MoonBuffaFLOW #FlowNFT"
        elif event_type == 'offer':
            return f"💍 NEW OFFER! Someone offered {price_str} for MoonBuffaFLOW #{token_id} 💎\n\n@opensea #MoonBuffaFLOW #FlowNFT"
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
        client.create_tweet(text=tweet_text)
        print(f"Tweet posted: {tweet_text[:50]}...")
        return True
    except Exception as e:
        print(f"Error posting tweet: {e}")
        return False

def main():
    try:
        print("🔍 Monitoring MoonBuffaFLOW activity...")
        
        # Check for token trades
        trades = get_recent_transfers()
        print(f"Found {len(trades)} significant trades")
        
        tweets_posted = 0
        
        # Post about trades (limit to 2 per run to avoid spam)
        for trade in trades[:2]:
            if tweets_posted >= 3:  # Max 3 tweets per run
                break
                
            message = format_trade_message(trade)
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