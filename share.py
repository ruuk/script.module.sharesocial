import os, sys, traceback, threading, time, binascii
import xbmc, xbmcgui, xbmcvfs #@UnresolvedImport
from lib import ShareSocial, window
import urllib

DIALOG = None

def LOG(text):
	xbmc.log('ShareSocial: share.py: %s' % text)

def ERROR(message):
	LOG(message)
	traceback.print_exc()
	return str(sys.exc_info()[1])
		
class WorkerThread(threading.Thread):
	def __init__(self,group=None, target=None, name=None, args=(), kwargs={}):
		self.result = None
		self.remember = None
		threading.Thread.__init__(self,group=group, target=target, name=name, args=args, kwargs=kwargs)
		self.__args = args
		self.__kwargs = kwargs
		self.__target = target
		
	def run(self):
		kwargs = self.__kwargs
		args = self.__args
		self.result = self.__target(*args,**kwargs)
		
class ArrayPool():
	def __init__(self):
		self.jobs = []
		
	def addJob(self,function,remember,*args,**kwargs):
		t = WorkerThread(target=function,args=args,kwargs=kwargs)
		t.remember = remember
		self.jobs.append(t)
		t.start()
		
	def getResult(self,dialog=None):
		results = []
		dialog.create('Getting Feeds')
		dialog.update(0,'Please wait...','Getting feeds...')
		sofar = 0
		total = len(self.jobs) + 1
		names = []
		jobs = {}
		for j in self.jobs:
			names.append(j.remember.name)
			jobs[j.remember.name] = j
		while jobs:
			if dialog.iscanceled():
				for j in self.jobs:
					if j.isAlive(): break
				else:
					return None
			for k in jobs.keys():
				j = jobs[k]
				if not j.isAlive():
					del jobs[k]
					sofar += 1
					if j.result:
						if j.result._error:
							LOG('Failed to get feed %s: %s' % (j.remember.name,j.result._error))
							if j.result._error == 'NOUSERS':
								names[names.index(j.remember.name)] = '[COLOR FFFFFF00]%s[/COLOR]' % j.remember.name
							else:
								names[names.index(j.remember.name)] = '[COLOR FFFF0000]%s[/COLOR]' % j.remember.name
						else:
							names[names.index(j.remember.name)] = '[COLOR FF00FF00]%s[/COLOR]' % j.remember.name	
					else:
						names[names.index(j.remember.name)] = '[COLOR FFFF0000]%s[/COLOR]' % j.remember.name
			dialog.update(int((sofar*100.0)/total),' - '.join(names))
			time.sleep(0.2)
		for j in self.jobs: results.append(j.result)
		return results

class FeedListItem():
	def __init__(self,feeditem):
		self.item = xbmcgui.ListItem()
		self.feeditem = feeditem
		self.timestamp = 0
		if feeditem: self.fillItem()
		
	def fillItem(self):
		r = self.feeditem
		text = r.get('text','').replace('\t','  ').replace('\n','[CR]')
		username = r.get('user')
		userimage = r.get('usericon')
		self.timestamp = r.get('unixtime')
		textimage = extractEmbeddedURL(r.get('textimage',''))
		item = self.item
		item.setThumbnailImage(userimage)
		item.setLabel('[CR]' + text)
		item.setLabel2(username)
		item.setProperty('picture',textimage)
		item.setProperty('usericon',(r.get('client') or {}).get('photo',''))
		comments = buildCommentsDisplay('[CR][COLOR FF880000]%s: [/COLOR]%s' % (username,text),r.comments)
		item.setProperty('comments',comments)
		
	def __getattr__(self, prop):
		return self.item.__getattribute__(prop)
		
class ExtendedControlList():
	def __init__(self,window,controlID):
		self.control = window.getControl(controlID)
		self.items = []
		
	def getSelectedItem(self):
		pos = self.control.getSelectedPosition()
		return self.items[pos]
		
	def addItem(self,item):
		self.control.addItem(item.item)
		self.items.append(item)
	
	def addItems(self,items):
		for item in items:
			self.add(item)
	
	def reset(self):
		self.items = []
		self.control.reset()

