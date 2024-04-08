#!/usr/bin/python3

import socket
import sys
import os
import threading
from collections import deque
import re
import json
import triggers
import time
import queue

from telnet import IAC
from ansi import ansi
import mudfiles

line_buffer = deque([])
outq = queue.Queue()
line_count = 0
last_line = ''
logFile = sys.stdout
repeat_line = 0

hook_pattern = re.compile(r"\@\(([_a-zA-Z]*)\)")

def sendToQueue(line):
  # Process Hash - which will split into multiple lines
  lines = processHash(line)                                                                           
  for l in lines:
    outq.put(re.sub(";","\n",processUserLine(l)))

def mudOutput():
  spam = 0
  last_line = ""
  while True:
    toSend = outq.get().strip()+"\n"
    s.send(str.encode(toSend))
    if last_line == toSend:
      spam = spam + 1
      print("spamcount: ",spam)
    if spam > 18:
      print("spam var is: ",getVar("spamprotect"))
      s.send(str.encode(getVar("spamprotect")+"\n"))
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
    line = processHooks(line)                                                                          
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
  logFile.write(result)
  logFile.flush()
  processTriggers(result)
  sys.stdout.buffer.write(IAC.processIAC(mline))

def getVar(vname):
  x = vname.split(".")
  match len(x):
     case 1:
       return profile[x[0]]
     case 2:
       return profile[x[0]][x[1]]
     case 3:
       return profile[x[0]][x[1]][x[2]]
     case 4:
       return profile[x[0]][x[1]][x[2]][x[3]]
  print("Debug Error: varname too long")
  return ""

def processVars(line):
  # Get all occurances of vars in the line
  results = re.finditer(r"\$\(([\._a-zA-Z0-9]*)\)",line)
  # print("Results: ",results)
  # For each var replace it with the value
  for r in results:
    vname = r.group(1)
    vval  = getVar(vname)
    line = re.sub("\$\("+vname+"\)",vval,line)
  return line

def processHash(line):
  hashPat = "#([0-9]*)([a-zA-Z0-9 ]*)"
  #n command; indicates repeat command n times
  hashes = re.finditer(hashPat,line)
  for repeat in hashes:
    expanded = ""
    print("Found # ",repeat.group(1)," : ",repeat.group(2))
    for i in range(int(repeat.group(1))):
      expanded = expanded + repeat.group(2)+";"
    line = re.sub("#"+repeat.group(1)+repeat.group(2),expanded,line,1)
    print("Line: ",line)
    line = re.sub(";;",";",line)
  # Return list of lines
  lines = line.split(";")      
  return lines

def processAliases(line):
  aliases = profile["aliases"]
  # Walks are prefixed with go_
  isWalk  = re.match("go_([A-Za-z0-9].*)",line)
  # If this is a walk command, repalce it with the directions
  if isWalk:
    line = walks[isWalk.group(1)]
    line = processAliases(line)  # recursively decode aliases embedded in the walk
  else:
    for k in aliases.keys():
      # Check if line starts with an alias 
      line = re.sub("^"+k,aliases[k],line)
      line = re.sub(";"+k,";"+aliases[k],line)
  return line

def processHooks(line):
  # We need to remove all hooks from the line
  results = re.finditer(r"\@\(([\._a-zA-Z0-9]*)\)",line)
  # remove them from the lines
  line = hook_pattern.sub('',line)
  # iterate through all the hooks and take action
  for r in results:
    hook = r.group(1)
    match hook:
      case "tg_login_off":
        profile["tg_status"]["tg_login"] = False
        print("Debug: turned off login trigger group")
      case "sys_exit":
        print("Hook activated system exit")
        sys.exit()
      case "Debug":
        print("Debug: ")
  return line

def processTriggers(line):
  global profile
  tg_status = profile["tg_status"]
  tGroups = profile["trigger_groups"]
  # iterate through groups and only process ones that are active
  for g in tg_status:
    if tg_status[g]:
      # For each trigger in the active group, check and respond
      for t in tGroups[g]:
        # Update the pattern with var subs
        pattern = processVars(tGroups[g][t]["pattern"])
        # Search the line for the pattern
        result = re.search(str.encode(pattern),line)
        if result:
          sendToQueue(tGroups[g][t]["response"])

#
# Main
#

if len(sys.argv) < 2:
  print("Character name is a required argument\n")
  sys.exit()

print("Arg 1: "+sys.argv[1])

logFile = mudfiles.openLog(sys.argv[1])

profile = mudfiles.openProfile(sys.argv[1])
walks = mudfiles.loadWalks()

server_ip   = profile["connection"]["server"];
server_port = profile["connection"]["port"];

print(  "Connecting to: "+ server_ip + "," + "Port: "+str(server_port)+"\n");

s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
s.setblocking(1)
s.connect((server_ip,server_port))

userInputThread = threading.Thread(target=userInput)
userInputThread.start()

mudOutputThread = threading.Thread(target=mudOutput)
mudOutputThread.start()

chunk = []
mlines = []
mlines.append(b'')

while True:
  chunk = s.recv(4096)

  # a 0 length chunk would be an error
  if len(chunk) == 0:
    print("Chunk size 0 .. EXITING")
    sys.exit()

  #print("Mlines length: ",len(mlines))

  c = 0
  lc = 0
  mlines[lc] = b''

  # We should read the data into lines terminated by newline
  # last line may not be terminated .. eg. a prompt
  # mlines : mudline
  for x in chunk:
    mlines[lc] = mlines[lc] + bytes([x])
    if x == 10:
      #print("new line: mlines len: ",len(mlines))
      processMudLine(mlines[lc])
      lc = lc + 1
      if lc == len(mlines): # Grow the buffer if it is not long enough
        mlines.append(b'')
        #print("Debug : mlines buffersize: ",len(mlines))
      mlines[lc] = b''

  #There may be a line still in the buffer without a newline
  #such as when the user is being prompted. So we need to flush and process this too.
  #print("Flushing")
  if len(mlines[lc]) != 0:
    processMudLine(mlines[lc])
  sys.stdout.flush()

# If get here input from the mud has ceased so terminate
sys.exit()

