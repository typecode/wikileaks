import logging
import os
import re
import sys
import xml
import csv
import subprocess

import nltk

sys.path.append("lib")
import pymongo
from BeautifulSoup import BeautifulSoup

logging.basicConfig(level=logging.DEBUG, format="%(levelname)-8s %(message)s")

mongo_conn = pymongo.Connection('localhost', 27017)
db = mongo_conn['wikileaks']

class Cable():
  
  raw = ""
  attrs = {}
  
  def __init__(self,raw):
    logging.info('Cable()')
    self.raw = raw
  
  def __getitem__(self,name):
    if name == 'raw':
      return self.raw
    if name in self.attrs:
      return self.attrs[name]
    else:
      return None
    
  def __setitem__(self,name,value):
    self.attrs[name] = value
    
  def get(self):
    return self.attrs
    
class CableGateMirror():
  
  mirror_directory = 'data/cablegate/'
  
  def __init__(self):
    logging.info('CableGateMirror()')
    self.update()
    
  def update(self):
    logging.info('CableGateMirror.update')
    #subprocess.call(["httrack",'--update'],cwd=self.mirror_directory)
    Processor()
    

class Processor():
  
  data_directory = 'data/cablegate/cablegate.wikileaks.org/cable'
  
  country_dictionary_path = 'data/countries.csv'
  countries = []
  country_frequency = nltk.probability.FreqDist()
  
  file_regex = re.compile("\.html$")
  
  counts = {
    'files_to_process':0,
    'files_processed':0,
    'files_not_processed':0
  }
  
  def __init__(self):
    logging.info('Processor()')
    self.load_countries()
    self.process()
  
  def process(self):
    logging.info('Processor.process')
    self.read_files()
  
  def load_countries(self):
    logging.info('Processor.load_countries')
    try:
      file = open(self.country_dictionary_path,'r')
    except OSError:
      logging.warning('Processor.CANNOT OPEN FILE '+path)
      return
    countries = csv.reader(file, delimiter=',')
    for row in countries:
      self.countries.append(row[1].lower())
    
  def read_files(self):
    logging.info('Processor.read_files')
    try:
      for root, dirs, files in os.walk(self.data_directory):
        for name in files:
          if self.file_regex.search(name) is not None:
            path = root+"/"+name
            self.counts['files_to_process'] = self.counts['files_to_process'] + 1
            self.read_file(path)
    except OSError:
      logging.info(str(OSError))
  
  def read_file(self,path):
    logging.info('Processor.read_file')
    try:
      file = open(path)
    except OSError:
      logging.warning('Processor.CANNOT OPEN FILE '+path)
      self.counts['files_not_processed'] = self.counts['files_not_processed'] + 1
      return
    self.extract_content(file.read())
    
  def extract_content(self,raw):
    logging.info('Processor.extract_content')
    
    soup = BeautifulSoup(raw)
    cable_table = soup.find("table", { "class" : "cable" })
    cable_id = cable_table.findAll('tr')[1].findAll('td')[0]\
      .contents[1].contents[0]
    if db.cables.find_one({'_id':cable_id}):
      self.counts['files_not_processed'] = self.counts['files_not_processed'] + 1
      logging.info('Processor.extract_content["CABLE ALREADY EXISTS"]')
      self.print_counts()
      return
      
    cable = Cable(raw)
    cable['_id'] = cable_id
    cable['reference_id'] = cable_id
    cable['date_time'] = cable_table.findAll('tr')[1].findAll('td')[1]\
      .contents[1].contents[0]
    cable['classification'] = cable_table.findAll('tr')[1].findAll('td')[2]\
      .contents[1].contents[0]
    cable['origin'] = cable_table.findAll('tr')[1].findAll('td')[3]\
      .contents[1].contents[0]
    cable['header'] = nltk.clean_html(str(soup.findAll(['pre'])[0]))
    cable['body'] = nltk.clean_html(str(soup.findAll(['pre'])[1]))
    
    db.cables.insert(cable.get())
    
    self.counts['files_processed'] = self.counts['files_processed'] + 1
    
    self.print_counts()
    
    if (self.counts['files_processed'] + self.counts['files_not_processed'])\
      == self.counts['files_to_process']:
      self.dump_json()
  
  def print_counts(self):
    logging.info('Processor.print_counts')
    logging.info(str(self.counts['files_to_process'])+" | "+\
      str(self.counts['files_processed'])+" | "+\
      str(self.counts['files_not_processed']))
  
  def dump_json(self):
    logging.info('Processor.dump_json')
    
CableGateMirror()
    