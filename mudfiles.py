import os
import datetime
import json

def openLog(charName):
  d = datetime.datetime.now()
  muddir = os.environ["HOME"]+"/var-mud/"
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
  global charFile
  muddir = os.environ["HOME"]+"/var-mud/"
  charFile = open(muddir+"profiles/"+charName+".json","r")
  profile = json.load(charFile)
  #print("Profile is: \n"+json.dumps(profile,indent=2))
  return profile

def loadWalks():
  muddir = os.environ["HOME"]+"/var-mud/"
  walkFile = open(muddir+"profiles/walks.json","r")
  walks = json.load(walkFile)
  return walks

