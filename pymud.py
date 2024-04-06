#!/usr/bin/python3

import socket
import sys
import os
import threading
from collections import deque
import re
import json

from telnet import IAC
import ansi
import mudfiles

line_buffer = deque([])
line_count = 0
last_line = ''
logFile = sys.stdout

def userInput():
  global line_count
  global last_line
  global s
  for line in sys.stdin:
    # Spam protection
    if line == last_line:
      print("Repeated Line ",repeat_line)
      repeat_line = repeat_line + 1
    else:
      repeat_line = 0
    if repeat_line > 5:
      line_buffer.append( "smile\n" )
      repeat_line = 0
    last_line = line

    line_buffer.append( line )
    line_count = line_count + 1
    sys.stdout.write("echo: "+line)

    # Process the line .. for aliase/macros/variables etc.
    # For now though write it to the mud
    s.send(str.encode(getUserInput()))

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

# Check for and handle IAC codes
def processIAC(mline):
  result = IAC.CAN.sub(b'IAC_CAN',mline)
  result = IAC.WILL_MXP.sub(b'WILL_MXP',result)
  result = IAC.WONT_MXP.sub(b'WONT_MXP',result)
  result = IAC.WILL_ECHO.sub(b'WILL_ECHO',result)
  result = IAC.WONT_ECHO.sub(b'WONT_ECHO',result)
  return result

# Lines of text coming from the mud need to be printed to the screen
# but also checked for trigger patterns, and maybe altered or erased before printing
def processLine(mline):
  global logfile
  global ansi_escape
  # get a copy of the line without ansi colours
  result = ansi.pat_escape.sub(b'',mline)
  # write the line to the log
  logFile.write(result)
  sys.stdout.buffer.write(processIAC(mline))

#
# Main
#

if len(sys.argv) < 2:
  print("Character name is a required argument\n")
  sys.exit()

print("Arg 1: "+sys.argv[1])

logFile = mudfiles.openLog(sys.argv[1])

profile = mudfiles.openProfile(sys.argv[1])

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

