# -*- coding: utf-8 -*-
import xbmcaddon, xbmc, xbmcgui #@UnresolvedImport
import os, sys, urllib2, traceback, re, time, binascii
import iso8601

__author__ = 'ruuk'
__url__ = 'http://code.google.com'
__date__ = '02-13-2012'
__version__ = '0.1.5'
__addon__ = xbmcaddon.Addon(id='script.module.sharesocial')
__lang__ = __addon__.getLocalizedString

APILEVEL = 1

MAIN_PATH = xbmc.translatePath(__addon__.getAddonInfo('profile'))
TARGETS_PATH = os.path.join(MAIN_PATH,'targets')
CACHE_PATH = os.path.join(MAIN_PATH,'cache')
if not os.path.exists(CACHE_PATH): os.makedirs(CACHE_PATH)

def LOG(text):
	xbmc.log('ShareSocial: %s' % text)
	
def ERROR(message):
	LOG(message)
	traceback.print_exc()
	return str(sys.exc_info()[1])

def getSetting(key,default=None):
	string = __addon__.getSetting(key)
	if not string: return default
	if isinstance(default,list): return string.split(',')
	if isinstance(default,int): return int(string)
	if isinstance(default,float): return float(string)
	return string

def setSetting(key,value):
	if isinstance(value,list): value = ','.join(value)
	if not hasattr(value,'encode'): value = unicode(value)
	__addon__.setSetting(key,value)
	
def getShare(source,sharetype):
	return Share(source,sharetype)

def getShareTarget():
	return ShareTarget()

def registerShareTarget(target):
	ShareManager().registerShareTarget(target)
	
def shareTargetAvailable(share_type,sourceID):
	return ShareManager().shareTargetAvailable(share_type,sourceID)

def getCachedPath(path):
	thumbs = xbmc.translatePath('special://thumbnails')
	cachename = xbmc.getCacheThumbName(path)
	fullPath = os.path.join(thumbs,cachename[0],cachename)
	if os.path.exists(fullPath): return fullPath
	return None

def fixExtension(content_type,fn):
		if not 'image' in content_type: return
		ext = content_type.split('/',1)[-1]
		if not ext in 'jpeg,png,gif,bmp': return
		if ext == 'jpeg': ext = 'jpg'
		fn = os.path.splitext(fn)[0] + '.' + ext
		return fn
	
def getFile(url,target_file,progress_callback=None):
		if not url: return
		try:
			request = urllib2.urlopen(url)
			target_file = fixExtension(request.info().get('content-type',''),target_file)
		except:
			LOG('ERROR: urlopen() in getFile() - URL: %s' % url)
			return ''
		f = open(target_file,"wb")
		try:
			total = int(request.info()['content-length'])
		except:
			total = 0
			progress_callback = None
		chunk = 65536
		sofar = 0
		while True:
			data = request.read(chunk)
			if not data: break
			f.write(data)
			sofar += chunk
			if progress_callback:
				if not progress_callback(sofar,total,''): break
			
		f.close()
		return target_file

def clearDirFiles(filepath):
	if not os.path.exists(filepath): return
	for f in os.listdir(filepath):
		f = os.path.join(filepath,f)
		if os.path.isfile(f): os.remove(f)
			
def doKeyboard(prompt,default='',hidden=False):
	keyboard = xbmc.Keyboard(default,prompt)
	keyboard.setHiddenInput(hidden)
	keyboard.doModal()
	if not keyboard.isConfirmed(): return None
	return keyboard.getText()

class ChoiceMenu():
	def __init__(self,caption):
		self.caption = caption
		self.items = []
		self.display = []
		self.icons = []
		
	def addItem(self,ID,display,icon=None):
		if not ID: return self.addSep()
		self.items.append(ID)
		self.display.append(display)
		self.icons.append(icon)
		
	def addSep(self):
		pass
	
	def getChoiceIndex(self):
		return xbmcgui.Dialog().select(self.caption,self.display)
	
	def getResult(self):
		idx = self.getChoiceIndex()
		if idx < 0: return None
		return self.items[idx]

class EmbeddedChoiceDialog(xbmcgui.WindowXMLDialog):
	def __init__( self, *args, **kwargs ):
		self.result = None
		self.display = kwargs.get('display')
		self.icons = kwargs.get('icons')
		self.caption = kwargs.get('caption')
		xbmcgui.WindowXMLDialog.__init__( self, *args, **kwargs )
	
	def onInit(self):
		items = []
		for d,i in zip(self.display,self.icons):
			item = xbmcgui.ListItem(label=d,thumbnailImage=i or '')
			items.append(item)
			
		self.getControl(120).addItems(items)
		self.getControl(300).setLabel(self.caption)
		
	def onAction(self,action):
		if action == 92 or action == 10:
			self.close()
		elif action == 7:
			self.finish()
	
	def onClick( self, controlID ):
		if controlID == 120:
			self.finish()
			
	def finish(self):
		self.result = self.getControl(120).getSelectedPosition()
		self.close()
		
	def onFocus( self, controlId ): self.controlId = controlId
		