def durationToText(unixtime):
	disp = []
	days = int(unixtime/86400)
	if days: disp.append('%sd' % days)
	left = unixtime % 86400
	hours = int(left/3600)
	if hours: disp.append('%sh' % hours)
	left = left % 3600
	mins = int(left/60)
	if mins: disp.append('%sm' % mins)
	sec = int(left % 60)
	if sec: disp.append('%ss' % sec)
	return ' '.join(disp)

def durationToShortText(unixtime):
	disp = []
	days = int(unixtime/86400)
	if days: return '%sd' % days
	left = unixtime % 86400
	hours = int(left/3600)
	if hours: return '%sh' % hours
	left = left % 3600
	mins = int(left/60)
	if mins: return '%sm' % mins
	sec = int(left % 60)
	if sec: return '%ss' % sec
	return ' '.join(disp)
	

def extractEmbeddedURL(url):
	if not url: return url
	new = urllib.unquote(url.split('http',1)[-1])
	if 'http://' in new:
		url = 'http://' + new.split('http://',1)[-1]
	elif 'https://' in new:
		url = 'https://' + new.split('https://',1)[-1]
	else:
		return url
	if url.endswith('.jpg'): return url
	if url.endswith('.gif'): return url
	if '.jpg' in url: return url.split('.jpg',1)[0] + '.jpg'
	if '.gif' in url: return url.split('.gif',1)[0] + '.gif'
	return url
	
def buildCommentsDisplay(msg,commsObj):
	ret = msg + '[CR][CR]'
	if not commsObj: return ret
	if commsObj.items:
		if commsObj.count > len(commsObj.items): ret += '[CR][COLOR FF666666][--- Click to view all %s comments ---][/COLOR][CR][CR][CR]' % commsObj.count
		for c in commsObj.items:
			ret += '[COLOR FF008800]%s:[/COLOR] %s[CR][CR]' % (c.get('user',''),c.get('text',''))
	else:
		if commsObj.count:
			if commsObj.isReplyTo:
				ret += 'Click to view the target status of this reply.'
			else:
				ret += '[COLOR FF666666][--- %s comments - click to view ---][/COLOR]' % commsObj.count
	return ret
	
