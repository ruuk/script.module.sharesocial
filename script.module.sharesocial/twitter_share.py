import httplib, os
from twitter import TwitterSession, LOG, getUserList, TwitterUser
from twython import twython

from lib import ShareSocial

def scaleImage(path):
	try:
		import Image
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
	
def doShareSocial():
	return TwitterTargetFunctions()

class TwitterTargetFunctions(ShareSocial.TargetFunctions):
	def getUsers(self,share=None):
		ulist = []
		for ID in getUserList():
			user = TwitterUser(ID=ID).load()
			ulist.append({'id':user.ID,'name':user.name,'photo':user.photo})
		return ulist
	
	def share(self,share,user=None):
		try:
			return self.handleShare(share,user)
		except twython.TwythonError, e:
			return share.failed(e.msg)
		except:
			error = ShareSocial.ERROR('Twitter: Share failed')
			return share.failed(error)
	
	def getFeedComments(self,commsObj):
		replyToID = commsObj.callbackDict.get('replyToID')
		session = TwitterSession()
		status = session.twit.showStatus(id=replyToID)
		#print status
		commsObj.addItem(status['user'].get('name','ERROR'),status['user'].get('profile_image_url'),status.get('text','ERROR'),status.get('created_at'))
		return commsObj
			
	def provide(self,getObject,ID=None):
		session = TwitterSession(ID=ID,require_existing_user=True)
		if not session.twit: return getObject.error('NOUSERS')
		user = {'id':session.user.ID,'name':session.user.name,'photo':session.user.photo}
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
				share = None
				if ent:
					#print ent
					media = ent.get('media')
					urls = ent.get('urls')
					if media:
						if media[0].get('type') == 'photo':
							textimage = media[0].get('media_url')
							share = ShareSocial.getShare('script.module.sharesocial', 'image')
							share.media = textimage
							share.page = media[0].get('expanded_url')
							share.title = "From Twitter via XBMC"
							share.thumbnail = textimage
							#print textimage
							#print media[0].get('expanded_url')
							#print media[0].get('url')
							#print media[0].get('display_url')
					elif urls:
						url = urls[0].get('expanded_url')
						if 'youtu.be' in url or 'youtube.com' in url:
							ID = ShareSocial.extractYoutubeIDFromPageURL(url)
							textimage = ShareSocial.getYoutubeThumbURL(ID)
							share = ShareSocial.getShare('script.module.sharesocial', 'video')
							share.media = ShareSocial.getYoutubeSWFUrl(ID)
							share.page = url
							share.title = "From Youtube via Twitter via XBMC"
							share.thumbnail = textimage
							
				replyToID = r.get('in_reply_to_status_id')
				if replyToID:
					commsObj = getObject.getCommentsList()
					commsObj.count = 1
					commsObj.isReplyTo = True
					commsObj.callbackDict['replyToID'] = replyToID
					
				getObject.addItem(username,userimage,text,timestamp,textimage,comments=commsObj,client_user=user,share=share)
		return getObject
				
	def handleShare(self,share,ID):
		httplib.HTTPConnection.progressCallback = share.progressCallback
		
		session = TwitterSession(ID=ID)
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