#!/usr/bin/env python
from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4 import QtWebKit
import time
import sys
import os
from sgmllib import SGMLParser
import time
import hashlib
import re
import argparse

URLs={}

class URLLister(SGMLParser):
    def reset(self):
        SGMLParser.reset(self)
        self.Urls = []

    def start_a(self, attrs):
        href = [v for k, v in attrs if k=='href']
        if href:
            self.Urls.extend(href)

class clsGoogleSearch(QtWebKit.QWebView):
    def __init__(self, parent=None):
      super(clsGoogleSearch, self).__init__(parent)

    def start(self, _keyFile, _urlsFile, _args):
        self.KeyFile=_keyFile
        self.URLsFile = _urlsFile
        self.MaxPages=_args.MaxPages
        self.Site=_args.Domain
        self.MatchTo = _args.RegEx
        self.SSL = _args.SSL

        self.newKeyyword()
    
    def newKeyyword(self):
        self.StartFrom=0
        self.Keyword = self.KeyFile.readline()
        if self.Keyword == '':
            self.close()
        else:
            self.search()

    def search(self):
        QtWebKit.QWebSettings.globalSettings().setAttribute(QtWebKit.QWebSettings.AutoLoadImages, False);
        self.DoNothing=False
        if self.SSL:
          URLStr='https://www.google.com/search?q='+ ("site:"+self.Site + "+" if len(self.Site) > 0 else "") + self.Keyword.strip()+ ("&start=" + str(self.StartFrom) if self.StartFrom > 0 else "")
        else:
          URLStr='http://www.google.com/search?q='+ ("site:"+self.Site + "+" if len(self.Site) > 0 else "") + self.Keyword.strip()+ ("&start=" + str(self.StartFrom) if self.StartFrom > 0 else "")
          
        self.URL = QtCore.QUrl(URLStr)
        print "\n==========================>" + URLStr
        self.loadFinished.connect(self._loadFinished)
        self.load(self.URL)
        self.show()

    def createWindow(self, windowType):
        return self

    def _loadFinished(self):
        global URLs
        self.loadFinished.disconnect(self._loadFinished)

        print "Load Finished. New URLs:"
        self.stop();
        
        PageContent=str(self.page().mainFrame().toHtml().toAscii());
        if 'name="captcha"' in PageContent:
            print "\n\n****************************** Captcha needed ********************************\n\n"
            self.loadFinished.connect(self._loadFinished)
            if self.DoNothing == False:
                QtWebKit.QWebSettings.globalSettings().setAttribute(QtWebKit.QWebSettings.AutoLoadImages, True);
                self.reload()
                self.DoNothing=True
            else:
                self.DoNothing=False
            return

        Parser = URLLister()
        Parser.feed(PageContent)
        for Url in Parser.Urls:
            if re.match('.*googleusercontent.*',Url) or  re.match('^\/[^url].*',Url) or re.match(".*\.google.com\/.*",Url):
                continue
            Url=re.sub("^\/url\?q\=","", Url)
            Url=re.sub("\&sa\=U\&e.*","", Url).strip()

            if re.match('^https?\:\/\/.*',Url) and (self.MatchTo == "" or re.match(self.MatchTo, Url)):
                MD5URL = hashlib.md5()
                MD5URL.update(Url)
                if MD5URL.hexdigest() not in URLs:
                    print Url
                    URLs[MD5URL.hexdigest()] = 1;
                    self.URLsFile.write(Url+"\n")

        self.URLsFile.flush()
        self.timer = QtCore.QTimer()

        if self.DoNothing == False:
          if (self.StartFrom >= ((int(self.MaxPages) - 1) * 10)):
            self.timer.singleShot(1000, self.newKeyyword)
          else:
            self.StartFrom += 10
            self.timer.singleShot(1000, self.search)

def main():
    global URLs

    Parser = argparse.ArgumentParser(description='A simple Google search based on QtWebKit')
    Parser.add_argument('-p', '--pages', dest='MaxPages', action='store', default=0, help='Number of pages to return. Max 60')
    Parser.add_argument('-d', '--domain', dest='Domain', action='store', default="", help='Domain to specificly search on')
    Parser.add_argument('-s', '--ssl', dest='SSL', action='store_true', default=False, help='Use SSL connection')
    Parser.add_argument('-m', '--match', dest='RegEx', action='store', default="", help='A RegEx to match before accept')
    Parser.add_argument('-k', '--keywords', dest='KeywordsFile', action='store', default="",required=True, help='Keywords File')
    Parser.add_argument('-o', '--output', dest='OutputFile', action='store', default="", help='Output File')
    
    args = Parser.parse_args()

    if not args.KeywordsFile:
        Parser.print_help()
        exit()

    qApp = QtGui.QApplication(sys.argv)

    try:
      KeyFile  = open(args.KeywordsFile,  "r" )
    except:
      print "Unable to READ: ", args.KeywordsFile
      sys.exit(-1);


    if not args.OutputFile :
      args.OutputFile = "Urls.csv"
      
    try:
      OldFile  = open(args.OutputFile,  "r" )
      while True:
        URL=OldFile.readline().strip()
        if URL == '':
          break;
        MD5URL = hashlib.md5()
        MD5URL.update(URL)

        URLs[MD5URL.hexdigest()] = 1
    except:
      True

    try:
      OutFile  = open(args.OutputFile,  "a" )
    except:
      print "Unable to APPEND: URLs.txt"
      sys.exit(-1);

      
    GoogleSearch = clsGoogleSearch()
    GoogleSearch.start(KeyFile, OutFile, args)
    
    sys.exit(qApp.exec_())

if __name__ == "__main__":
    main()