class EmbeddedChoiceMenu(ChoiceMenu):
	def getResult(self):
		windowFile = 'ShareSocial-ShareProgressChoiceMenu.xml'
		w = EmbeddedChoiceDialog(windowFile , xbmc.translatePath(__addon__.getAddonInfo('path')), 'Default',display=self.display,icons=self.icons,caption=self.caption)
		w.doModal()
		result = w.result
		del w
		if result == None: return None
		return self.items[result]
		
	
class ProgressWindow(xbmcgui.WindowXML):
	def __init__( self, *args, **kwargs ):
		self.soFar = 0
		self.total = 1
		self.barMax = 642.0
		self.canceled = False
		self.bar = None
		self.barLabel = None
		self.msgLabel = None
		self.line1 = ''
		self.line2 = ''
		self.line3 = ''
		self._barhidden = False
		
		xbmcgui.WindowXML.__init__( self, *args, **kwargs )
	
	def onInit(self):
		self.bar = self.getControl(200)
		self.barLabel = self.getControl(201)
		self.msgLabel = self.getControl(205)
			
	def onFocus( self, controlId ):
		self.controlId = controlId
		
	def onAction(self,action):
		if action == 92 or action == 10:
			self.doCancel()
		
	def onClick( self, controlID ):
		pass
	
	def doCancel(self):
		self.canceled = True
		self.barLabel.setLabel()
		
	def calcPercent(self,sofar,total):
		return int((sofar * 100.0)/total)
	
	def setIcons(self,source,target):
		self.getControl(202).setImage(source)
		self.getControl(203).setImage(target)
		
	def create(self,heading,line1='', line2='', line3=''):
		self.show()
		self.onInit()
		self.updateProgress(0, 1, line1, line2, line3)
	
	def update(self,percent,line1='', line2='', line3=''):
		self.updateProgress(percent, 100, line1, line2, line3)
	
	def updateProgress(self,sofar,total,line1='', line2='', line3=''):
		if self.canceled: return
		self.line1 = line1 or self.line1
		self.line2 = line2 or self.line2
		self.line3 = line3 or self.line3
		barWidth = int((sofar * self.barMax) / total)
		if barWidth > self.barMax:
			barWidth = int(self.barMax)
			pct = 100
		else:
			pct = self.calcPercent(sofar,total)
		self.bar.setWidth(barWidth)
		self.barLabel.setLabel('%s%%' % pct)
		self.msgLabel.setLabel('%s[CR]%s[CR]%s' % (self.line1,self.line2,self.line3))
	
	def hideBar(self,hide):
		self._barhidden = hide
		self.bar.setVisible(not hide)
		
	def iscanceled(self):
		return self.canceled
	
	def close(self):
		xbmcgui.WindowXML.close(self)
		del self

def openProgress():
	windowFile = 'ShareSocial-ShareProgress.xml'
	w = ProgressWindow(windowFile , xbmc.translatePath(__addon__.getAddonInfo('path')), 'Default')
	return w
			
class ShareFailure():
	def __init__(self,code,reason,error=''):
		self.code = code
		self.reason = reason
		self.error = error
	
	def __nonzero__(self):
		return False
	
def convertTimestampToUnix(timestamp):
	if isinstance(timestamp,float): return int(timestamp)
	if isinstance(timestamp,int): return timestamp
	if timestamp.isdigit(): return int(timestamp)
	try:
		return time.mktime(iso8601.parse_date(timestamp).timetuple())
	except:
		pass
	
	try:
		offset = 0
		try: offset = int(re.search('([-+]\d{2}):?\d{2}',timestamp).group(1))
		except: pass
		return int(time.mktime(time.strptime(re.sub('\+\d+','',timestamp)))) + (offset * 3600)
	except:
		timestamp = int(time.time())
	return timestamp

def valToString(val):
	if hasattr(val,'encode'):
		try:
			return val.encode('utf-8')
		except:
			LOG('valToString() encode error')
			return val
	return str(val).encode('utf-8')

def dictFromString(data,val_is_hex=True):
	if not data: return {}
	theDict = {}
	for keyval in data.split(','):
		key,val = keyval.split('=',1)
		if key.startswith('dict___'):
			key = key[7:]
			val = dictFromString(binascii.unhexlify(val),val_is_hex)
			theDict[key] = val
		elif key.startswith('list___'):
			key = key[7:]
			val = binascii.unhexlify(val).split(',')
			theDict[key] = val
		else:
			if val_is_hex:
				theDict[key] = binascii.unhexlify(val)
			else:
				theDict[key] = val.decode('utf-8')
	return theDict

