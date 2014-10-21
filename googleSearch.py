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
from itertools import product

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
        self.Args=_args
        self.URLsFile = _urlsFile
        self.AllKeyword = []
        Keywords = _keyFile.readlines()
        for Keyword in  Keywords:
            if len(Keyword.strip()) > 0:
              self.AllKeyword.append(Keyword.strip())

        if self.Args.KeywordsCombination > 0:
            for Keyword1 in  Keywords:
              if len(Keyword1.strip()) > 0:
                for Keyword2 in  Keywords:
                  if len(Keyword2.strip()) > 0 and not Keyword2 == Keyword1:
                    self.AllKeyword.append(Keyword1.strip() + " " + Keyword2.strip())

        if self.Args.KeywordsCombination > 1:
            for Keyword1 in Keywords:
              if len(Keyword1.strip()) > 0:
                for Keyword2 in Keywords:
                  if len(Keyword2.strip()) > 0 and not Keyword2 == Keyword1:
                    for Keyword3 in  Keywords:
                      if len(Keyword3.strip()) > 0 and Keyword2 != Keyword3 and Keyword1 != Keyword3:
                        self.AllKeyword.append(Keyword1.strip() + " " + Keyword2.strip() + " " + Keyword3.strip())

        self.KeywordIndex=0
        self.newKeyword()

    def newKeyword(self):
        self.StartFrom=0
        if self.Args.Keyword:
            self.Keyword = self.Args.Keyword
            self.Args.Keyword = None
            self.search()
        elif self.Args.KeywordsFile:
            if len(self.AllKeyword) == self.KeywordIndex:
                self.close()
                return
            
            self.Keyword = self.AllKeyword[self.KeywordIndex]
            self.KeywordIndex+=1
            self.search()
            

    def search(self):
        QtWebKit.QWebSettings.globalSettings().setAttribute(QtWebKit.QWebSettings.AutoLoadImages, False);
        self.DoNothing=False
        if self.Args.SSL:
          URLStr='https://www.google.com/search?q='
        else:
          URLStr='http://www.google.com/search?q='

        URLStr += ("site:"+self.Args.Domain + "+" if len(self.Args.Domain) > 0 else "") + self.Keyword.strip()
        URLStr += ("&start=" + str(self.StartFrom) if self.StartFrom > 0 else "")
        URLStr += ("&lr=lang_" + self.Args.Lang if len(self.Args.Lang)  == 2 else "")

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

            if re.match('^https?\:\/\/.*',Url) and (self.Args.RegEx == "" or re.match(self.Args.RegEx, Url)):
                MD5URL = hashlib.md5()
                MD5URL.update(Url)
                if MD5URL.hexdigest() not in URLs:
                    print Url
                    URLs[MD5URL.hexdigest()] = 1;
                    self.URLsFile.write(Url+"\n")

        self.URLsFile.flush()
        self.timer = QtCore.QTimer()

        if self.DoNothing == False:
          if not '>Next</span>' in PageContent:
            print "----- No more pages found ----\n"
            self.timer.singleShot(1000, self.newKeyword)
          elif (self.StartFrom >= ((int(self.Args.MaxPages) - 1) * 10)):
            self.timer.singleShot(1000, self.newKeyword)
          else:
            self.StartFrom += 10
            self.timer.singleShot(1000, self.search)

def main():
    global URLs

    Parser = argparse.ArgumentParser(description='A simple Google search based on QWebKit')
    Parser.add_argument('-p', '--pages', dest='MaxPages', action='store', default=0, help='Number of pages to return. Max 60')
    Parser.add_argument('-d', '--domain', dest='Domain', action='store', default="", help='Domain to specificly search on')
    Parser.add_argument('-s', '--ssl', dest='SSL', action='store_true', default=False, help='Use SSL connection')
    Parser.add_argument('-m', '--match', dest='RegEx', action='store', default="", help='A RegEx to match before accept')
    Parser.add_argument('-l', '--lang', dest='Lang', action='store', default="", help='Language to search on ISO639')
    Parser.add_argument('-f', '--file', dest='KeywordsFile', action='store', default="", help='Keywords File')
    Parser.add_argument('-k', '--keyword', dest='Keyword', action='store', default="", help='Keyword to search')
    Parser.add_argument('-o', '--output', dest='OutputFile', action='store', default="", help='Output File')
    Parser.add_argument('-c', '--combinations', dest='KeywordsCombination', action='store', default=0, help='Combines Keywords n rounds Max 3')

    Args = Parser.parse_args()

    if not Args.KeywordsFile and not Args.Keyword:
        print "You must provide either a keyword or a file"
        Parser.print_help()
        sys.exit(-1);

    qApp = QtGui.QApplication(sys.argv)


    if Args.KeywordsFile :
      try:
        KeyFile  = open(Args.KeywordsFile,  "r" )
      except:
        print "Unable to READ: ", Args.KeywordsFile
        sys.exit(-1);


    if not Args.OutputFile :
      Args.OutputFile = "Urls.csv"

    try:
      OldFile  = open(Args.OutputFile,  "r" )
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
      OutFile  = open(Args.OutputFile,  "a" )
    except:
      print "Unable to APPEND: URLs.txt"
      sys.exit(-1);

    print "Old File has ", len(URLs), " Entries"


    GoogleSearch = clsGoogleSearch()

    if Args.Keyword:
      GoogleSearch.Args=Args
      GoogleSearch.URLsFile=OutFile
      GoogleSearch.KeyFile=None
      GoogleSearch.newKeyyword()
    else:
      GoogleSearch.start(KeyFile, OutFile, Args)

    sys.exit(qApp.exec_())

if __name__ == "__main__":
    main()
