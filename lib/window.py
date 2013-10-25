import os, re, xbmc, xbmcgui, xbmcaddon

def getFontList():
	with open(getFontXMLPath(),'r') as f: xml = f.read()
	return re.findall('<name>(.*)</name>',xml)
	
def getDefaultFont(size=12,flist=None):
	size = str(size)
	flist = flist or getFontList()
	for f in flist:
		if size in f and not 'cap' in f.lower(): return f
	return 'font%s' % size
		
def getFontXMLPath():
	skinPath = xbmc.translatePath('special://skin')
	res = '720p'
	if not os.path.exists(os.path.join(skinPath,res)):
		res = '1080i'
	return os.path.join(skinPath,res,'Font.xml')

def openWindow(windowClass,windowXML,theme='Default',*args,**kwargs):
	settings = xbmcaddon.Addon('script.module.sharesocial')
	path = xbmc.translatePath(settings.getAddonInfo('path'))
	skin = os.path.join(path,'resources','skins',theme,'720p')
	src = os.path.join(skin,windowXML)		
	xml = open(src,'r').read()
	xmlFilename = 'ShareSocial-Current.xml'
	fonts = ('font_list_status_text','font_list_status_name','font_list_status_time','font_comments_text')
	default = getDefaultFont()
	for f in fonts:
		xml = xml.replace(f,settings.getSetting(f) or default)
	with open(os.path.join(skin,xmlFilename),'w') as f:
		f.write(xml)
	w = windowClass(xmlFilename,path,theme,*args,**kwargs)
	w.doModal()
	del w
	
class FontSelectDialog(xbmcgui.WindowXMLDialog):
	def __init__(self,*args,**kwargs):
		self.setting = kwargs.get('setting')
		xbmcgui.WindowXMLDialog.__init__(self)
	
def fontSelectDialog(setting):
	path = xbmc.translatePath(xbmcaddon.Addon('script.module.sharesocial').getAddonInfo('path'))
	skin = os.path.join(path,'resources','skins','Default','720p')
	xmlFilename = 'ShareSocial-Current.xml'
	src = os.path.join(skin,'ShareSocial-FontChooser.xml')
	controlfn = os.path.join(path,'lib','font-select-item-base.xml')
	with open(controlfn,'r') as f:
		control = f.read()
	replace = ''
	ID=200
	for font in getFontList():
		replace += control.replace('!FONT!',font).replace('!LABEL!',font).replace('!SETTING!',setting).replace('!ID',str(ID))
		ID += 1
	with open(src,'r') as f:
		xml = f.read()
	with open(os.path.join(skin,xmlFilename),'w') as f:
		f.write(xml.replace('<!-- CONTROLS -->',replace))
	w = FontSelectDialog(xmlFilename,path,'Default','720p',setting=setting)
	w.doModal()
	del w
	
def setFontSetting(setting,val):
	xbmcaddon.Addon('script.module.sharesocial').setSetting(setting,val)