def dictToString(data_dict):
	if not data_dict: return ''
	ret = []
	try:
		for key,val in data_dict.items():
			if val == None:
				continue
			elif isinstance(val,dict):
				val = dictToString(val)
				key = 'dict___' + key
			elif isinstance(val,list):
				val = ','.join(val)
				key = 'list___' + key
			ret.append('%s=%s' % (key,binascii.hexlify(valToString(val))))
	except:
		print data_dict
		raise
	return ','.join(ret)

class FeedItem(dict):
	def __init__(self, *args, **kwargs ):
		dict.__init__(self, *args, **kwargs )
		self.share = None
		self.comments = None
		
	def toString(self):
		ret = []
		if self.comments: ret.append('comments=%s' % binascii.hexlify(self.comments.toString()))
		if self.share: ret.append('share=%s' % binascii.hexlify(self.share.toString()))
		ret.append('data=%s' % binascii.hexlify(dictToString(self)))
		return ','.join(ret)
	
	def fromString(self,kv_list,target=None):
		for kv in kv_list.split(','):
			key,val = kv.split('=',1)
			val = binascii.unhexlify(val)
			if key == 'data': self.update(dictFromString(val))
			elif key == 'share': self.share = Share().fromString(val)
			elif key == 'comments': self.comments = CommentsList(target).fromString(val)
			ut = self.get('unixtime')
			if ut: self['unixtime'] = int(float(ut))
		return self
	
class CommentsList():
	def __init__(self,target=None):
		self.target = target
		self.count = 0
		self.isReplyTo = False
		self.items = []
		self.callbackDict = {}
		
	def clear(self):
		self.items = []
		
	def setGetCommentsData(self,data):
		self._commentsCallbackData = data
	
	def addItem(self,user,usericon,text,timestamp):
		timestamp = convertTimestampToUnix(timestamp)
		self.count += 1
		self.items.append({'user':user,'usericon':usericon,'text':text,'unixtime':timestamp})
		
	def getComments(self):
		if not self.count: return False
		if len(self.items) >= self.count: return False
		LOG('Getting comments via callback')
		self.count = 0
		dialog = xbmcgui.DialogProgress()
		dialog.create('Getting Comments')
		dialog.update(0,'Getting comments','Please wait...')
		try:
			self.target.functions().getFeedComments(self)
		except:
			ERROR('Getting comments failed!')
		finally:
			dialog.close()
		return True
					
	def toString(self):
		lines = ['count=%s,isReplyTo=%s,callbackDict=%s' % (self.count,self.isReplyTo,binascii.hexlify(dictToString(self.callbackDict)))]
		for c in self.items:			
			lines.append(dictToString(c))
		return '\n'.join(lines)
	
	def fromString(self,data):
		lines = data.splitlines()
		first = dictFromString(lines.pop(0),False)
		self.count = int(first.get('count',0))
		self.isReplyTo = first.get('isReplyTo') == 'True'
		self.callbackDict = dictFromString(binascii.unhexlify(first.get('callbackDict','')))
		for line in lines:
			self.items.append(dictFromString(line))
		for i in self.items:
			ut = i.get('unixtime')
			if ut: i['unixtime'] = int(float(ut))
		return self
						
class FeedProvision():
	def __init__(self,target=None):
		self.target = target
		self.type = 'feed'
		self._error = None
		self.items = []
	
	def error(self,error):
		self._error = error
		return self
	
	def addItem(self,user,usericon,text,timestamp,textimage,comments=None,share=None,client_user={}):
		timestamp = convertTimestampToUnix(timestamp)
		f = FeedItem({'user':user,'usericon':usericon,'text':text,'unixtime':timestamp,'textimage':textimage,'client':client_user})
		f.comments = comments
		f.share = share
		self.items.append(f)
		
	def getCommentsList(self):
		return CommentsList(self.target)
	
	def failed(self,error='Unknown'):
		self.error = error
		return self
	
	def toString(self):
		lines = ['target=%s,type=%s' % (self.target.addonID,self.type)]
		for i in self.items:
			lines.append(i.toString())
		return '\n'.join(lines)
	
	def fromString(self,data):
		lines = data.splitlines()
		first = dictFromString(lines.pop(0),False)
		addonID = first.get('target',0)
		self.target = ShareManager().getTarget(addonID)
		print addonID
		print self.target
		for line in lines:
			self.items.append(FeedItem().fromString(line,self.target))
		return self

