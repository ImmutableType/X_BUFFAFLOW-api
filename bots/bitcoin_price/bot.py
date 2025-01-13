import os
import requests
import tweepy
from datetime import datetime

def get_daily_horoscope():
    base_url = "https://horoscope-app-api.vercel.app/api/v1/get-horoscope/daily"
    signs = {
        'aries': '♈',
        'taurus': '♉',
        'gemini': '♊',
        'cancer': '♋',
        'leo': '♌',
        'virgo': '♍',
        'libra': '♎',
        'scorpio': '♏',
        'sagittarius': '♐',
        'capricorn': '♑',
        'aquarius': '♒',
        'pisces': '♓'
    }
    
    horoscopes = []
    for sign, emoji in signs.items():
        url = f"{base_url}?sign={sign}&day=today"
        response = requests.get(url)
        data = response.json()
        horoscope_text = data['data']['horoscope_data']
        horoscopes.append(f"{emoji} {sign.capitalize()}: {horoscope_text}")
    
    return "\n\n".join(horoscopes)

def create_tweet_text(horoscope_data):
    current_time = datetime.now().strftime("%Y-%m-%d")
    return f"🌟 Daily Horoscopes for {current_time}\n\n{horoscope_data}\n\n#DailyHoroscope #Zodiac"

def post_tweet(tweet_text):
    client = tweepy.Client(
        consumer_key=os.getenv('TWITTER_API_KEY'),
        consumer_secret=os.getenv('TWITTER_API_SECRET'),
        access_token=os.getenv('TWITTER_ACCESS_TOKEN'),
        access_token_secret=os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
    )
    
    # Split into threads if too long
    if len(tweet_text) > 280:
        tweets = [tweet_text[i:i+280] for i in range(0, len(tweet_text), 280)]
        previous_tweet_id = None
        for tweet in tweets:
            response = client.create_tweet(
                text=tweet,
                in_reply_to_tweet_id=previous_tweet_id
            )
            previous_tweet_id = response.data['id']
    else:
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
