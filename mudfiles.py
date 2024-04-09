import os
import datetime
import json

muddir = os.environ["HOME"]+"/var-mud/"

def openLog(charName):
  global muddir
  d = datetime.datetime.now()
  logFile = open(muddir+"logs/"+charName+"-logfile.txt","ab")
  logFile.write(str.encode("Opened Logfile: "+
        str(d.year)+"-"+
        str(d.month)+"-"+
        str(d.day)+"-"+
        str(d.hour)+"-"+
        str(d.minute)+"-"+
        str(d.second)+"\n"))
  return logFile

def openProfile(charName):
  global muddir
  global charFile
  charFile = open(muddir+"profiles/"+charName+".json","r")
  profile = json.load(charFile)
  #print("Profile is: \n"+json.dumps(profile,indent=2))
  return profile

def loadWalks():
  global muddir
  walkFile = open(muddir+"profiles/walks.json","r")
  walks = json.load(walkFile)
  return walks

def loadTriggers():
  global muddir
  trFile = open(muddir+"profiles/triggers.json","r")
  trs = json.load(trFile)
  return trs

