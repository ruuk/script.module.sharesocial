# -*- coding: utf-8 -*-
import xbmcaddon, xbmc, xbmcgui #@UnresolvedImport
import os

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
	
def getShare(source,sharetype=None,content=None,source_name='',share_title=''):
	return Share(source,sharetype,content)

def getShareTarget():
	return ShareTarget()

def registerShareTarget(target):
	ShareManager().registerShareTarget(target)
	
def shareTargetAvailable(share_type):
	return ShareManager().shareTargetAvailable(share_type)

class Share():
	def __init__(self,source,sharetype=None,content=None,source_name='',share_title=''):
		self.shareType = sharetype
		self.content = content
		self.source = source
		self.sourceName = source_name
		self.title = share_title
	
	def share(self):
		ShareManager().doShare(self)
	
class ShareTarget():
	def __init__(self,target_data=None):
		self.ID = ''
		self.shareTypes = []
		self.name = ''
		self.importName = ''
		self.iconPath = ''
		if target_data: self.fromString(target_data)
	
	def canShare(self,shareType):
		if shareType in self.shareTypes: return True
		return False
	
	def fromString(self,target_data):
		kvdict = {}
		for keyval in target_data.split(':::'):
			key,val = keyval.split('=',1)
			kvdict[key] = val
		self.ID = kvdict.get('ID')
		self.name = kvdict.get('name')
		self.importName = kvdict.get('importName')
		self.shareTypes = kvdict.get('shareTypes').split(',')
		self.iconPath = kvdict.get('iconPath')
		return self
	
	def toString(self):
		return 'ID=%s:::name=%s:::importName=%s:::shareTypes=%s:::iconPath=%s' % (	self.ID,
																					self.name,
																					self.importName,
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
			if target.canShare(share.shareType):
				options.append(target.name)
				optionIDs.append(target.ID)
		idx = xbmcgui.Dialog().select("Share to:",options)
		if idx < 0:
			return None
		else:
			option = optionIDs[idx]
		return self.targets[option]
	
	def shareTargetAvailable(self,share_type):
		for target in self.targets.values():
			if target.canShare(share_type): return True
		return False
				
	def registerShareTarget(self,target):
		self.targets[target.ID] = target
		self.writeTargets()
		
	def unRegisterShareTarget(self,target):
		if target.ID in self.targets:
			del self.targets[target.ID]
			self.writeTargets()
	
	def handOffShare(self,target,share):
		try:
			mod = __import__(target.importName)
		except ImportError:
			LOG('Error importing module %s for share target %s. Unregistering target.' % (target.importName,target.ID))
			self.unRegisterShareTarget(target)
			return False
		mod.doShareSocial(share)
		return True
	
	def readTargets(self):
		self.targets = {}
		if not os.path.exists(TARGETS_PATH): return
		tf = open(TARGETS_PATH,'r')
		tdata = tf.read()
		tf.close()
		for t in tdata.splitlines():
			target = ShareTarget(t)
			self.targets[target.ID] = target
			
	def writeTargets(self):
		out = ''
		for t in self.targets.values():
			out += t.toString() + '\n'
		tf = open(TARGETS_PATH,'w')
		tf.write(out)
		tf.close()
			
			
		
	