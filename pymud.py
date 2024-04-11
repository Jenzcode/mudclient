#!/usr/bin/python3

import socket
import sys
import os
import threading
from collections import deque
import re
import json
import time
import queue
from mudConnect import MudConnection
from mudFiles   import MudFiles

from telnet import IAC
from ansi import ansi

line_buffer = deque([])
outq = queue.Queue()
line_count = 0
last_line = ''
logFile = sys.stdout
repeat_line = 0

fn_pattern = re.compile(r"fn_([_a-zA-Z0-9]*)")
sv_pattern = re.compile(r"sv_([_a-zA-Z0-9\.]*)=([,_a-zA-Z0-9]*)")
sm_pattern = re.compile(r";+")

def sendToQueue(line):
  for l in line.split(";"):
    pline = processUserLine(l)
    if pline != "":
      outq.put(re.sub(";","\n",pline))

def mudOutput():
  spam = 0
  last_line = ""
  while True:
    toSend = outq.get().strip()+"\n"
    mc.send(toSend)
    if last_line == toSend:
      spam = spam + 1
    if spam > 18:
      mc.send(getVar("s_spamprotect")+"\n")
      spam = 0
    last_line = toSend

def processUserLine(line):
  count = 0
  while True:
    if count > 10:   # catch run away recursion
      print("Recursion Error: processUserLine()")
      break
    count = count +1
    start_line = line
    line = processAliases(line)
    line = processVars(line)
    line = processDirectives(line)
    line = processFunction(line)
    line = processHash(line)
    # If the line is unchanged .. send it, otherwise process it again
    if line == start_line:
      break
  return line

def userInput():
  last_line = ""
  # This read of stdin will block, waiting for user input
  for line in sys.stdin:
    #sys.stdout.write("echo: "+line)
    if line == "\n":
      line = last_line
    sendToQueue(line)
    last_line = line
    if line == "quit\n":
      sys.exit()

# Lines of text coming from the mud need to be printed to the screen
# but also checked for trigger patterns, and maybe altered or erased before printing
def processMudLine(mline):
  global logfile
  # get a copy of the line without ansi colours
  result = ansi.pat_escape.sub(b'',mline)
  result = ansi.pat_cr.sub(b'',result)
  # write the line to the log
  mf.writeToLog(result)
  processTriggers(result)
  sys.stdout.buffer.write(IAC.processIAC(mline))

def getVar(vname):
  x = vname.split(".")
  p = profile.get(x[0],'NV')
  if len(x) == 1 or p == 'NV':
    return(p)
  p = p.get(x[1],'NV')                                                                    
  if len(x) == 2 or p == 'NV':
    return(p)
  p = p.get(x[2],'NV')                                                                    
  if len(x) == 3 or p == 'NV':
    return(p)
  p = p.get(x[3],'NV')                                                                    
  if len(x) == 4 or p == 'NV':
    return(p)
  print("Debug Error: getVar() varname too long")
  return ""

def setVar(vname,value):
  x = vname.split(".")
  match len(x):
     case 1:
       profile[x[0]] = value
       return
     case 2:
       profile[x[0]][x[1]] = value
       return
     case 3:
       profile[x[0]][x[1]][x[2]] = value
       return
     case 4:
       profile[x[0]][x[1]][x[2]][x[3]] = value
       return
  print("Debug Error: setVar() varname too long")
  return ""

def processVars(line):
  # Get all occurances of vars in the line
  results = re.finditer(r"\$\(([a-zA-Z][\._a-zA-Z0-9]*)\)",line)
  # print("Results: ",results)
  # For each var replace it with the value
  for r in results:
    vname = r.group(1)
    vval  = getVar(vname)
    vval  = str(vval)
    line = re.sub("\$\("+vname+"\)",vval,line)
  return line

def processHash(line):
  hashPat = "#([0-9]*)(['a-zA-Z0-9 ]*)"
  #n command; indicates repeat command n times, keep as one line and insert ;
  hashes = re.finditer(hashPat,line)
  for repeat in hashes:
    expanded = ""
    print("Found # ",repeat.group(1)," : ",repeat.group(2))
    for i in range(int(repeat.group(1))):
      expanded = expanded + repeat.group(2)+";"
    line = re.sub("#"+repeat.group(1)+repeat.group(2),expanded,line,1)
    line = re.sub(";;",";",line)
  return line

