import httplib, os
from twitter import TwitterSession, LOG
from twython import twython

def scaleImage(path):
	try:
		import Image
		from lib import ShareSocial
		LOG('Imported PIL')
		large = Image.open(path)
		w,h = large.size
		# Twitter scales to width of 500 so might as well do it here
		new_h = int((500 * h)/w)
		LOG('Twitter: Scaling image from %sx%s to %sx%s' % (w,h,500,new_h))
		small = large.resize((500,new_h))
		newPath = os.path.join(ShareSocial.CACHE_PATH,'twitterResizeImage.jpg')
		small.save(newPath,'jpeg')
		return newPath
	except ImportError:
		LOG('Could not import PIL')
		return path
	except:
		ShareSocial.ERROR('Twitter: Failed to scale image')
		return path
	
def doShareSocial(share):
	try:
		return handleShare(share)
	except twython.TwythonError, e:
		return share.failed(e.msg)
	except:
		from lib import ShareSocial
		error = ShareSocial.ERROR('Twitter: Share failed')
		return share.failed(error)

def doShareSocialGetFeedComments(commsObj,replyToID):
	session = TwitterSession()
	status = session.twit.showStatus(id=replyToID)
	#print status
	commsObj.addItem(status['user'].get('name','ERROR'),status['user'].get('profile_image_url'),status.get('text','ERROR'),status.get('created_at'))
	return commsObj
		
def doShareSocialProvide(getObject):
	session = TwitterSession()
	if getObject.type == 'feed':
		results = session.twit.getHomeTimeline(include_entities=1)
		for r in results:
			text = r.get('text','ERROR')
			#print '%s : %s' % (r.get('id'),text)
			username = r['user'].get('name','ERROR')
			userimage = r['user'].get('profile_image_url')
			timestamp = r.get('created_at')
			textimage = ''
			ent = r.get('entities')
			commsObj = None
			if ent:
				media = ent.get('media')
				if media: 
					textimage = media[0].get('media_url')
			replyToID = r.get('in_reply_to_status_id')
			if replyToID:
				commsObj = getObject.getCommentsList()
				commsObj.count = 1
				commsObj.isReplyTo = True
				commsObj.setCallback(doShareSocialGetFeedComments,replyToID)
				
			getObject.addItem(username,userimage,text,timestamp,textimage,comments=commsObj)
	return getObject
			
def handleShare(share):
	httplib.HTTPConnection.progressCallback = share.progressCallback
	
	session = TwitterSession()
	if share.shareType == 'status':
		if not share.message: share.askMessage()
		params={'status':share.message}
		if share.latitude:
			params['lat'] = share.latitude
			params['long'] = share.longitude
		session.twit.updateStatus(**params)
		return share.succeeded()
	elif share.shareType == 'imagefile':
		path = share.media
		if os.path.getsize(path) > 716800:
			path = scaleImage(path)
			if os.path.getsize(path) > 716800:
				return share.failed('Twitter requires image size less than 700KB')
		share.askMessage()
		params={'status':share.message}
		if share.latitude:
			params['lat'] = share.latitude
			params['long'] = share.longitude
		session.twit.updateStatusWithMedia(path,params=params)
		return share.succeeded()
	elif share.shareType == 'image' or share.shareType == 'video':
		share.askMessage()
		params={'status':share.message + ' - ' + session.twit.shortenURL(share.page or share.media)}
		if share.latitude:
			params['lat'] = share.latitude
			params['long'] = share.longitude
		session.twit.updateStatus(**params)
		return share.succeeded()
	else:
		return share.failed('Cannot Share This Type') # This of course shoudn't happen
	
	return share.failed('Unknown Error') # This of course shoudn't happen