class FeedWindow(xbmcgui.WindowXML):
	def __init__( self, *args, **kwargs ):
		self.feeds = ShareSocial.ShareManager().getProviders('feed')
		self.started = False
		self.provisions = []
		self.items = []
		self.saveFile = os.path.join(ShareSocial.MAIN_PATH,'FeedData')
		self.feedList = None
		xbmcgui.WindowXML.__init__( self, *args, **kwargs )

	def shouldRefresh(self,last):
		return time.time() - last > 300
	
	def onInit(self):
		if self.started: return
		self.feedList = ExtendedControlList(self,120)
		try:
			last = self.load()
		except:
			ERROR('Could not load feeds')
			last = 0
		if last: self.fillFeedList(self.provisions)
		if self.shouldRefresh(last): self.fillFeedList()
		self.setFocusId(120)
		self.started = True
		
	def save(self):
		sections = [str(int(time.time()))]
		for p in self.provisions:
			sections.append(p.toString())
		out = '\n@--SECTION--@\n'.join(sections)
		f = open(self.saveFile,'w')
		f.write(out)
		f.close()
		
	def load(self):
		if not os.path.exists(self.saveFile): return 0
		f = open(self.saveFile,'r')
		data = f.read()
		f.close()
		
		sections = data.split('\n@--SECTION--@\n')
		first = sections.pop(0)
		unixtime = int(first)
		for section in sections:
			fp = ShareSocial.FeedProvision().fromString(section)
			if fp: self.provisions.append(fp)
		return unixtime
		
	def getFeedUserIDs(self,feed):
		users = ShareSocial.getSetting('feed_users_' + feed.addonID,[])
		IDs = []
		for u in users:
			IDs.append(self.decodeUser(u).get('id'))
		return IDs
	
	def fillFeedList(self,results=None):
		#TODO: clean this up so I don't need this sorta crap
		passed_results = results and True or False
		if not self.feeds: return
		items = {}
		ct = 1
		if not results:
			blocked = ShareSocial.getSetting('blocked_feeds',[])
			pool = ArrayPool()
			for f in self.feeds:
				if f.addonID in blocked: continue
				pcall = f.getProvideCall()
				pool.addJob(f.provideWithCall,f,'feed',pcall,self.getFeedUserIDs(f))
		fct = len(self.feeds)
		afterpct = int((fct * 100.0) / (fct + 1))
		left = float(100 - afterpct)
		dialog = xbmcgui.DialogProgress()
		dialog.create('Getting Feeds')
		now = time.daylight and (time.time() + time.altzone + 3600) or int(time.mktime(time.gmtime()))
		try:
			if not results:
				results = pool.getResult(dialog)
				self.provisions = results
			c=0
			for result in results:
				if not result.target: continue
				if not result or result._error:
					if result:
						LOG('No result for feed: %s - %s' % (result.target.name,result._error))
					else:
						LOG('No result for feed')
					c+=1
					continue
				lastpct = int((c * left) / fct)
				dialog.update(afterpct + lastpct,result.target.name,'Preparing feed...')
				feedIcon = result.target.getIcon()
				#print '%s : %s' % (result.target.name, feedIcon)
				c+=1
				for r in result.items:
					item = FeedListItem(r)
					item.setProperty('feedicon',feedIcon)
					item.setProperty('ago',durationToShortText(now - item.timestamp) + ' ago')
					items[item.timestamp + (1.0/ct)] = item #add decimal to make unique
					ct+=1
			
			keys = items.keys()
			keys.sort(reverse=True)
			self.feedList.reset()
			for k in keys:
				#print "%s - %s" % (k,durationToShortText(now - items[k].timestamp))
				self.feedList.addItem(items[k])
			if not keys:
				fi = FeedListItem(None)
				fi.setLabel('[CR]NO FEEDS')
				self.feedList.addItem(fi)
			elif not passed_results:
				self.save()
		finally:
			dialog.close()
		
	def itemClicked(self):
		item = self.feedList.getSelectedItem()
		f = item.feeditem
		commsObj = f.comments
		if not commsObj: return
		commsObj.getComments()
		item.setProperty('comments',buildCommentsDisplay('[CR][COLOR FF880000]%s: [/COLOR]%s' % (f.get('user'),f.get('text','')),commsObj))
				
	def onFocus( self, controlId ):
		self.controlId = controlId
		
	def onAction(self,action):
		if action == 92 or action == 10:
			self.close()
		elif action == 117:
			self.doContextMenu()
		elif action == 7:
			self.itemClicked()
		
	def onClick( self, controlID ):
		if controlID == 120:
			self.itemClicked()
	
	def setUser(self):
		feed = True
		while feed:
			menu = ShareSocial.ChoiceMenu('Add Users: Choose Feed')
			for f in self.feeds:
				show = ''
				users = ShareSocial.getSetting('feed_users_' + f.addonID,[])
				if users:
					sh = []
					for u in users:
						sh.append(self.decodeUser(u).get('name','ERROR'))
					show = ' (%s)' % ', '.join(sh)
				menu.addItem(f,f.name + show)
			feed = menu.getResult()
			if not feed: return
			submenu = ShareSocial.ChoiceMenu('Add Users: Choose User')
			for u in feed.functions().getUsers():
				submenu.addItem(u,u.get('name','ERROR'))
			user = submenu.getResult()
			if not user: return
			self.setFeedUser(feed, user)
		
	def removeUser(self):
		feed = True
		while feed:
			menu = ShareSocial.ChoiceMenu('Remove Users: Choose Feed')
			for f in self.feeds:
				show = ''
				users = ShareSocial.getSetting('feed_users_' + f.addonID,[])
				if not users: continue
				
				sh = []
				us = []
				for u in users:
					user = self.decodeUser(u)
					sh.append(user.get('name','ERROR'))
					us.append(user)
				show = ' (%s)' % ', '.join(sh)
				menu.addItem((f,us),f.name + show)
			
			if not menu.items:
				xbmcgui.Dialog().ok('No Users','No users to remove :)')
				return
				
			feed_users = menu.getResult()
			if not feed_users: return
			feed, users = feed_users
			submenu = ShareSocial.ChoiceMenu('Remove Users: Choose User')
			for u in users:
				submenu.addItem(u,u.get('name','ERROR'))
			user = submenu.getResult()
			if not user: return
			self.removeFeedUser(feed, user)
		
	def decodeUser(self,data):
		return ShareSocial.dictFromString(binascii.unhexlify(data))
		
	def encodeUser(self,user):
		return binascii.hexlify(ShareSocial.dictToString(user))
			
	def setFeedUser(self,feed,user):
		key = 'feed_users_' + feed.addonID
		users = ShareSocial.getSetting(key,[])
		for u in users:
			if user.get('id') == self.decodeUser(u).get('id'): return
		users.append(self.encodeUser(user))
		ShareSocial.setSetting(key,users)
		
	def removeFeedUser(self,feed,user):
		key = 'feed_users_' + feed.addonID
		users = ShareSocial.getSetting(key,[])
		i = 0
		for u in users:
			if self.decodeUser(u).get('id') == user.get('id'):
				users.pop(i)
				ShareSocial.setSetting(key,users)
				return
			i+=1
		
	def manageFeedsMenu(self):
		menu = ShareSocial.ChoiceMenu('Feed Options')
		menu.addItem('show_hide', 'Show/Hide Feeds')
		menu.addItem('add_users','Add Users To Feed')
		menu.addItem('remove_users','Remove Users From Feed')
		res = True
		while res:
			res = menu.getResult()
			if not res: return
			
			if		res == 'show_hide': self.showHideFeedMenu()
			elif 	res == 'add_users': self.setUser()
			elif	res == 'remove_users': self.removeUser()
		
	def showHideFeedMenu(self):
		feed = True
		while feed:
			menu = ShareSocial.ChoiceMenu('Toggle Visibility')
			feedlist = ShareSocial.getSetting('blocked_feeds',[])
			for f in self.feeds:
				blocked = ''
				if f.addonID in feedlist: blocked = ' [HIDDEN]'
				menu.addItem(f, f.name + blocked, f.iconPath)
			feed = menu.getResult()
			if not feed: return
			if feed.addonID in feedlist:
				self.showFeed(feed)
			else:
				self.hideFeed(feed)
		
	def hideFeed(self,feed):
		feedlist = ShareSocial.getSetting('blocked_feeds',[])
		if feed.addonID in feedlist: return
		feedlist.append(feed.addonID)
		ShareSocial.setSetting('blocked_feeds',feedlist)
		
	def showFeed(self,feed):
		feedlist = ShareSocial.getSetting('blocked_feeds',[])
		if feed.addonID in feedlist: feedlist.pop(feedlist.index(feed.addonID))
		ShareSocial.setSetting('blocked_feeds',feedlist)
		
	def doContextMenu(self):
		menu = ShareSocial.ChoiceMenu('Options')
		menu.addItem('update_status','Update Status')
		menu.addItem('refresh','Refresh Feeds')
		menu.addItem('manage_feeds','Manage Feeds')
		menu.addItem('settings','Settings')
		f = self.feedList.getSelectedItem().feeditem
		if f:
			if f.share and ShareSocial.shareTargetAvailable(f.share.shareType,'script.module.sharesocial'):
				menu.addItem(None,None)
				menu.addItem('share','Share %s...' % f.share.shareType)
			if f.share: f.share.updateData()
			if f.share and f.share.shareType == 'video':
				menu.addItem('watch_video','Watch Video')
			elif f.share and f.share.shareType == 'image':
				if f.share.media:
					menu.addItem('view_image','View Image')
			elif f.get('textimage'):
				menu.addItem('view_picture','View Image')
			
		result = menu.getResult()
		if not result: return
		if result == 'update_status':
			updateStatus()
		elif result == 'refresh':
			self.fillFeedList()
		elif result == 'manage_feeds':
			self.manageFeedsMenu()
		elif result == 'settings':
			ShareSocial.__addon__.openSettings() #@UndefinedVariable
		elif result == 'share':
			f.share.share()
		elif result == 'watch_video':
			self.showVideo(f.share.media)
		elif result == 'view_image':
			self.showImage(f.share.media)
		elif result == 'view_picture':
			url = self.feedList.getSelectedItem().getProperty('picture')
			print url
			self.showImage(url)
	
	def showVideo(self,source):
		xbmc.executebuiltin('PlayMedia(%s)' % source)
		
	def showImage(self,source):
		target_path = os.path.join(ShareSocial.CACHE_PATH,'slideshow')
		if not os.path.exists(target_path): os.makedirs(target_path)
		ShareSocial.clearDirFiles(target_path)
		ShareSocial.getFile(source,os.path.join(target_path,'image.jpg'))
		xbmc.executebuiltin('SlideShow(%s)' % target_path)
		