class Share():
	def __init__(self,sourceID=None,sharetype=None):
		self.sourceID = sourceID
		self.shareType = sharetype
		self.html = '' # HTML representation of content (or actual html/text in the case of html/text share)
		self.sourceName = '' # Name of source ie: flickr, Facebook, YouTube
		self.title = '' # Title of the share
		self.thumbnail = '' # Thumbnail image of the share
		self.media = '' # Link to the actual media or path to file (if applicable)
		self.embed = '' # Embed code if applicable (for target optional use)
		self.swf = '' # Link to flash swf file if applicable
		self.page = '' # Link to page for this media, if available
		self.latitude = 0 # Geo latutude, if available
		self.longitude = 0 # Geo longitude, if available
		self.altitude = 0 # Geo altitude, if available
		self.message = '' # Default message
		self.alternates = []
		self.callbackData = {}
		
		self._shareManager = None
		self._failed = []
		self._succeeded = []
		self._error = None
	
	def getIcon(self):
		if self.sourceID.startswith('skin.'): return os.path.join(__addon__.getAddonInfo('path'),'xbmc.png')
		return xbmcaddon.Addon(id=self.sourceID).getAddonInfo('icon') or ''
	
	def failed(self,message='Unknown Reason',error=None):
		self._failed.append(message)
		self._error = error
		return self
		
	def succeeded(self,message=''):
		self._succeeded.append(message)
		return self
		
	def finishedMessage(self):
		if self._failed: return self._failed[0]
		if self._succeeded: return self._succeeded[0]
		
	def progressCallback(self,*args,**kwargs):
		return self._shareManager.progressCallback(*args,**kwargs)
	
	def getCopy(self):
		import copy
		return copy.deepcopy(self)
	
	def addAlternate(self,share):
		self.alternates.append(share)
		
	def mediaIsRemote(self):
		return not os.path.exists(self.media)
	
	def mediaIsWeb(self):
		if self.media.startswith('http:/'): return True
		if self.media.startswith('https:/'): return True
		if self.media.startswith('ftp:/'): return True
		return False

	def askMessage(self,heading='Enter Message'):
		self.message = doKeyboard(heading,self.message) or self.message
		
	def getOptionsMenu(self,caption='Options'):
		return EmbeddedChoiceMenu(caption)
	
	def link(self):
		return self.page or self.media
	
	def asHTML(self,use_media=False):
		thumb = use_media and self.media or self.thumbnail
		html = self.html or '<div style="text-align: center; float: left;"><a href="%s"><img src="%s" /><br /><br />%s</a></div>' % (self.link(),thumb,self.title)
		print html
		return html
	
	def getLatitude(self):
		if isinstance(self.latitude,float): return self.latitude
		try:
			self.latitude = float(self.latitude)
		except:
			self.latitude = 0
		return self.latitude
	
	def getLongitude(self):
		if isinstance(self.longitude,float): return self.longitude
		try:
			self.longitude = float(self.longitude)
		except:
			self.longitude =  0
		return self.longitude
	
	def getAltitude(self):
		if isinstance(self.altitude,float): return self.altitude
		try:
			self.altitude = float(self.altitude)
		except:
			self.altitude =  0
		return self.altitude
	
	def updateData(self):
		if self.callbackData:
			target = ShareManager().getTarget(self.sourceID)
			target.functions().getShareData(self)
			
	def share(self,target_id=None,withall=False):
		self.updateData()
		ShareManager().doShare(self,target_id,withall)
		
	def toString(self):
		d = self.__dict__.copy()
		for k in d.keys():
			if k.startswith('_'): d.pop(k)
		d.pop('alternates')
		return dictToString(d)
	
	def fromString(self,string):
		d = dictFromString(string)
		self.__dict__.update(d)
		return self
	
	def toPluginRunscriptString(self):
		return 'XBMC.RunScript(script.module.sharesocial,share,%s)' % self.toString().replace(',',':')
	
############################################################--------------------####
#                                                              TargetFunctions              ((o))->
############################################################--------------------####
class TargetFunctions():
	def share(self,share,ID):
		"""
			Must return the share by calling either
			
			return share.success()
			return share.failed(message)
			
			where message is a message displayable to the user
		"""
		return share.failed('Not Handled')
	
	def getFeedComments(self,commsObj,post): return commsObj
	def provide(self,ID): pass
	def getShareData(self,share): return share
	def getUsers(self,share=None):
		"""
			Must return a list of dicts in the form of
			{'id':user_id,'name':user_display_name,'photo':user_photo_url}
			
			id is REQUIRED and will be (possibly) passed to other functions
			name is REQUIRED and will be used when showing relevant data to the user
			photo is OPTIONAL
			
		"""
		return None
	
	def setHTTPConnectionProgressCallback(self,share):
		import httplib, StringIO
		from array import array
		
		def send(self, data):
			"""Send `data' to the server."""
			if self.sock is None:
				if self.auto_open:
					self.connect()
				else:
					raise httplib.NotConnected()
	
			if self.debuglevel > 0:
				print "send:", repr(data)
			blocksize = 8192
			total = 1
			progressCallback = self.progressCallback
			if not hasattr(data,'read') and not isinstance(data, array) and hasattr(data,'len'):
				total = len(data)
				data = StringIO.StringIO(data)
			elif hasattr(data,'read') and not isinstance(data, array):
				try:
					total = int(data.info()['content-length'])
				except:
					total = 1
					progressCallback = None
			if hasattr(data,'read') and not isinstance(data, array):
				if self.debuglevel > 0: print "sendIng a read()able"
				datablock = data.read(blocksize)
				sofar = len(datablock)
				while datablock:
					self.sock.sendall(datablock)
					if progressCallback:
						if not progressCallback(sofar,total): break
					datablock = data.read(blocksize)
					sofar += blocksize
			else:
				self.sock.sendall(data)
		httplib.HTTPConnection.send = send
		httplib.HTTPConnection.progressCallback = share.progressCallback

