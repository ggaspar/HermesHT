from django.shortcuts import HttpResponse
from TwitterConnection import twitterInterface
from models import Company, Hashtag
import threading
import time
import datetime
import json


tweepy = twitterInterface.TweepyLib()
hashtagsPool = {}
intervalBetweenAutoRefreshes = 60
lastUpdate = None
#isServerRunning=False
#print "pe"



threadTwtReaderName = "Twitters Reader"
def readTweetsJob():
    """
    to be run by a dedicated thread. it reads from a queue all the tweets catched by Twitter streamer and updates
    hashtagsPool (in memory)
    """
    global hashtagsPool, tweepy
    while (True):
        try:
            tweet = tweepy.tweetsQueue.get()
            if(not tweet.entities['hashtags']):
                continue
            for hashtag in tweet.entities['hashtags']:
                htName = hashtag['text'].upper()
                if  htName in hashtagsPool.keys():
                    hashtagsPool[htName] = hashtagsPool[htName] + 1
            tweepy.tweetsQueue.task_done()
        except Exception as e:
            print "FAIL: " + str(e)

threadProdUpdater = "Production Updater"
def updateProductionJob():
    """
    to be run by a dedicated thread.
    every <intervalBetweenAutoRefreshes> seconds forces a refresh
    """
    global intervalBetweenAutoRefreshes
    while(True):
        time.sleep(intervalBetweenAutoRefreshes)
        forceRefresh()


def addCompany(request, name):
    """
    to be called by a a web service.
    adds a new Company/hashtag <name> to the DB and to twitter filter
    returns the status of the system
    """
    global hashtagsPool, tweepy
    name = name.upper()
    Company.objects.create(name=name)
    if not name in hashtagsPool:
        hashtagsPool[name]=0
    tweepy.addHashtagToFilter(name)
    return getStatus(request)

def removeCompany(request, name):
    """
    to be called by a a web service.
    removes a new Company/hashtag <name> to the DB and to twitter filter
    returns the status of the system
    """
    global tweepy
    name = name.upper()
    Company.objects.filter(name=name).delete()
    tweepy.removeHashtagFromFilter(name)
    hashtagsPool.pop(name, None)
    return getStatus(request)


def forceRefresh(request=None):
    """
    syncronizes the twitter filter and the DB and triggers a DB refresh
    returns the status of the system
    """
    global tweepy, lastUpdate
    dbCompanies = Company.objects.all()
    filterHashtags = tweepy.filter

    companyNames = []
    for company in dbCompanies:
        companyNames.append('#' + company.name)

    notInFilter = set(companyNames) - set(filterHashtags)
    notInDb = set(filterHashtags) - set(companyNames)

    for hashtag in notInDb:
        removeCompany(request, hashtag)

    for company in notInFilter:
        addCompany(request, company[1:])

    refreshProductionCounter()
    lastUpdate = datetime.datetime.now()
    return getStatus(request)


def refreshProductionCounter():
    """
    updates the DB with the counters stored in memory. resets the counters in memory
    """
    global hashtagsPool
    for hashtag,counter in hashtagsPool.iteritems():
        Hashtag.objects.create(name=hashtag,tweetsQuantity=counter)
        hashtagsPool[hashtag]=0



def startServer(request):
    """
    to be called as a web service
    starts Twitter streaming server
    forces a syncronization/refresh
    starts job threads if needed
    returns the status of the system
    """
    global tweepy
    tweepy.restartStreamer()
    #logger.info("Twitter Server initialized")
    #isServerRunning = True
    forceRefresh(request)

    if not isThreadAlive(threadTwtReaderName):
        tweetsReaderTask = threading.Thread(target=readTweetsJob, name=threadTwtReaderName)
        tweetsReaderTask.daemon=False
        tweetsReaderTask.start()

    if not isThreadAlive(threadProdUpdater):
        updateDBdataTask = threading.Thread(target=updateProductionJob, name=threadProdUpdater)
        updateDBdataTask.daemon=False
        updateDBdataTask.start()

    return getStatus(request)


def stopServer(request):
    """
    stops the twitter streaming server
    """
    global tweepy
    tweepy.stopStreamer()
    #logger.info("Twitter Server initialized")
    #isServerRunning = False
    return getStatus(request)

