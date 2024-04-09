import socket

class MudConnection:
  def __init__(self,server_ip,server_port):
    self.server_ip   = server_ip
    self.server_port = server_port

  def connect(self):
    print(  "Connecting to: "+ self.server_ip + "," + "Port: "+str(self.server_port)+"\n");
    self.s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    self.s.setblocking(1)
    self.s.connect((self.server_ip,self.server_port))

  def send(self,data):
    self.s.send(str.encode(data))

  def getChunk(self):
    return self.s.recv(4096)
