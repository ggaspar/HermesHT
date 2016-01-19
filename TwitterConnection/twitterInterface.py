from ConfigParser import RawConfigParser
from tweepy.streaming import StreamListener
from tweepy.auth import OAuthHandler
from tweepy.streaming import Stream
import logging
import os
import Queue

logging.config.fileConfig("logging.conf")
logger = logging.getLogger('twitter')


#===============================================================================
# To manager the interface with twitter
# the following class uses Tweepy Lib
# self.consumer_key: to authenticate to twitter api
# self.consumer_secret:to authenticate to twitter api
# self.access_token:to authenticate to twitter api
# self.access_token_secret:to authenticate to twitter api
# self.auth: to authenticate to twitter api
# self.isStreaming: to know if we are currently streaming
# self.tweetsQueue: a queue to save retrieved tweets, that later will be read by DataManagementTools
# self.filter: a list with the terms to searched in tweets
#===============================================================================
class TweepyLib:
    
    CONFIG_FILENAME = "twitterConfig.ini" # name of the config file defining e.g. the Twitter API key
    CONFIG_SECTION_KEYS = "keys" # name of the section of the config file holding the various Twitter API keys/tokens/etc.

    def __init__(self):
        config = RawConfigParser()
        configFilePath = os.path.join(os.path.dirname(__file__), self.__class__.CONFIG_FILENAME)
        logger.info("HELLO WORLD")
        logger.info(configFilePath)
        config.read(configFilePath)
        
        # Read API keys/tokens from config file
        self.consumer_key = config.get(self.__class__.CONFIG_SECTION_KEYS, "consumer_key")
        self.consumer_secret = config.get(self.__class__.CONFIG_SECTION_KEYS, "consumer_secret")
        self.access_token = config.get(self.__class__.CONFIG_SECTION_KEYS, "access_token")
        self.access_token_secret = config.get(self.__class__.CONFIG_SECTION_KEYS, "access_token_secret")
        self.auth = OAuthHandler(self.consumer_key, self.consumer_secret)
        
        self.isStreaming=False
        self.connect()
        self.tweetsQueue = Queue.Queue()
        self.filter=[]
    
    def connect(self):
        #todo: recheck needed auth
        self.auth.set_access_token(self.access_token, self.access_token_secret)
        logger.info("Connected with Twitter")
  
    def doStreaming(self):
        class StdOutListener(StreamListener):
            def __init__(self, twitterObject):
                super(StdOutListener, self).__init__()
                self.twitterObject = twitterObject
           
            def on_status(self, status):
                logger.info("adds new tweeter to queue with id %s: %s" % (status.id, status.text))
                self.twitterObject.tweetsQueue.put(status)
                return True
                 
            def on_error(self, status):
                logger.warning("Error %s while reading twitter" % status)
  
        listener = StdOutListener(self) 
        self.stream = Stream(self.auth, listener)
        self.stream.filter(track=self.filter, async=True)
  
    def startStreamer(self):
        if(not self.filter):
            logger.warning("Trying to start stream, but the filter is empty")
            return
        self.doStreaming()
        logger.info("Streamer was started")
        self.isStreaming = True
    
    def stopStreamer(self):
        if(self.isStreaming):      
            self.isStreaming = False      
            self.stream.disconnect()
            logger.info("Streamer was stopped")
      
    def restartStreamer(self):
        self.stopStreamer()
        self.startStreamer()
      
    def addHashtagToFilter(self, newHashtag):
        if(newHashtag[:1] != '#'):
            newHashtag = '#' + newHashtag
        if(newHashtag in self.filter):
            return    
        self.filter.append(newHashtag.encode())
        logger.info("%s added to the filter" % newHashtag)
        self.restartStreamer()
        
    def removeHashtagFromFilter(self, existingHashtag):
        if(existingHashtag[:1] != '#'):
            existingHashtag = '#' + existingHashtag
        if(existingHashtag in self.filter):
            return    
        self.filter.remove(existingHashtag)
        logger.info("%s removed from the filter" % existingHashtag)
        self.restartStreamer()
        
    def removeAllHashtagsFromFilter(self):
        changes = 0
        for i in self.filter:
            # we only want to rmeove hashtags, not other filters
            if(i[:1] == '#'):
                changes += 1
                self.filter.remove(i)
        logger.info("All hashtags removed from the filter")
        if(changes != 0):
            self.restartStreamer()
      