def isThreadAlive(name):
    """
    checks if thread <name> is still alive
    """
    for t in threading.enumerate():
        if t.getName() == name and t.isAlive():
            return True
    return False

def getStatus(request):
    """
    to be called as a web service
    returns system status encapsulated as a http response
    """
    readerThreadAlive = isThreadAlive(threadTwtReaderName)

    updaterThreadAlive = isThreadAlive(threadProdUpdater)

    status = {"LocalCounter" : hashtagsPool,
              "threadTwtReaderName": readerThreadAlive,
              "threadProdUpdater": updaterThreadAlive,
              "intervalBetweenAutoRefreshes" : intervalBetweenAutoRefreshes,
              "lastUpdate" : lastUpdate,
              }

    return HttpResponse(str(status))

def setAutoRefreshDelay(request, interval):
    global intervalBetweenAutoRefreshes
    try:
        intervalBetweenAutoRefreshes = int(interval)
    except Exception as e:
        pass
    return getStatus(request)


def getCompaniesProduction(request, fromDateStr, toDateStr, granularity):
    """
    to be called as a web service
    returns the counters of tweets in a give time range [<fromDateStr> - <toDateStr>], with a given granularity
        {
            Q - counters summed by intervals of 15 minutes
            H - counters summed by hour
            D - counters summed by day
            W - counters summed by week
            M - counters summed by month
        }
    """
    toDate, fromDate = None, None
    
    if toDateStr is None:
        toDate = datetime.date.today()
    else:
        toDate = datetime.datetime.strptime(toDateStr, '%Y-%m-%d').date()

    if fromDateStr is None:
        fromDate = datetime.date(1900,01,01)
    else:
        fromDate = datetime.datetime.strptime(fromDateStr, '%Y-%m-%d').date()

    productionWithinDates = Hashtag.objects.filter(startingTime__range=[fromDate,toDate]).order_by('name')

    result = {}

    #per every 15 minutes
    if granularity == 'Q':

        for ht in productionWithinDates:
            minutes = 0
            if ht.startingTime.minute >= 45:
                minutes = 45
            elif ht.startingTime.minute >= 30:
                minutes = 30
            elif ht.startingTime.minute >= 15:
                minutes = 15


            dateTimeSlot = str(datetime.datetime(ht.startingTime.date().year,
                                             ht.startingTime.date().month,
                                             ht.startingTime.date().day,
                                             ht.startingTime.hour,
                                             minutes))

            if not ht.name in result:
                result[ht.name] = {dateTimeSlot : 0}
            elif not dateTimeSlot in result[ht.name]:
                result[ht.name][dateTimeSlot] = 0

            result[ht.name][dateTimeSlot] += ht.tweetsQuantity

    #per every hour
    elif granularity == 'H':
        for ht in productionWithinDates:
            dateTimeSlot = str(datetime.datetime(ht.startingTime.date().year,
                                             ht.startingTime.date().month,
                                             ht.startingTime.date().day,
                                             ht.startingTime.hour))

            if not ht.name in result:
                result[ht.name] = {dateTimeSlot : 0}
            elif not dateTimeSlot in result[ht.name]:
                result[ht.name][dateTimeSlot] = 0

            result[ht.name][dateTimeSlot] += ht.tweetsQuantity

    #per day
    elif granularity=='D':
        for ht in productionWithinDates:
            dateTimeSlot = datetime.datetime(ht.startingTime.date().year,
                                             ht.startingTime.date().month,
                                             ht.startingTime.date().day)

            if not ht.name in result:
                result[ht.name] = {dateTimeSlot : 0}
            elif not dateTimeSlot in result[ht.name]:
                result[ht.name][dateTimeSlot] = 0

            result[ht.name][dateTimeSlot] += ht.tweetsQuantity

    #per every week
    elif granularity == 'W':
        pass

    #per every month
    elif granularity == 'M':
        for ht in productionWithinDates:
            dateTimeSlot = datetime.datetime(ht.startingTime.date().year,
                                             ht.startingTime.date().month,
                                             ht.startingTime.date().day)

            if not ht.name in result:
                result[ht.name] = {dateTimeSlot : 0}
            elif not dateTimeSlot in result[ht.name]:
                result[ht.name][dateTimeSlot] = 0

            result[ht.name][dateTimeSlot] += ht.tweetsQuantity

    else:
        pass

    return HttpResponse(json.dumps(result))