def openFeedWindow():
	windowFile = 'ShareSocial-Feed.xml'
	window.openWindow(FeedWindow, windowFile, 'Default')

def askType():
	options = ('Video','Audio','Image')
	optNames = ('video','audio','image')
	idx = xbmcgui.Dialog().select("Select share type:",options)
	if idx < 0: return None
	return optNames[idx]

def getTypeFromExt(ext):
	ext = ext.lower()
	video = xbmc.getSupportedMedia('video').replace('.','').split('|')
	audio = xbmc.getSupportedMedia('music').replace('.','').split('|')
	image = xbmc.getSupportedMedia('picture').replace('.','').split('|')
	if ext in video:
		return 'videofile'
	elif ext in audio:
		return 'audiofile'
	elif ext in image:
		return 'imagefile'
	return None

def getTypeFromFolderPath(path):
	media = path.split('.',2)[:2][-1]
	if media in ('image','video','audio'): return media
	media = path.split('db://',1)[0].replace('music','audio')
	if media in ('image','video','audio'): return media
	return None

def progressCallback(level,total,message):
	if not DIALOG: return
	if DIALOG.iscanceled(): return False
	DIALOG.update(int((level*100)/total),'Downloading...')
	return True

def copyRemote( source, destination ):
	try:
		dialog = xbmcgui.DialogProgress()
		dialog.create('Network Copy','Copying file to local filesystem,','please wait...')
		dialog.update(0)
		success = xbmcvfs.copy(source,destination)
		#msg = xbmc.executehttpapi( "FileCopy(%s,%s)" % ( source, destination ) ).replace( "<li>", "" )
	finally:
		dialog.close()
		
	LOG( "Remote Copy: %s - copy(%s,%s)" % ( success, source, destination ))
	return os.path.exists(destination)