def processAliases(line):
  aliases = profile["aliases"]
  # Walks are prefixed with go_
  isWalk  = re.match("go_([A-Za-z0-9].*)",line)
  # If this is a walk command, repalce it with the directions
  if isWalk:
    line = walks[isWalk.group(1)]
    print("isWalk: ",line)
    line = processAliases(line)  # recursively decode aliases embedded in the walk
  else:
    for k in aliases.keys():
      result = re.match(k,line)
      if result: # Check if line starts with an alias
        line = re.sub(k,aliases[k],line)
        if len(result.groups()) > 0:
          for i in range(len(result.groups())):
            line = re.sub("\$\("+str(i+1)+"\)",result.group(i+1),line);
            print("subbed , results: ",line)
  return line

def processFunction(line):
  # We need to remove all hooks from the line
  results = fn_pattern.finditer(line)
  # iterate through all the hooks and take action
  for r in results:
    hook = r.group(1)
    match hook:
      case "loginOff":
        setVar("tgStatus.b_login",False)
        print("Debug: turned off login trigger group")
      case "startFight":
        setVar("tgStatus.b_notFighting",False)
        setVar("tgStatus.b_fighting",True)
        if getVar("eq.s_wield2") != "":
          setVar("tgStatus.b_fighting_dual_wield",True)
        print("Debug: turned off not_fighting trigger group")
      case "stopFight":
        setVar("tgStatus.b_notFighting",True)
        setVar("tgStatus.b_fighting",False)
        if getVar("eq.s_wield2") != "":
          setVar("tgStatus.b_fighting_dual_wield",False)
        print("Debug: turned off fighting trigger group")
      case "sysExit":
        print("Hook activated system exit")
        sys.exit()
      case "Debug":
        print("Debug: ")
  line = fn_pattern.sub('',line)
  return line

def processDirectives(line):
  results = re.finditer(sv_pattern,line)
  for r in results:
    sv = r.group(1)
    vv = r.group(2)
    print("Setting: ",sv,", Value: ",vv)
    setVar(sv,vv)
  line = sv_pattern.sub('',line)
  return line

def squashSemicolons(line):
  line = sm_pattern.sub(';',line)
  if line == ";":
    line = ""
  return line

def processTriggers(line):
  global profile
  tgStatus = profile["tgStatus"]
  # iterate through groups and only process ones that are active
  for g in list(tgStatus):
    if tgStatus[g]:
      group = re.sub("b_","",g)
      # For each trigger in the active group, check and respond
      for t in trigs[group]:
        # Update the pattern with var subs
        pattern = processVars(trigs[group][t]["pattern"])
        # Search the line for the pattern
        result = re.search(str.encode(pattern),line)
        if result:
          response = processVars(trigs[group][t]["response"])
          response = processMatchGroups(response,result)
          response = processDirectives(response)
          response = squashSemicolons(response)
          print("Response: ",response)
          if len(response) > 1:
            sendToQueue(response)

def processMatchGroups(line,result):
  if result.span == (0,0):
    return line
  ngroups = len(result.groups())
  if ngroups == 0:
    return line
  for i in range(ngroups):
    gr = result.group(i+1)
    print("result: ",result,", i ",i,", ngroups: ",ngroups," Group: ",gr)
    if gr is None:
      gr = b''
    line = re.sub("\$\("+str(i+1)+"\)",gr.decode(),line);
  return line

#
# Main
#

if len(sys.argv) < 2:
  print("Character name is a required argument\n")
  sys.exit()

muddir = os.environ["HOME"]+"/var-mud/"                                                                
mf = MudFiles(muddir,sys.argv[1])
mf.openLog()

profile = mf.loadProfile()
walks   = mf.loadWalks()
trigs   = mf.loadTriggers()

mc = MudConnection( getVar("connection.s_server"),getVar("connection.i_port") )
mc.connect()

userInputThread = threading.Thread(target=userInput)
userInputThread.start()

mudOutputThread = threading.Thread(target=mudOutput)
mudOutputThread.start()

chunk = []
mlines = []
mlines.append(b'')

while True:
  chunk = mc.getChunk()  # blocks untilt the mud sends data
  if len(chunk) == 0:    # a 0 length chunk would be an EOF .. connection closed
    print("Chunk size 0 .. EXITING")
    sys.exit()

  c = 0
  lc = 0
  mlines[lc] = b''

  # We should read the data into lines terminated by newline
  # last line may not be terminated .. eg. a prompt
  # mlines : mudline
  for x in chunk:
    mlines[lc] = mlines[lc] + bytes([x])
    if x == 10:   # Newline==10, process the line and move on to next.
      processMudLine(mlines[lc])
      lc = lc + 1
      if lc == len(mlines): # Grow the buffer if it is not long enough
        mlines.append(b'')
      mlines[lc] = b''

  #There may be a line still in the buffer without a newline
  #such as when the user is being prompted. So we need to flush and process this too.
  if len(mlines[lc]) != 0:
    processMudLine(mlines[lc])

  sys.stdout.flush()

# If get here input from the mud has ceased so terminate
sys.exit()

