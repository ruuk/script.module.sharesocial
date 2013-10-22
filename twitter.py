import xbmcaddon #@UnresolvedImport
from twython import Twython
import binascii, httplib, StringIO, obfuscate
from lib import ShareSocial
from array import array

if True:
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
		if not hasattr(data,'read') and not isinstance(data, array):
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
	httplib.HTTPConnection.progressCallback = None

__addon__ = xbmcaddon.Addon(id='script.module.sharesocial')
__lang__ = __addon__.getLocalizedString

import locale
loc = locale.getdefaultlocale()
print loc
ENCODING = loc[1] or 'utf-8'

DIALOG = None

def ENCODE(string):
	return string.encode(ENCODING,'replace')

def LOG(string):
		print 'ShareSocial: Twitter: %s' % ENCODE(string)
		
def getSetting(sett,default=None):
	return __addon__.getSetting(sett) or default

def setSetting(sett,val):
	__addon__.setSetting(sett,val)
	
def getUserList():
	ulist = getSetting('user_list')
	if not ulist: return []
	return ulist.split(',')

def addUserToList(userID):
	users = getUserList()
	if userID in users: return
	users.append(userID)
	setSetting('user_list',','.join(users))

class TwitterUser():
	def __init__(self,oauth_dict={},oauth_token=None,oauth_secret=None,name='',ID=None):
		self.oauthToken = oauth_token
		self.oauthSecret = oauth_secret
		self.name = name
		self.ID = ID
		self.photo = ''
		
	def getData(self,twit):
		data = twit.show_user(user_id=self.ID)
		self.photo = data.get('profile_image_url','')
		print self.photo
		
	def fromOauthDict(self,oauth_dict):
		self.oauthToken = oauth_dict.get('oauth_token')
		self.oauthSecret = oauth_dict.get('oauth_token_secret')
		self.name = oauth_dict.get('screen_name')
		self.ID = oauth_dict.get('user_id')
		return self
	
	def save(self):
		addUserToList(self.ID)
		data = binascii.hexlify(ShareSocial.dictToString(self.__dict__))
		setSetting('user_data_%s' % self.ID,data)
		
	def load(self):
		data = getSetting('user_data_%s' % self.ID)
		if not data: return None
		data = ShareSocial.dictFromString(binascii.unhexlify(data))
		self.__dict__.update(data)
		return self
		
class TwitterSession():
	consumerKey = '2qKlX9iYmds7w4wLcASQw'
	secret = '54544577637a64355231423257444658646d737a53304e5452546c774f56427363544670625846715a6b39455446563363325251533239560a'
	def __init__(self,user=None,add_user=False,ID=None,require_existing_user=False):
		self.consumerSecret = obfuscate.deobfuscate(self.secret)
		if add_user: return self.addUser()
		self.user = user
		if ID: self.user = TwitterUser(ID=ID).load()
		if not self.user: self.setUser(require_existing_user)
		if not self.user:
			self.twit = None
			return
		self.initializeUserTwit()
	
	def initializeUserTwit(self):
		self.twit = Twython(self.consumerKey,self.consumerSecret,self.user.oauthToken,self.user.oauthSecret)
		self.user.getData(self.twit)
		
	def getAuth(self):
		self.twit = Twython(self.consumerKey,self.consumerSecret)
		auth = self.twit.get_authentication_tokens()
		url,html = self.doBrowserAuth(auth['auth_url'])  # @UnusedVariable
		oauth_token, oauth_verifier = self.extractTokensFromURL(url)  # @UnusedVariable
		oauth_token = auth['oauth_token']
		oauth_token_secret = auth['oauth_token_secret']
		if not oauth_token or not oauth_token_secret: return False
		self.twit = Twython(self.consumerKey,self.consumerSecret,oauth_token,oauth_token_secret)
		authorized_tokens = self.twit.get_authorized_tokens(oauth_verifier)
		self.user = TwitterUser().fromOauthDict(authorized_tokens)
		self.initializeUserTwit()
		#self.user.getData(self.twit)
		self.user.save()
		setSetting('last_user',self.user.ID)
		return True
		
	def doBrowserAuth(self,url):
		from webviewer import webviewer #@UnresolvedImport
		#login = {'action':'login.php'}
		#if email and password:
		#	login['autofill'] = 'email=%s,pass=%s' % (email,password)
		#	login['autosubmit'] = 'true'
		autoForms = [{'name':'oauth_form'}]
		#autoClose = {'url':'.*access_token=.*','heading':'','message':''}
		print url
		return webviewer.getWebResult(url,autoForms=autoForms) #,autoClose=autoClose) #@UnusedVariable
		
	def extractTokensFromURL(self,url):
		#http://www.2ndmind.com/xbmc/sharesocial/authenticated.html?oauth_token=3P6dvkqXBFIXrIoeTg360JBUZynPUNJfcFcw3bgT5oU&oauth_verifier=bczsQGOnjgZ1GLSREqt6oGad30g7jjsKr3eIvpX87E
		from cgi import parse_qs
		import urlparse
		try:
			oauth_token = parse_qs(urlparse.urlparse(url.replace('#','?',1))[4])['oauth_token'][0]
			oauth_verifier = parse_qs(urlparse.urlparse(url.replace('#','?',1))[4])['oauth_verifier'][0]
			return oauth_token,oauth_verifier
		except:
			LOG("Failed to parse tokens from url: %s" % url)
			return None,None
	
	def setUser(self,require_existing_user=False):
		user = getSetting('last_user')
		if not user:
			users = getUserList()
			if users: user = users[0]
		if not user and not require_existing_user:
			self.getAuth()
			return
		self.user = TwitterUser(ID=user).load()
		
	def addUser(self):
		import xbmcgui #@UnresolvedImport
		if not self.getAuth():
			xbmcgui.Dialog().ok('Failed','Failed to add user!')
		else:
			xbmcgui.Dialog().ok('Success','User Added:','',self.user.name)


	
