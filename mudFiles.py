import os
import datetime
import json

imudir = os.environ["HOME"]+"/var-mud/"

class MudFiles:
  def __init__(self,muddir,charName):
    self.muddir = muddir
    self.charName = charName

  def openLog(self):
    d = datetime.datetime.now()
    self.logFile = open(self.muddir+"logs/"+self.charName+"-logfile.txt","ab")
    self.logFile.write(str.encode("Opened Logfile: "+
          str(d.year)+"-"+
          str(d.month)+"-"+
          str(d.day)+"-"+
          str(d.hour)+"-"+
          str(d.minute)+"-"+
          str(d.second)+"\n"))
    return self.logFile

  def loadProfile(self):
    self.profileFile = open(self.muddir+"profiles/"+self.charName+".json","r")
    self.profile = json.load(self.profileFile)
    #print("Profile is: \n"+json.dumps(profile,indent=2))
    return self.profile
  
  def loadWalks(self):
    self.walkFile = open(self.muddir+"profiles/walks.json","r")
    self.walks = json.load(self.walkFile)
    return self.walks
  
  def loadTriggers(self):
    self.trFile = open(self.muddir+"profiles/triggers.json","r")
    self.trs = json.load(self.trFile)
    return self.trs
  
  def writeToLog(self,logLine):
    self.logFile.write(logLine)
    self.logFile.flush()
