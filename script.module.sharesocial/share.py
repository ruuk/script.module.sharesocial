import os, sys, traceback, threading, time
import xbmc, xbmcgui #@UnresolvedImport
from lib import ShareSocial
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
			for k in jobs.keys():
				j = jobs[k]
				if not j.isAlive():
					sofar += 1
					if j.result:
						names[names.index(j.remember.name)] = '[COLOR FF00FF00]%s[/COLOR]' % j.remember.name 
					else:
						names[names.index(j.remember.name)] = '[COLOR FFFF0000]%s[/COLOR]' % j.remember.name
					del jobs[k]
			dialog.update(int((sofar*100.0)/total),' - '.join(names))
			time.sleep(0.2)
		for j in self.jobs: results.append(j.result)
		return results
	
class FeedWindow(xbmcgui.WindowXML):
	def __init__( self, *args, **kwargs ):
		self.feeds = ShareSocial.ShareManager().getProviders('feed')
		self.started = False
		self.items = []
		xbmcgui.WindowXML.__init__( self, *args, **kwargs )

	def onInit(self):
		if not self.started: self.fillFeedList()
		self.started = True
		
	def extractEmbeddedURL(self,url):
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
		
			
	def fillFeedList(self):
		if not self.feeds: return
		#TODO: Do each feed in a thread 
		items = {}
		ct = 1
		pool = ArrayPool()
		for f in self.feeds:
			pcall = f.getProvideCall()
			pool.addJob(f.provideWithCall,f,'feed',pcall)
		fct = len(self.feeds)
		afterpct = int((fct * 100.0) / (fct + 1))
		left = float(100 - afterpct)
		dialog = xbmcgui.DialogProgress()
		try:
			results = pool.getResult(dialog)
			c=0
			for result in results:
				if not result or result.error:
					if result:
						LOG('No result for feed: %s - %s' % (result.target.name,result.error))
					else:
						LOG('No result for feed' )
					c+=1
					continue
				lastpct = int((c * left) / fct)
				dialog.update(afterpct + lastpct,result.target.name,'Preparing feed...')
				feedIcon = result.target.getIcon()
				#print '%s : %s' % (result.target.name, feedIcon)
				c+=1
				for r in result.items:
					text = r.get('text','').replace('\t','  ').replace('\n','[CR]')
					username = r.get('user')
					userimage = r.get('usericon')
					timestamp = r.get('unixtime')
					textimage = self.extractEmbeddedURL(r.get('textimage'))
					item = xbmcgui.ListItem()
					item.setThumbnailImage(userimage)
					item.setLabel('[CR]' + text)
					item.setLabel2('[CR][COLOR FF880000]%s[/COLOR]' % username)
					item.setProperty('picture',textimage)
					item.setProperty('feedicon',feedIcon)
					comments = self.buildCommentsDisplay('[CR][COLOR FF880000]%s: [/COLOR]%s' % (username,text),r.get('comments'))
					item.setProperty('comments',comments)
					items[timestamp + (1.0/ct)] = (item,r) #add decimal to make unique
					ct+=1
			
			keys = items.keys()
			keys.sort(reverse=True)
			wlist = self.getControl(120)
			wlist.reset()
			self.items = []
			for k in keys:
				wlist.addItem(items[k][0])
				self.items.append(items[k][1])
		finally:
			dialog.close()
		
	def itemClicked(self):
		idx = self.getControl(120).getSelectedPosition()
		item = self.getControl(120).getListItem(idx)
		r = self.items[idx]
		commsObj = r.get('comments')
		if not commsObj: return
		commsObj.getComments()
		item.setProperty('comments',self.buildCommentsDisplay('[CR][COLOR FF880000]%s: [/COLOR]%s' % (r.get('user'),r.get('text','')),commsObj))
	
	def buildCommentsDisplay(self,msg,commsObj):
		ret = msg + '[CR][CR]'
		if not commsObj: return ret
		if commsObj.items:
			for c in commsObj.items:
				ret += '[COLOR FF008800]%s:[/COLOR] %s[CR][CR]' % (c.get('user',''),c.get('text',''))
		else:
			if commsObj.count:
				if commsObj.isReplyTo:
					ret += 'Click to view the target status of this reply.'
				else:
					ret += '%s comments - click to view.' % commsObj.count
		return ret
				
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
	
	def doContextMenu(self):
		menu = ShareSocial.ChoiceMenu('Options')
		menu.addItem('update_status','Update Status')
		result = menu.getResult()
		if not result: return
		if result == 'update_status':
			updateStatus()
		
def openFeedWindow():
	windowFile = 'ShareSocial-Feed.xml'
	w = FeedWindow(windowFile , xbmc.translatePath(ShareSocial.__addon__.getAddonInfo('path')), 'Default')
	w.doModal()
	del w

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
		msg = xbmc.executehttpapi( "FileCopy(%s,%s)" % ( source, destination ) ).replace( "<li>", "" )
	finally:
		dialog.close()
		
	LOG( "Remote Copy: %s - copy(%s,%s)" % ( msg, source, destination ))
	return os.path.exists(destination)

def clearDirFiles(filepath):
	if not os.path.exists(filepath): return
	for f in os.listdir(filepath):
		f = os.path.join(filepath,f)
		if os.path.isfile(f): os.remove(f)
		
def processShare():
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
	share.share(True)
if __name__ == '__main__':
	if len(sys.argv) > 1:
		if sys.argv[1] == 'install_skin_mod':
			ShareSocial.installSkinMod()
		elif sys.argv[1] == 'undo_skin_mod':
			ShareSocial.installSkinMod(True)
		else:
			processShare()
	else:
		registerAsShareTarget()
		#updateStatus()
		openFeedWindow()
