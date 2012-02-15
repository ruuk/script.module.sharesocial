# -*- coding: utf-8 -*-
import xbmcaddon, xbmc, xbmcgui #@UnresolvedImport
import os, sys

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
	
def getShare(source,sharetype):
	return Share(source,sharetype)

def getShareTarget():
	return ShareTarget()

def registerShareTarget(target):
	ShareManager().registerShareTarget(target)
	
def shareTargetAvailable(share_type,sourceID):
	return ShareManager().shareTargetAvailable(share_type,sourceID)

class Share():
	def __init__(self,sourceID,sharetype):
		self.sourceID = sourceID
		self.shareType = sharetype
		self.content = None
		self.sourceName = ''
		self.title = ''
		self.thumbnail = ''
		self.link = ''
		self.lattitude = None
		self.longitude = None
		self.altitude = None
	
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
	
class ShareManager():
	sharetypes = {	'image':1,
					'audio':1,
					'video':1,
					'link':1,
					'imagelink':1,
					'videolink':1,
					'audiolink':1,
					'html':1,
					'text':1}
	
	def __init__(self):
		self.readTargets()
	
	def doShare(self,share):
		target = self.askForTarget(share)
		if not target: return
		self.handOffShare(target,share)
		
	def askForTarget(self,share):
		options = []
		optionIDs = []
		for tkey in self.targets:
			target = self.targets[tkey]
			if target.canShare(share.shareType) and target.addonID != share.sourceID:
				options.append(target.name)
				optionIDs.append(target.addonID)
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
	
	def handOffShare(self,target,share):
		module = os.path.basename(target.importPath)
		subPath = os.path.dirname(target.importPath)
		addonPath = xbmcaddon.Addon(target.addonID).getAddonInfo('path')
		importPath = os.path.join(addonPath,subPath)
		sys.path.insert(0,importPath)
		try:
			mod = __import__(module)
		except ImportError:
			LOG('Error importing module %s for share target %s. Unregistering target.' % (target.importPath,target.addonID))
			self.unRegisterShareTarget(target)
			return False
		finally:
			del sys.path[0]
		mod.doShareSocial(share)
		return True
	
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
			
			
		
	