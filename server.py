
import os
import struct
import sys
import time
import socket
import threading
from datetime import datetime
import json
import tkinter as tk
import tkinter.font as tf
import tkinter.filedialog
from tkinter import scrolledtext


# 将数字转为定长的字符串 
def format(num, length, filler='0', position=0):
    num = str(num)
    while len(num) < length:
        if position == 0:
            num = filler + num
        else:
            num = num + filler
    return num

#进度条
def process_bar(precent, width=50):
    use_num = int(precent*width)
    space_num = int(width-use_num)
    precent = precent*100

    print('[%s%s]%d%%'%(use_num*'#', space_num*' ',precent),file=sys.stdout,flush=True, end='\r')

def recvall(self, length):
    data = b''
    while len(data) < length:
        data += self.recv(length - len(data))
    return data
socket.socket.recvall = recvall

# 用于发送信息的线程方法
def Send():
    global clients
    global messages
    global threadLock # 线程锁 防止多个线程同时修改数据造成错误

    del_lis = []

    while True:
        if len(messages):
            threadLock.acquire()  # 锁定全局资源
            message = messages[0]
            del messages[0]
            threadLock.release()  # 释放全局资源

            for client in clients.keys():
                try:
                    client.sendall(message)
                except: # 出现异常表示用户断开连接，将该用户从clients中移除
                    del_lis.append(client)
            
            for client in del_lis:
                print(clients[client])
                del clients[client]
            del_lis.clear()
        
        else:
            time.sleep(0.1)

# 用于接收信息的线程方法
def Recv(client):
    dt = datetime
    while True:
        try:
            h = client.recvall(1).decode('utf-8')

            if h == '0': # 用户设定用户名
                length = int(client.recvall(2).decode('utf-8'))
                username = client.recvall(length).decode('utf-8')
                clients[client] = username

            elif h == '1': # 接收用户发送的信息并转发给所有用户
                length = int(client.recvall(4).decode('utf-8'))
                message = client.recvall(length) # 信息内容
                cur_time = dt.now().strftime('%Y-%m-%d %H:%M:%S').encode('utf-8') # 服务器收到信息的时间，使用服务器接收的时间而不是客户端发送时间以防止时间的错乱
                username = clients[client].encode('utf-8') # 获取该用户的用户名

                threadLock.acquire() 
                messages.append(('1' + format(len(username), 2)).encode('utf-8') + username + format(len(cur_time), 2).encode('utf-8') + cur_time + format(len(message), 4).encode('utf-8') + message)
                threadLock.release() 
            elif h== '2':   #接收文件
                #接受报头，包含文件名字和大小
                head_len = int(client.recvall(4).decode('utf-8'))
                head_struct = json.loads(client.recvall(head_len).decode('utf-8'))
                filepath = head_struct['filepath']
                filesize = head_struct['filesize']
                
                filename = os.path.basename(filepath)

                #接收文件内容
                buffersize = 1024
                recv_len = 0
                recv_mesg=b''
                old = time.time()   
                f = open(filename,'wb')
                while recv_len < filesize :
                    percent = recv_len / filesize
                    process_bar(percent)
                    
                    if filesize - recv_len > buffersize:
                        recv_mesg = client.recvall(buffersize)
                        f.write(recv_mesg)
                        recv_len += len(recv_mesg)
                    else:
                        recv_mesg = client.recvall(filesize - recv_len)
                        recv_len += len(recv_mesg)
                        f.write(recv_mesg)
                now = time.time()
                stamp = int(now - old)
                print('总共用时%ds' % stamp)
                f.close()
                #转发给客户
                F = open(filename,'rb')
                filecont = F.read()
                filemes = {'filepath': filepath, 'filesize': filesize}
                head_info_mes = json.dumps(filemes).encode('utf-8')
                head_info_len = len(head_info_mes)
                message = ('2' + format(head_info_len, 4)).encode('utf-8') + head_info_mes + filecont
                F.close()
                threadLock.acquire()
                messages.append(message)
                threadLock.release()

            elif h=='3':
                #接受语音
                head_len = int(client.recvall(4).decode('utf-8'))
                head_struct = json.loads(client.recvall(head_len).decode('utf-8'))
                filename = head_struct['filename']
                filesize = head_struct['filesize']

                buffersize = 1024
                recv_len = 0
                recv_mesg=b''
                old = time.time()   
                f = open(filename,'wb')
                while recv_len < filesize :
                    percent = recv_len / filesize
                    process_bar(percent)
                    
                    if filesize - recv_len > buffersize:
                        recv_mesg = client.recvall(buffersize)
                        f.write(recv_mesg)
                        recv_len += len(recv_mesg)
                    else:
                        recv_mesg = client.recvall(filesize - recv_len)
                        recv_len += len(recv_mesg)
                        f.write(recv_mesg)
                now = time.time()
                stamp = int(now - old)
                print('总共用时%ds' % stamp)
                f.close()
                #转发给客户
                F = open(filename,'rb')
                filecont = F.read()
                filemes = {'filename': filename, 'filesize': filesize}
                head_info_mes = json.dumps(filemes).encode('utf-8')
                head_info_len = len(head_info_mes)
                message = ('3' + format(head_info_len, 4)).encode('utf-8') + head_info_mes + filecont
                F.close()
                threadLock.acquire()
                messages.append(message)
                threadLock.release()

        except:
            return

host = ''
port = 32540 #端口，client.py中要设置相同的端口

clients = {}  #存储用户信息 键为客户的socket， 值为用户名
messages = [] #储存将要发送的信息

threadLock = threading.Lock() # 线程锁 防止多个线程同时修改数据造成错误

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((host, port))
server.listen(20) 
print('等待连接......')

thread_send = threading.Thread(target=Send, args=())
thread_send.start()

while True:
    client, addr = server.accept()
    clients[client] = addr[0] # 默认使用ip地址作为用户名
    print(addr,'connect') 

    thread_recv = threading.Thread(target=Recv, args=(client,))
    thread_recv.start()  
    