############################################################--------------------####
#                                                                ShareTarget             ((o))
############################################################--------------------####
class ShareTarget():
	def __init__(self,target_data=None):
		self.addonID = ''
		self.shareTypes = []
		self.provideTypes = []
		self.name = ''
		self.importPath = ''
		self.iconPath = ''
		self._functions = None
		self.user = {}
		if target_data: self.fromString(target_data)
	
	def getIcon(self):
		return self.iconPath or xbmcaddon.Addon(id=self.addonID).getAddonInfo('icon') or ''
		
	def canShare(self,shareType):
		if shareType in self.shareTypes: return True
		return False
	
	def canProvide(self,provideType):
		if provideType in self.provideTypes: return True
		return False
	
	def getIconPath(self):
		if self.iconPath: return self.iconPath
		iconPath = os.path.join(xbmcaddon.Addon(self.addonID).getAddonInfo('path'),'icon.png')
		if os.path.exists(iconPath): return iconPath
		return None
	
	def fromString(self,target_data):
		kvdict = {}
		for keyval in target_data.split(':::'):
			key,val = keyval.split('=',1)
			kvdict[key] = val
		self.addonID = kvdict.get('addonID')
		self.name = kvdict.get('name')
		self.importPath = kvdict.get('importPath')
		self.shareTypes = kvdict.get('shareTypes','').split(',')
		self.provideTypes = kvdict.get('provideTypes','').split(',')
		self.iconPath = kvdict.get('iconPath')
		return self
	
	def toString(self):
		return 'addonID=%s:::name=%s:::importPath=%s:::shareTypes=%s:::provideTypes=%s:::iconPath=%s' % (	self.addonID,
																											self.name,
																											self.importPath,
																											','.join(self.shareTypes),
																											','.join(self.provideTypes),
																											self.iconPath )
	
	def getFunctions(self):
		module = os.path.basename(self.importPath)
		subPath = os.path.dirname(self.importPath)
		addonPath = xbmcaddon.Addon(self.addonID).getAddonInfo('path')
		importPath = os.path.join(addonPath,subPath)
		sys.path.insert(0,importPath)
		try:
			mod = __import__(module)
			reload(mod)
			del sys.path[0]
			return mod.doShareSocial()
		except ImportError:
			ERROR('ShareTarget.getFunctions(): Error importing module %s for share target %s.' % (self.importPath,self.addonID))
			#self.unRegisterShareTarget(self)
			return ShareFailure('targetImportFailure','Failed To Import Share Target')
		except:
			error = ERROR('ShareTarget.getFunctions(): Error during target sharing import')
			return ShareFailure('targetImportError','Error In Target Sharing Import: %s' % error,error)
		
	def functions(self):
		if self._functions: return self._functions
		self._functions = self.getFunctions()
		return self._functions
	
	def provide(self,provideType):
		if provideType == 'feed':
			getObject = FeedProvision(self)
		try:
			return self.functions().provide(getObject)
		except:
			err = ERROR('ShareTarget.provide(): Error in target provide() function')
			return getObject.failed(err)
		
	def getProvideCall(self):
		return self.functions().provide
		
	def provideWithCall(self,provideType,provideCall,userIDs=None):
		if provideType == 'feed':
			getObject = FeedProvision(self)
		try:
			if not userIDs: return provideCall(getObject)
			for ID in userIDs:
				provideCall(getObject,ID)
			return getObject
		except:
			err = ERROR('ShareTarget.provideWithCall(): Error in target provide() function')
			return getObject.failed(err)
			
	def doShare(self,share):
		try:
			return self.functions().share(share,self.user.get('id'))
		except:
			ERROR('ShareTarget.doShare(): Error in target share() function')
			return share.failed('Error in target share() function')
		
	def register(self):
		ShareManager().registerShareTarget(self)

