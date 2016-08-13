#Thank you to http://www.beartech.ca/writeups/2015/4/4/python-instagram-api-to-like-pictures-by-tag for providing me with base code to get this app up and running

from instagram.client import InstagramAPI

from pprint import pprint
import sys

from nltk.sentiment.vader import SentimentIntensityAnalyzer
#Make sure the vader_lexicon.txt file is in wherePythonPackagesAreStored/nltk/sentiment
#You can download it here: https://github.com/nltk/nltk/blob/develop/nltk/sentiment/vader_lexicon.txt
#See here for example usage: http://www.nltk.org/howto/sentiment.html


import requests
import ast
from datetime import datetime
import time

from IPython.core.display import HTML

#NVD3 can be found here: https://python-nvd3.readthedocs.org/en/latest/index.html
from nvd3 import pieChart
from nvd3 import multiBarChart



import numpy as np

sentimentAnalyzer = SentimentIntensityAnalyzer()
client_id = ''
client_secret = ''
access_token = ''

api = InstagramAPI(client_id=client_id, client_secret=client_secret, access_token = access_token)




def getNumberOfLikes(media_id):
	return api.media_likes(media_id = media_id.id)


def getUser(media_id):
	return media_id.user


def getAllInfoOnThisUser(thisUser): 

	#Although the Instagram Python API has cleaner syntax, some functions prove much easier to perform with direct HTML calls to Instagram's API

	webpageReturnedForThisUser = 'https://api.instagram.com/v1/users/' + thisUser.id + '/?access_token=2236032195.1677ed0.a5d8ac7ad8b84b72801597cbdd9e97dd'
	
	r = requests.get(webpageReturnedForThisUser)
	dictOfInfoOnThisUser = ast.literal_eval(r.text)

	numberOfUsersWhoFollowThisUser = dictOfInfoOnThisUser['data']['counts']['followed_by']
	numberOfUsersThisUserFollows = dictOfInfoOnThisUser['data']['counts']['follows']
	numberOfPosts = dictOfInfoOnThisUser['data']['counts']['media']


	return numberOfUsersWhoFollowThisUser, numberOfUsersThisUserFollows, numberOfPosts


def getCaption(media_id):
	return media_id.caption.text


def getSentiment(caption): 
	#I am using Valence Aware Dictionary for sEntiment Reasoning (VADER) (http://comp.social.gatech.edu/papers/icwsm14.vader.hutto.pdf)
	#from Python's Natural Languange Toolkit (NLTK) to perform sentiment analysis

	sentimentForThisCaption = sentimentAnalyzer.polarity_scores(caption.replace('#', ''))

	sentimentScores = [sentimentForThisCaption['pos'], sentimentForThisCaption['neg'], sentimentForThisCaption['neu']]

	return sentimentScores



def getSentimentClassification(sentimentScores):
	if sentimentScores[0] > .01 and sentimentScores[1] < .01: #If the text is pretty positive and only a little negative, call it positive
		return 1
	elif sentimentScores[1] > .01 and sentimentScores[0] < .01: #If the text is pretty negative and only a little positive, call it negative
		return -1

	else: #Otherwise, call it neutral
		return 0


def getTimeStamp(media_id):
	return media_id.created_time


def outputPieChart(numberPositive, numberNegative, numberNeutral):
	chart = pieChart(name='pieChart', 
                 height=700, width=700)


	color_list = ['#00E600', 'red', '#00CCFF']
	  

	xdata = ["Positive", "Negative", "Neutral"]
	ydata = [numberPositive, numberNegative, numberNeutral]

	extra_serie = {"tooltip": {"y_start": "", "y_end": " posts"},  "color_list": color_list}
	chart.add_serie(y=ydata, x=xdata, extra=extra_serie)
	chart.buildhtml()

	output_file = open('temp.html', 'w')
	output_file.write(chart.htmlcontent)

	output_file.close()

	#Edit HTML file directly to add functionality that Python library does not support
	f = open('temp.html', 'r') 

	data = f.readlines()

	relevantLine = data[20];
	relevantLine = relevantLine[:relevantLine.find(';')] + '\n' + '.showLabels(true)\n' + '.labelType("percent")\n;\n' 
       
	data[20] = relevantLine

	newFile = open('frequencyPieChart.html', 'w')

	newFile.writelines( data )
	newFile.close()


def outputWeightedSentimentDistribution(listOfWeightedScores):

	hist, edges = np.histogram(listOfWeightedScores, bins=25) #Discretize data


	bin_ticks = [round((edges[i] + edges[i + 1])/2, 2)for i in range(len(edges) - 1)]


	chart = multiBarChart(width=700, height=700, margin_bottom = 60)


	xdata = bin_ticks

	ydata1 = [int(hist[i]) for i in range(len(hist))] / sum(hist)

	chart.add_serie(name="Weighted Sentiment Scores", y=ydata1, x=xdata)

	chart.create_x_axis(name = 'Weighted Sentiment Score')
	chart.create_y_axis(name = 'Relative Frequency')

	chart.buildhtml()


	output_file = open('temp.html', 'w')
	output_file.write(chart.htmlcontent)

	output_file.close()

	#Edit HTML file directly to add functionality that Python library does not support

	f = open('temp.html', 'r') 

	data = f.readlines()

	relevantLine = data[21];
	relevantLine =  "chart.xAxis \n .axisLabel('Weighted Sentiment Score') \n chart.yAxis  \n .axisLabel('Relative Frequency') \n"
       
	data[21] = relevantLine

	newFile = open('weightedDistibutionBarChart.html', 'w')

	newFile.writelines( data )
	newFile.close()