def clearDirFiles(filepath):
	if not os.path.exists(filepath): return
	for f in os.listdir(filepath):
		f = os.path.join(filepath,f)
		if os.path.isfile(f): os.remove(f)
		
def processSkinShare():
	LOG('Processing share')
	
	argNames = ['ignore','apiver','addonID','addonName','ext','imagepath','title','folder','filename','label','path']
	args = {}
	
	for s in sys.argv:
		if not argNames: break
		argName = argNames.pop(0)
		args[argName] = s
	
	path = args.get('folder','') + args.get('filename','') # Because some paths get screwed up from the filenameandpath infolabel
	if 'plugin://' in path: path = args.get('path','') # Because we need this for the URL
	print 'Test: %s' % args
	print sys.argv
	
	shareType = None
	if args.get('imagepath'):
		shareType = 'imagefile'
		path = args.get('imagepath','')
		LOG('shareType: %s - determined by PicturePath' % shareType)
	else:
		ext = args.get('ext')
		if ext: shareType = getTypeFromExt(ext)
		if shareType:
			LOG('shareType: %s - determined by FileExtension' % shareType)
		else:
			shareType = getTypeFromFolderPath(args.get('folderpath'))
			if shareType:
				LOG('shareType: %s - determined from FolderPath' % shareType)
			else:
				shareType = askType()
				if shareType:
					LOG('shareType: %s - determined by asking user' % shareType)
				else:
					return
		
	share = ShareSocial.getShare(args['addonID'], shareType)
	share.title = args.get('title') or args.get('label') or args.get('filename','')
	share.media = path
	share.sourceName = args.get('addonName')
	lpath = None
	if share.shareType in ('imagefile','videofile','audiofile'):
		#TODO: check for cahed file before deciding it's remote
		if share.mediaIsRemote():
			LOG('Share is media and remote.')
			if share.mediaIsWeb():
				LOG('Share is media and on the web. Looking for local copy...')
				lpath = ShareSocial.getCachedPath(share.media)
				if lpath:
					LOG('Found cached content')
				else:
					LOG('Not cached - downloading...')
					targetPath = os.path.join(ShareSocial.CACHE_PATH,'tempmediafile.' + args.get('ext',''))
					try:
						global DIALOG
						DIALOG = xbmcgui.DialogProgress()
						DIALOG.create('Download','Waiting for download...')
						DIALOG.update(0,'Waiting for download...')
						lpath = ShareSocial.getFile(share.media, targetPath, progressCallback)
					except:
						error = ERROR('Download failed!')
						xbmcgui.Dialog().ok('Failed','Download failed.', error)
						return
					finally:
						DIALOG.close()
					
				if lpath:
					LOG('Converting content to local file')
					alt = share.getCopy()
					alt.shareType = alt.shareType.replace('file','')
					share.media = lpath
					share.addAlternate(alt)
				else:
					LOG('Could not download content - changing type to %s' % share.shareType.replace('file',''))
					share.shareType = share.shareType.replace('file','')
			else:
				LOG('Share is media and on the local network. Looking for local copy...')
				lpath = ShareSocial.getCachedPath(share.media)
				if lpath:
					LOG('Found cached content')
				else:
					LOG('Not cached - copying to local filesystem...')
					lpath = os.path.join(ShareSocial.CACHE_PATH,'tempmediafile.' + args.get('ext',''))
					got = copyRemote(share.media,lpath)
					if not got:
						LOG('Failed to copy remote file')
						lpath = None
						
				if lpath:
					share.media = lpath
				else:
					xbmcgui.Dialog().ok('Failed','Unable to share remote file.')
					return
				
	share.share()
	clearDirFiles(ShareSocial.CACHE_PATH)	