############################################################--------------------####
#                                                              ShareManager                      !!
############################################################--------------------####
class ShareManager():
	sharetypes = {	'image':1,
					'audio':1,
					'video':1,
					'link':1,
					'imagefile':1,
					'videofile':1,
					'audiofile':1,
					'binaryfile':1,
					'html':1,
					'text':1,
					'status':1}
	
	def __init__(self):
		self.dialog = None
		self.readTargets()
	
	def doShare(self,share,target_id=None,withall=False):
		try:
			self.dialog = openProgress()
			self.dialog.create('Sharing','Starting...')
			self.dialog.setIcons(share.getIcon(),'')
			share = self._doShare(share,target_id,withall)
		finally:
			self.dialog.close()
	
		if not share._failed:
			xbmcgui.Dialog().ok('Finished','Sharing complete!',share.finishedMessage())
			LOG('Sharing: Done')
			return True
		else:
			xbmcgui.Dialog().ok('Failed','Sharing failed!',share.finishedMessage())
			LOG('Sharing: Failed - %s' % share.finishedMessage())
			return False
	
	def _doShare(self,share,target_id=None,withall=False):
		share._shareManager = self
		if target_id:
			target = self.getTarget(target_id)
			if not target: return share.failed('Share Target Not Found')
			if not target.canShare(share):
				return share.failed('Type Not Supported By Target')
		else:
			target = self.askForTarget(share,withall)
		if not target: return share.failed('User Canceled')
		if isinstance(target,list):
			for t in target:
				self.dialog.setIcons(share.getIcon(),t.getIcon())
				t.doShare(share)
			return share
		else:
			self.dialog.setIcons(share.getIcon(),target.getIcon())
			return target.doShare(share)
		
	def askForTarget(self,share,withall=False):
		menu = EmbeddedChoiceMenu('Share to:')
		for tkey in self.targets:
			target = self.targets[tkey]
			if target.addonID != share.sourceID or share.sourceID == 'script.module.sharesocial':
				for s in [share] + share.alternates:
					if target.canShare(s.shareType):
						users = target.functions().getUsers(share) or [{}]
						for user in users:
							show = target.name
							if user: show = '%s (%s)' % (target.name,user.get('name',''))
							menu.addItem((target,user),show,target.getIcon())
						break
					
		if withall:
			menu.addItem(menu.items[:],'-All-')
		target_user = menu.getResult()
		if not target_user or isinstance(target_user,list): return target_user
		target, user = target_user
		target.user = user
		return target
	
	def shareTargetAvailable(self,share_type,sourceID):
		for target in self.targets.values():
			if target.canShare(share_type) and target.addonID != sourceID: return True
		return False
				
	def registerShareTarget(self,target):
		self.targets[target.addonID] = target
		self.writeTargets()
		
	def unRegisterShareTarget(self,target):
		if target.addonID in self.targets:
			del self.targets[target.addonID]
			self.writeTargets()
	
	def getProviders(self,provideType):
		providers = []
		for t in self.targets.values():
			if t.canProvide(provideType):
				providers.append(t)
		return providers
	
	def getTarget(self,addonID):
		return self.targets.get(addonID)
	
	def readTargets(self):
		self.targets = {}
		if not os.path.exists(TARGETS_PATH): return
		tf = open(TARGETS_PATH,'r')
		tdata = tf.read()
		tf.close()
		for t in tdata.splitlines():
			if not t: continue
			target = ShareTarget(t)
			self.targets[target.addonID] = target
			
	def writeTargets(self):
		out = ''
		for t in self.targets.values():
			out += t.toString() + '\n'
		tf = open(TARGETS_PATH,'w')
		tf.write(out)
		tf.close()
		
	def progressCallback(self,level,total,message='Please wait...',m2='',m3='',hide=None):
		total = total or 1
		if not self.dialog: return True
		if self.dialog.iscanceled(): return False
		if hide is not None: self.dialog.hideBar(hide)
		self.dialog.updateProgress(level,total,message,m2,m3)
		return True

def getVideoInfo(url):
	return WebVideo().getVideoObject(url)
	
def getVideoPlayable(sourceName,ID):
	if sourceName == 'Vimeo':
		return WebVideo().getVimeoFLV(ID)
	elif sourceName == 'YouTube':
		return WebVideo().getYoutubePluginURL(ID)
	
class Video():
	def __init__(self,ID=None):
		self.ID = ID
		self.thumbnail = ''
		self.swf = ''
		self.media = ''
		self.embed = ''
		self.page = ''
		self.playable = ''
		self.title = ''
		self.sourceName = ''
		self.playableCallback = None
		self.isVideo = True
		
	def playableURL(self):
		return self.playable or self.media
	
	def getPlayableURL(self):
		if not self.playableCallback: return self.playableURL()
		return self.playableCallback(self.ID)
		
