#!/usr/bin/python3

import socket
import sys
import os
import threading
from collections import deque
import re
import json
import triggers

from telnet import IAC
from ansi import ansi
import mudfiles

line_buffer = deque([])
line_count = 0
last_line = ''
logFile = sys.stdout
varDict = {}

def sendToMud(line):
  global s
  global last_line
  # Spam protection
  if line == last_line:
    print("Repeated Line ",repeat_line)
    repeat_line = repeat_line + 1
  else:
    repeat_line = 0
  if repeat_line > 5:
    s.send(str.encode(varsDict["spam_protect"]))
    repeat_line = 0
  last_line = line
  # Sub in vars 
  line = processVars(line)
  s.send(str.encode(line))

def userInput():
  # This read of stdin will block, waiting for user input
  for line in sys.stdin:
    sys.stdout.write("echo: "+line)
    sendToMud(line)

def getUserInput():
  global line_count
  line_count = line_count - 1
  return line_buffer.popleft()

def isUserInput():
  global line_count
  if line_count > 0:
    return true
  else:
    return false

# Lines of text coming from the mud need to be printed to the screen
# but also checked for trigger patterns, and maybe altered or erased before printing
def processLine(mline):
  global logfile
  # get a copy of the line without ansi colours
  result = ansi.pat_escape.sub(b'',mline)
  # write the line to the log
  logFile.write(result)
  logFile.flush()
  #triggers.process(mline)
  sys.stdout.buffer.write(IAC.processIAC(mline))

# initialize a dictionary with values from the profile
# these will be used when make 'var' subs in triggers/aliases
def initVars(profile):
  global varDict
  for v in profile["vars"]:
    varDict[v] = profile["vars"][v]
    words = re.split("\.",varDict[v])
    print("Words: ",words)
    if len(words) == 1:
     varDict[v] = profile[words[0]]
    if len(words) == 2:
     varDict[v] = profile[words[0]][words[1]]
    if len(words) == 3:
     varDict[v] = profile[words[0]][words[1]][words[2]]
    print("Read Var: ",v,", Assigned: ",varDict[v])
  return varDict

def processVars(line):
  for k in varDict.keys():
    # Get all occurances of vars in the line
    results = re.finditer(r"\$\(([a-zA-Z]*)\)",line)
    print("Results: ",results)
    # For each var replace it with the value
    for r in results:
      line = re.sub("\$\("+r.group(1)+"\)",varDict[r.group(1)],line)
      print("Var subs: ",line)
  return line

def processTriggers(line)
  # iterate through groups and only process ones that are active
  for g in trGroup:
    if trGroup[g]:
      for t in triggers[g]:
        # Search the line for the pattern
        result = re.search(t["pattern"],line)
        if result:
          sendToMud(t["response"])

#
# Main
#

if len(sys.argv) < 2:
  print("Character name is a required argument\n")
  sys.exit()

print("Arg 1: "+sys.argv[1])

logFile = mudfiles.openLog(sys.argv[1])

profile = mudfiles.openProfile(sys.argv[1])
mVars = initVars(profile)

server_ip   = profile["connection"]["server"];
server_port = profile["connection"]["port"];

print(  "Connecting to: "+ server_ip + "," + "Port: "+str(server_port)+"\n");

s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
s.setblocking(1)
s.connect((server_ip,server_port))

userInputThread = threading.Thread(target=userInput)
userInputThread.start()

chunk = []
mlines = []
mlines.append(b'')

while True:
  chunk = s.recv(4096)

  print("Debug: Chunk len: ",len(chunk))

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
      processLine(mlines[lc])
      lc = lc + 1
      if lc == len(mlines): # Grow the buffer if it is not long enough
        mlines.append(b'')
        #print("Debug : mlines buffersize: ",len(mlines))
      mlines[lc] = b''

  #There may be a line still in the buffer without a newline
  #such as when the user is being prompted. So we need to flush and process this too.
  #print("Flushing")
  if len(mlines[lc]) != 0:
    processLine(mlines[lc])
  sys.stdout.flush()

# If get here input from the mud has ceased so terminate
sys.exit()

