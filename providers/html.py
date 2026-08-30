from html.parser import HTMLParser
from urllib.request import Request,urlopen
from aggregator import Listing,clean_text
import re
class P(HTMLParser):
 def __init__(self): super().__init__(); self.title=[]; self.desc=[]
 def handle_starttag(self,t,a):
  d=dict(a)
  if t=='meta' and d.get('name','').lower() in ('description','og:description'): self.desc.append(d.get('content',''))
  if t=='meta' and d.get('property','').lower()=='og:title': self.title.append(d.get('content',''))
class HtmlProvider:
 name='html'
 def fetch(self,url):
  h=urlopen(Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=12).read().decode('utf-8','ignore'); p=P();p.feed(h)
  return Listing(source=self.name,source_url=url,title=clean_text(max(p.title,key=len,default='')),description=clean_text(max(p.desc,key=len,default='')),raw={'html_bytes':len(h)},confidence=.4)