class WebVideo():
	alphabetB58 = '123456789abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ'
	countB58 = len(alphabetB58)
	
	def __init__(self):
		self.modules = {}
		
	def getVideoObject(self,url):
		if 'youtu.be' in url or 'youtube.com' in url:
			ID = self.extractYoutubeIDFromURL(url)
			video = Video(ID)
			video.sourceName = 'YouTube'
			video.thumbnail = self.getYoutubeThumbURL(ID)
			video.playable = self.getYoutubePluginURL(ID)
			video.swf = self.getYoutubeSWFUrl(ID)
		elif 'vimeo.com' in url:
			ID = self.extractVimeoIDFromURL(url)
			video = Video(ID)
			video.sourceName = 'Vimeo'
			info = self.getVimeoInfo(ID)
			video.thumbnail = info.get('thumbnail','')
			video.title = info.get('title','')
			video.playableCallback = self.getVimeoFLV
		elif 'flic.kr/' in url:
			ID = self.getFlickrIDFromURL(url)
			info = self.getFlickrInfo(ID)
			video = Video(ID)
			video.sourceName = 'flickr'
			video.thumbnail = info.get('thumbnail','')
			video.title = info.get('title','')
			if not info.get('type') == 'video':
				video.isVideo = False
				return video
			video.playable = self.getFlickrPluginURL(ID)
		else:
			return None
		return video
	
	def getFlickrPluginURL(self,ID):
		return 'plugin://plugin.image.flickr/?video_id=' + ID
	
	def getYoutubePluginURL(self,ID):
		return 'plugin://plugin.video.youtube/?path=/root/video&action=play_video&videoid=' + ID
			
	def getYoutubeThumbURL(self,ID):
		return 'http://i1.ytimg.com/vi/%s/default.jpg' % ID
	
	def getYoutubeSWFUrl(self,ID):
		return 'http://www.youtube.com/v/' + ID
		
	def extractYoutubeIDFromURL(self,url):
		if 'youtu.be' in url:
			#http://youtu.be/sSMbOuNBV0s
			sp = url.split('.be/',1)
			if len(sp) == 2: return sp[1]
			return ''
		elif 'youtube.com' in url:
			#http://www.youtube.com/watch?v=MuLDUws0Zh8&feature=autoshare
			ID = url.split('v=',1)[-1].split('&',1)[0]
			if 'youtube.com' in url: return ''
			return ID
	
	def getFlickrIDFromURL(self,url):
		#try:
		#	longURL = urllib2.urlopen(url).geturl()
		#except:
		#	return ''
		#if longURL.endswith('/'): longURL = longURL[:-1]
		#return longURL.rsplit('/',1)[-1]
		end = url.rsplit('/',1)[-1]
		return str(self.decodeBase58(end))
		
	def getFlickrInfo(self,ID):
		fImport = self.doImport('plugin.image.flickr', '', 'default')
		if not fImport: return {}
		fsession = fImport.FlickrSession()
		if not fsession.authenticate(): return {}
		info = fsession.flickr.photos_getInfo(photo_id=ID)
		photo = info.find('photo')
		title = photo.find('title').text
		media = photo.get('media','')
		thumb = fImport.photoURL(photo.get('farm',''),photo.get('server',''),ID,photo.get('secret',''))
		#<location latitude="47.574433" longitude="-122.640611" accuracy="16" context="0" place_id="pqEP2S9UV7P8W60smQ" woeid="55995994">
		return {'title':title,'type':media,'thumbnail':thumb}
		
	def extractVimeoIDFromURL(self,url):
		#TODO: Finish this :)
		ID = url.rsplit('/',1)[-1]
		return ID
	
	def getVimeoInfo(self,ID):
		infoURL = 'http://vimeo.com/api/v2/video/%s.xml' % ID
		xml = urllib2.urlopen(urllib2.Request(infoURL,None,{'User-Agent':'Wget/1.9.1'})).read()
		ret = {}
		try:
			ret = {}
			ret['title'] = re.search('<url>([^<]*)</url>',xml).group(1)
			ret['thumbnail'] = re.search('<thumbnail_large>([^<]*)</thumbnail_large>',xml).group(1)
		except:
			pass
		return ret
		
	def getVimeoFLV(self,ID):
		#TODO: Make this better
		infoURL = 'http://www.vimeo.com/moogaloop/load/clip:' + ID
		o = urllib2.urlopen(infoURL)
		info = o.read()
		try:
			sig = re.search('<request_signature>([^<]*)</request_signature>',info).group(1)
			exp = re.search('<request_signature_expires>([^<]*)</request_signature_expires>',info).group(1)
			hd_or_sd = int(re.search('isHD>([^<]*)</isHD>',info).group(1)) and 'hd' or 'sd'
		except:
			return ''
		flvURL = 'http://www.vimeo.com/moogaloop/play/clip:%s/%s/%s/?q=%s' % (ID,sig,exp,hd_or_sd)
		try:
			flvURL = urllib2.urlopen(urllib2.Request(flvURL,None,{'User-Agent':'Wget/1.9.1'})).geturl()
		except:
			ERROR('Failed to get vimeo URL')
			return ''
		#print flvURL
		return flvURL
	
	def decodeBase58(self,s):
		""" Decodes the base58-encoded string s into an integer """
		decoded = 0
		multi = 1
		s = s[::-1]
		for char in s:
			decoded += multi * self.alphabetB58.index(char)
			multi = multi * self.countB58
		return decoded
	
	def doImport(self,addonID,path,module):
		full = '/'.join((addonID,path,module))
		if full in self.modules: return self.modules[full]
		addonPath = xbmcaddon.Addon(addonID).getAddonInfo('path')
		importPath = os.path.join(addonPath,path)
		sys.path.insert(0,importPath)
		try:
			mod = __import__(module)
			reload(mod)
			del sys.path[0]
			self.modules[full] = mod
			return mod
		except ImportError:
			ERROR('Error importing module %s for share target %s.' % (self.importPath,self.addonID))
		except:
			ERROR('ShareTarget.getModule(): Error during target sharing import')
		return 
