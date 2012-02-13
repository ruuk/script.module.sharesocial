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

SHAREMANAGER = None
MAIN_PATH = xbmc.translatePath(__addon__.getAddonInfo('profile'))
TARGETS_PATH = os.path.join(MAIN_PATH,'targets')

def LOG(text):
	print text
	
def getShare(source,sharetype=None,content=None):
	return Share(source,sharetype,content)

def getShareTarget():
	return ShareTarget()

def getShareManager():
	if SHAREMANAGER: return SHAREMANAGER
	SHAREMANAGER = ShareManager()
	return SHAREMANAGER

def registerShareTarget(target):
	getShareManager().registerShareTarget(target)

class Share():
	def __init__(self,source,sharetype=None,content=None,source_name=None):
		self._sharetype = sharetype
		self._content = content
		self._source = source
		self._sourceName = source_name
		
	def sharetype(self,sharetype=None):
		if sharetype: self._sharetype = sharetype
		return self._sharetype
	
	def content(self,content=None):
		if content: self._content = content
		return self._content
	
	def source(self):
		return self._source
	
	def sourceName(self,source_name=None):
		if source_name: self._sourceName = source_name
		return self._sourceName or self._source
	
	def share(self):
		getShareManager().doShare(self)
	
class ShareTarget():
	def __init__(self,target_data=None):
		self.ID = ''
		self.shareTypes = []
		self.name = ''
		self.importName = ''
		self.iconPath = ''
		if target_data: self.fromString(target_data)
	
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
					'url':1,
					'html':1,
					'text':1}
	
	def __init__(self):
		self.readTargets()
	
	def doShare(self,share):
		target = self.askForTarget(share)
		if not target: return
		self.handOffShare(target,share)
		
	def askForTarget(self,shareobj):
		#TODO: Something
		if self.targets: return self.targets.values()[0]
		return None
	
	def registerShareTarget(self,target):
		self.targets[target.ID] = target
		self.writeTargets()
		
	def handOffShare(self,target,share):
		try:
			mod = __import__(target.importName)
		except ImportError:
			LOG('Error importing module %s for share target %s' % (target.importName,target.ID)) 
			return False
		mod.doShareSocial(share)
		return True
	
	def readTargets(self):
		self.targets = {}
		tf = open(TARGETS_PATH,'r')
		tdata = tf.read()
		tf.close()
		for t in tdata.splitlines():
			target = ShareTarget(t)
			self.targets[target.ID] = target
			
	def writeTargets(self):
		out = ''
		for t in self.targets.values():
			out.append(t.toString() + '\n')
		tf = open(TARGETS_PATH,'r')
		tf.write(out)
		tf.close()
			
			
		
	