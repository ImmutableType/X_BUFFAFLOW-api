import os
import requests
import tweepy
from datetime import datetime

def get_bitcoin_price():
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
    response = requests.get(url)
    data = response.json()
    return data['bitcoin']['usd']

def create_tweet_text(price):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    return f"Bitcoin Price Update 🚨\n${price:,} USD\n\n{current_time}"

def post_tweet(tweet_text):
    client = tweepy.Client(
        consumer_key=os.getenv('TWITTER_API_KEY'),
        consumer_secret=os.getenv('TWITTER_API_SECRET'),
        access_token=os.getenv('TWITTER_ACCESS_TOKEN'),
        access_token_secret=os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
    )
    
    client.create_tweet(text=tweet_text)

def main():
    try:
        price = get_bitcoin_price()
        tweet_text = create_tweet_text(price)
        post_tweet(tweet_text)
        print("Tweet posted successfully!")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()