#http://vimeo.com/moogaloop.swf?clip_id=38759453
#http://vimeo.com/api/v2/video/38759453.json

#http://www.vimeo.com/moogaloop/load/clip:82739
#http://www.vimeo.com/moogaloop/play/clip:82739/38c7be0cecb92a0a3623c2769bccf73b/1221451200/?q=sd

def copyGenericModImages(skinPath):
	import shutil
	for f in ('ShareSocial-ButtonFocus.png','ShareSocial-CloseButtonFocus.png','ShareSocial-CloseButton.png','ShareSocial-DialogBack.png'):
		src = os.path.join(__addon__.getAddonInfo('path'),'skinmods',f)
		dst = os.path.join(skinPath,'media',f)
		shutil.copy(src, dst)
	
def copyTree(source,target):
	import shutil
	shutil.copytree(source, target)
	
def installSkinMod(restore=False):
	restart = False
	localAddonsPath = os.path.join(xbmc.translatePath('special://home'),'addons')
	skinPath = xbmc.translatePath('special://skin')
	if skinPath.endswith(os.path.sep): skinPath = skinPath[:-1]
	currentSkin = os.path.basename(skinPath)
	localSkinPath = os.path.join(localAddonsPath,currentSkin)
	
	if not os.path.exists(localSkinPath):
		yesno = xbmcgui.Dialog().yesno('Mod Install','Skin not installed in user path.','Click Yes to copy,','click No to Abort')
		if not yesno: return
		dialog = xbmcgui.DialogProgress()
		dialog.create('Copying Files','Please wait...')
		try:
			copyTree(skinPath,localSkinPath)
		except:
			err = ERROR('Failed to copy skin to user directory')
			xbmcgui.Dialog().ok('Error',err,'Failed to copy files, aborting.')
			return
		finally:
			dialog.close()
		restart = True
		xbmcgui.Dialog().ok('Success','Files copied.')
	skinPath = localSkinPath
	
	dialogPath = os.path.join(skinPath,'720p','DialogContextMenu.xml')
	backupPath = os.path.join(skinPath,'720p','DialogContextMenu.xml.SSbackup')
	sourcePath = os.path.join(__addon__.getAddonInfo('path'),'skinmods',currentSkin + '.xml')
	fallbackSourcePath = os.path.join(__addon__.getAddonInfo('path'),'skinmods','default.xml')
	
			
	LOG('Local Addons Path: %s' % localAddonsPath)
	LOG('Current skin: %s' % currentSkin)
	LOG('Skin path: %s' % skinPath)
	LOG('Target path: %s' % dialogPath)
	LOG('Source path: %s' % sourcePath)
	if restore:
		if not os.path.exists(backupPath):
			LOG('Asked to restore skin file, mod not installed or backup missing')
			xbmcgui.Dialog().ok('Undo','Mod not installed or','backup file is missing')
			return
		LOG('Restoring skin file')
		os.remove(dialogPath)
		open(dialogPath,'w').write(open(backupPath,'r').read())
		#Remove added files
		os.remove(backupPath)
		for f in ('ShareSocial-ButtonFocus.png','ShareSocial-CloseButtonFocus.png','ShareSocial-CloseButton.png','ShareSocial-DialogBack.png'):
			dst = os.path.join(skinPath,'media',f)
			if os.path.exists(dst): os.remove(dst)

		xbmcgui.Dialog().ok('Undo','Mod successfully removed!')
	else:
		if os.path.exists(sourcePath):
			yesno = xbmcgui.Dialog().yesno('Mod Install','Matching mod found!','Click Yes to install,','click No to install generic mod')
			if not yesno:
				copyGenericModImages(skinPath)
				sourcePath = fallbackSourcePath
		else:
			yesno = xbmcgui.Dialog().yesno('Mod Install','Matching mod not found!','Install generic mod?')
			if not yesno:
				xbmcgui.Dialog().ok('Mod Install','Mod not installed.')
				return
			copyGenericModImages(skinPath)
			sourcePath = fallbackSourcePath
		
		if not os.path.exists(backupPath):
			LOG('Creating backup of original skin file: ' + backupPath)
			open(backupPath,'w').write(open(dialogPath,'r').read())	
			
		os.remove(dialogPath)
		open(dialogPath,'w').write(open(sourcePath,'r').read())
		xbmcgui.Dialog().ok('Mod Install','Mod successfully installed!')
		if restart:
			xbmcgui.Dialog().ok('Restart','XBMC needs to be restarted','for the changes to take effect')
	