def main():

	numberOfPostsForThisTag = 0

	dictOfAllInfo = {}	
	'''
	{
		media_id: {
						'Likes': number of likes on this post
						'User': user who posted this post
						'UserFollowers': number of users who follow this user
						'UserFollows': number of users this user follows
						'Posts': number of posts this user has made
						'Caption': caption on this post
						'Sentiment Scores': percentage positive, negative, and neutral 
						'Sentiment Classification': -1 for negative, 0 for neutral, 1 for positive
						'Weighted Sentiment Score': Sentiment Classification * Likes
				  }

	}

	'''	
	
	sentimentFreqDict = {
		
		'pos': 0,
		'neg': 0,
		'neu': 0
	}

	listOfWeightedScores = []


	now = datetime.now() #Current time

	tag = 'capitalone'

	media_ids,next = api.tag_recent_media(tag_name=tag, count=800)

	counter = 0

	timeRangeInDays= 14 #Get all instagram posts in past timeRangeInDays days
	haveExceededTimeRange = False

	while next :

		if haveExceededTimeRange:
			break

		if counter > 0: #The first page requires special care
			more_media, next = api.tag_recent_media(tag_name = tag, with_next_url = next)#, max_tag_id=max_tag)

		else:
			more_media = media_ids


		for media_id in more_media: #Each post on instagram is identified by a unique media id

			numberOfPostsForThisTag += 1


			if not media_id: #If this is not a valid media id
				continue

			if media_id.id not in dictOfAllInfo.keys():
				dictOfAllInfo[media_id.id] = {}


			timeStampForThisPost = getTimeStamp(media_id)
			print('THIS POST IS FROM: ' + str(timeStampForThisPost))
			daysAgoThisWasPosted = (now - timeStampForThisPost).days

			if daysAgoThisWasPosted > timeRangeInDays: #Get only the past timeRangeInDays days of posts
				haveExceededTimeRange = True
				break

			dictOfAllInfo[media_id.id] ['Likes'] = getNumberOfLikes(media_id)	#Get number of likes on this post


			dictOfAllInfo[media_id.id] ['User'] = getUser(media_id)	#Get user who posted this post


			numberOfUsersWhoFollowThisUser, numberOfUsersThisUserFollows, numberOfPosts = getAllInfoOnThisUser(dictOfAllInfo[media_id.id] ['User'] ) #Get information about this user

			dictOfAllInfo[media_id.id] ['UserFollowers'] = numberOfUsersWhoFollowThisUser
			dictOfAllInfo[media_id.id] ['UserFollows'] = numberOfUsersThisUserFollows
			dictOfAllInfo[media_id.id] ['Posts'] = numberOfUsersWhoFollowThisUser


			dictOfAllInfo[media_id.id] ['Caption'] = getCaption(media_id)	#Get caption on this post

		
			dictOfAllInfo[media_id.id] ['Sentiment Scores']  = getSentiment(dictOfAllInfo[media_id.id] ['Caption'] )	#Get sentiment scores for the caption


			dictOfAllInfo[media_id.id] ['Sentiment Classification']  = getSentimentClassification(dictOfAllInfo[media_id.id] ['Sentiment Scores'] ) #Get sentiment classification for the caption

			if dictOfAllInfo[media_id.id] ['Sentiment Classification'] == 1:
				sentimentFreqDict['pos'] += 1

			elif dictOfAllInfo[media_id.id] ['Sentiment Classification'] == -1:
				sentimentFreqDict['neg'] += 1

			else:
				sentimentFreqDict['neu'] += 1


			dictOfAllInfo[media_id.id] ['Weighted Sentiment Score'] = dictOfAllInfo[media_id.id] ['Sentiment Classification'] * len(dictOfAllInfo[media_id.id] ['Likes'] )


			listOfWeightedScores.append(dictOfAllInfo[media_id.id] ['Weighted Sentiment Score'])


		counter += 1

	print('NUMBER OF POSITIVE POSTS: ' + str(sentimentFreqDict['pos']))
	print('NUMBER OF NEGATIVE POSTS: ' + str(sentimentFreqDict['neg']))
	print('NUMBER OF NEUTRAL POSTS: ' + str(sentimentFreqDict['neu']))


	print('MEAN WEIGHTED SENTIMENT SCORE: ' + str(np.mean(listOfWeightedScores)))
	outputPieChart(sentimentFreqDict['pos'], sentimentFreqDict['neg'], sentimentFreqDict['neu'])
	outputWeightedSentimentDistribution(listOfWeightedScores)

	import webbrowser
	import os
	webbrowser.open_new('file://' + os.path.realpath('frequencyPieChart.html'))
	webbrowser.open_new('file://' + os.path.realpath('weightedDistibutionBarChart.html'))





main()