### Working off of script from: https://github.com/feconroses/gather-tweets-from-stream


import tweepy
from datetime import date
import csv
import ssl
import time
from requests.exceptions import Timeout, ConnectionError
from requests.packages.urllib3.exceptions import ReadTimeoutError

# Add your Twitter API credentials
# keys_tweepy.py is a file of the form (which should be added to .gitignore locally)
# consumer_key = "***"
# consumer_secret = "***"
# access_key = "***-***"
# access_secret = "***"

from keys_tweepy import *


# Handling authentication with Twitter
auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_key, access_secret)

# Create a wrapper for the API provided by Twitter
api = tweepy.API(auth)

# Setting up the keywords, hashtag or mentions we want to listen
keywords = ["#prospectpark",
            "#brooklyn",
            "#nycparks",
            "#prospect_park",
            "#prospectparkzoo",
            "prospectparknyc"]

# Set the name for CSV file  where the tweets will be saved
filename = "tweets_aws"

writer_day = None
writer_file = None
writer = None


# We need to implement StreamListener to use Tweepy to listen to Twitter
class StreamListener(tweepy.StreamListener):

    def on_error(self, status_code):
        print("on_error", status_code)
        return False
    
    def on_status(self, status):
#        print("on_status", status)
        try:
            # saves the tweet object
            tweet_object = status

            # Checks if its a extended tweet (>140 characters)
            if 'extended_tweet' in tweet_object._json:
                tweet = tweet_object.extended_tweet['full_text']
            else:
                tweet = tweet_object.text

            '''Convert all named and numeric character references
            (e.g. &gt;, &#62;, &#x3e;) in the string s to the
            corresponding Unicode characters'''
            tweet = (tweet.replace('&amp;', '&').replace('&lt;', '<')
                     .replace('&gt;', '>').replace('&quot;', '"')
                     .replace('&#39;', "'").replace(';', " ")
                     .replace(r'\u', " "))

            # Save the keyword that matches the stream
            keyword_matches = []
            for word in keywords:
                if word.lower() in tweet.lower():
                    keyword_matches.extend([word])

            keywords_strings = ", ".join(str(x) for x in keyword_matches)

            # Save other information from the tweet
            user = status.author.screen_name
            timeTweet = status.created_at
            source = status.source
            tweetId = status.id
            tweetUrl = "https://twitter.com/statuses/" + str(tweetId)

            # Exclude retweets, too many mentions and too many hashtags
            if not any((('RT @' in tweet, 'RT' in tweet,
                       tweet.count('@') >= 2, tweet.count('#') >= 3))):
                write_tweet([tweet, keywords_strings, timeTweet,
                                user, source, tweetId, tweetUrl])
                print("adding tweet", timeTweet)
        except Exception as e:
            print('Encountered Exception:', e)
            pass

def write_tweet(row):
    global writer
    global writer_file
    global writer_day
    current_day = date.today().isoformat()
    if current_day != writer_day:
        if writer is not None:
            writer_file.close()
        writer_file = open(f"{filename}_{current_day}.csv", 'w')
        writer = csv.writer(writer_file)
        writer_day = current_day
        # Add a header row to the CSV
        writer.writerow(["Tweet", "Matched Keywords", "Date", "User",
                        "Source", "Tweet ID", "Tweet URL"])
    # Saves the tweet information in a new row of the CSV file
    writer.writerow(row)
    writer_file.flush()
    

def work():

    # Initializing the twitter streap Stream
    try:
        print("checking authentification")
        streamingAPI = tweepy.streaming.Stream(auth=api.auth, listener=StreamListener())
        streamingAPI.filter(track=keywords)

    # Stop temporarily when hitting Twitter rate Limit
    except tweepy.RateLimitError:
        print("RateLimitError...waiting ~15 minutes to continue")
        time.sleep(1001)
        streamingAPI = tweepy.streaming.Stream(auth, StreamListener())
        streamingAPI.filter(track=[keywords])

    # Stop temporarily when getting a timeout or connection error
    except (Timeout, ssl.SSLError, ReadTimeoutError,
            ConnectionError) as exc:
        print("Timeout/connection error...waiting ~15 minutes to continue")
        time.sleep(1001)
        streamingAPI = tweepy.streaming.Stream(auth, StreamListener())
        streamingAPI.filter(track=[keywords])

    # Stop temporarily when getting other errors
    except tweepy.TweepError as e:
        if 'Failed to send request:' in e.reason:
            print("Time out error caught.")
            time.sleep(1001)
            streamingAPI = tweepy.streaming.Stream(auth, StreamListener())
            streamingAPI.filter(track=[keywords])
        else:
            print("Other error with this user...passing")
            pass


if __name__ == '__main__':
    work()