def processShare():
	try:
		share = ShareSocial.Share().fromString(sys.argv[2].replace(':',','))
	except:
		ERROR('share.py: processShare(): Failed to create share from string')
	share.share()
	
def registerAsShareTarget():
	target = ShareSocial.getShareTarget()
	target.addonID = 'script.module.sharesocial'
	target.name = 'Twitter'
	target.importPath = 'twitter_share'
	target.iconPath = os.path.join(ShareSocial.__addon__.getAddonInfo('path'),'twitter.png')
	target.shareTypes = ['status','imagefile','image','video']
	target.provideTypes = ['feed']
	ShareSocial.registerShareTarget(target)
	LOG('Registered as share target for Twitter')
	
def updateStatus():
	if not ShareSocial.shareTargetAvailable('status','script.module.sharesocial'):
		xbmcgui.Dialog().ok('Failed','No status update targets available.')
		return
	share = ShareSocial.getShare('script.module.sharesocial', 'status')
	share.askMessage('Enter Status Message')
	if not share.message: return
	share.share(withall=True)
	
def addTwitterUser():
	from twitter import TwitterSession
	TwitterSession(add_user=True)
	
if __name__ == '__main__':
	if len(sys.argv) > 1:
		if sys.argv[1] == 'install_skin_mod':
			ShareSocial.installSkinMod()
		elif sys.argv[1] == 'undo_skin_mod':
			ShareSocial.installSkinMod(True)
		elif sys.argv[1] == 'add_twitter_user':
			addTwitterUser()
		elif sys.argv[1] == 'share':
			processShare()
		elif sys.argv[1] == 'font_select_dialog':
			window.fontSelectDialog(sys.argv[2])
		elif sys.argv[1] == 'set_font_setting':
			window.setFontSetting(sys.argv[2],sys.argv[3])
		else:
			processSkinShare()
	else:
		registerAsShareTarget()
		#updateStatus()
		openFeedWindow()
