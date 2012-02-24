# -*- coding: utf-8 -*-
import xbmcaddon, xbmc, xbmcgui #@UnresolvedImport
import os, sys, urllib2, traceback

__author__ = 'ruuk'
__url__ = 'http://code.google.com'
__date__ = '02-13-2012'
__version__ = '0.1.0'
__addon__ = xbmcaddon.Addon(id='script.module.social')
__lang__ = __addon__.getLocalizedString

APILEVEL = 1

MAIN_PATH = xbmc.translatePath(__addon__.getAddonInfo('profile'))
TARGETS_PATH = os.path.join(MAIN_PATH,'targets')
if not os.path.exists(MAIN_PATH): os.makedirs(MAIN_PATH)

def LOG(text):
	print text
	
def ERROR(message):
	LOG(message)
	traceback.print_exc()
	return str(sys.exc_info()[1])

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
	
def getFile(url,target_file):
		if not url: return
		try:
			request = urllib2.urlopen(url)
			target_file = fixExtension(request.info().get('content-type',''),target_file)
		except:
			LOG('ERROR: urlopen() in getFile() - URL: %s' % url)
			return ''
		f = open(target_file,"wb")
		f.write(request.read())
		f.close()
		return target_file

def doKeyboard(prompt,default='',hidden=False):
	keyboard = xbmc.Keyboard(default,prompt)
	keyboard.setHiddenInput(hidden)
	keyboard.doModal()
	if not keyboard.isConfirmed(): return None
	return keyboard.getText()

class ShareFailure():
	def __init__(self,code,reason,error=''):
		self.code = code
		self.reason = reason
		self.error = error
	
	def __nonzero__(self):
		return False
	
class Share():
	def __init__(self,sourceID,sharetype):
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

	def askMessage(self):
		self.message = doKeyboard('Enter Message',self.message) or self.message
		
	def link(self):
		return self.page or self.media
	
	def asHTML(self,use_media=False):
		thumb = use_media and self.media or self.thumbnail
		return self.html or '<div style="text-align: center; float: left;"><a href="%s"><img src="%s" /><br /><br />%s</a></div>' % (self.link(),thumb,self.title)
	
	def share(self):
		ShareManager().doShare(self)
	
class ShareTarget():
	def __init__(self,target_data=None):
		self.addonID = ''
		self.shareTypes = []
		self.name = ''
		self.importPath = ''
		self.iconPath = ''
		if target_data: self.fromString(target_data)
	
	def canShare(self,shareType):
		if shareType in self.shareTypes: return True
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
		self.shareTypes = kvdict.get('shareTypes').split(',')
		self.iconPath = kvdict.get('iconPath')
		return self
	
	def toString(self):
		return 'addonID=%s:::name=%s:::importPath=%s:::shareTypes=%s:::iconPath=%s' % (	self.addonID,
																					self.name,
																					self.importPath,
																					','.join(self.shareTypes),
																					self.iconPath )
		
	def getModule(self):
		module = os.path.basename(self.importPath)
		subPath = os.path.dirname(self.importPath)
		addonPath = xbmcaddon.Addon(self.addonID).getAddonInfo('path')
		importPath = os.path.join(addonPath,subPath)
		sys.path.insert(0,importPath)
		try:
			return __import__(module)
		except ImportError:
			LOG('Error importing module %s for share target %s. Unregistering target.' % (self.importPath,self.addonID))
			self.unRegisterShareTarget(self)
			return ShareFailure('targetImportFailure','Failed To Import Share Target')
		except:
			error = ERROR('handOffShare(): Error during target sharing import')
			return ShareFailure('targetImportError','Error In Target Sharing Import: %s' % error,error)
		finally:
			del sys.path[0]
			
	def doShare(self,share):
		mod = self.getModule()
		if not mod: return mod
		
		try:
			mod.doShareSocial(share)
		except:
			error = ERROR('handOffShare(): Error in target doShareSocial() function')
			return ShareFailure('targetImportError','Error In Target doShareSocial() Function: %s' % error,error)
		return self
	
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
					'text':1}
	
	def __init__(self):
		self.readTargets()
	
	def doShare(self,share):
		target = self.askForTarget(share)
		if not target: return ShareFailure('userAbort','User Abort')
		return target.doShare(share)
		
	def askForTarget(self,share):
		options = []
		optionIDs = []
		for tkey in self.targets:
			target = self.targets[tkey]
			if target.addonID != share.sourceID:
				if target.canShare(share.shareType):
					options.append(target.name)
					optionIDs.append(target.addonID)
				else:
					for alt in share.alternates:
						if target.canShare(alt.shareType):
							options.append(target.name)
							optionIDs.append(target.addonID)
							break
		idx = xbmcgui.Dialog().select("Share to:",options)
		if idx < 0:
			return None
		else:
			option = optionIDs[idx]
		return self.targets[option]
	
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
			
			
		
	