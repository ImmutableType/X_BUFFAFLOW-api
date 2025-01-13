import os
import requests
import tweepy
from datetime import datetime

def get_daily_horoscope():
    url = "https://horoscope-app-api.vercel.app/api/v1/get-horoscope/daily"
    response = requests.get(url)
    data = response.json()
    return data['data']['horoscope_data']

def create_tweet_text(horoscope_data):
    current_time = datetime.now().strftime("%Y-%m-%d")
    return f"Daily Horoscope {current_time} 🌟\n\n{horoscope_data}\n\n#DailyHoroscope #Astrology"

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
        horoscope = get_daily_horoscope()
        tweet_text = create_tweet_text(horoscope)
        post_tweet(tweet_text)
        print("Tweet posted successfully!")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
