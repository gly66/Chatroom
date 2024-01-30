
import os
import struct
import sys
import time
import socket
import threading
import json
import soundfile as sf
import sounddevice as sd
import tkinter as tk
import tkinter.font as tf
import tkinter.filedialog
from tkinter import scrolledtext
from scipy.io.wavfile import write




#进度条
def process_bar(precent, width=50):
    use_num = int(precent*width)
    space_num = int(width-use_num)
    precent = precent*100

    print('[%s%s]%d%%'%(use_num*'#', space_num*' ',precent),file=sys.stdout,flush=True, end='\r')

# 将数字转为定长的字符串 
def format(num, length, filler='0', position=0): 
    num = str(num) # num可以是数字或字符串
    while len(num) < length:
        if position == 0:
            num = filler + num
        else:
            num = num + filler
    return num


def recvall(self, length): 
    data = b''
    while len(data) < length:
        data += self.recv(length - len(data))
    return data
socket.socket.recvall = recvall

# 绑定事件 发送用户名
def send_username(username = ''):
    if username == '':
        return
    
    username = username.encode('utf-8')
    username = ('0' + format(len(username), 2)).encode('utf-8') + username

    threadLock.acquire()
    messages.append(username)
    threadLock.release()


# 发送文件
def send_filenamesize():
    global messages
    global threadLock

    filepath = tkinter.filedialog.askopenfilename()

    filesize = os.path.getsize(filepath)
    filemes = {'filepath': filepath, 'filesize': filesize}
    head_info_mes = json.dumps(filemes).encode('utf-8')
    head_info_len = len(head_info_mes)
    with open(filepath, 'rb') as f:
        filecont = f.read()
    message = ('2' + format(head_info_len, 4)).encode('utf-8') + head_info_mes +filecont

    
    threadLock.acquire()
    messages.append(message)
    threadLock.release()

#发送语音
def send_sound():
    fs = 44100 # Sample rate
    seconds = 3 # Duration of recording
 
    myrecording = sd.rec(int(seconds * fs), samplerate=fs, channels=2)
    sd.wait() # Wait until recording is finished
    write('output.wav', fs, myrecording) # Save as WAV file
    filename = 'output.wav'
    filesize = os.path.getsize(filename)
    filemes = {'filename': filename, 'filesize': filesize}
    head_info_mes = json.dumps(filemes).encode('utf-8')
    head_info_len = len(head_info_mes)
    with open(filename, 'rb') as f:
        filecont = f.read()
    message = ('3' + format(head_info_len, 4)).encode('utf-8') + head_info_mes +filecont
    
    threadLock.acquire()
    messages.append(message)
    threadLock.release()

# 绑定事件， 发送输入框的内容并清空输入框
def send_message(event=None): 
    global messages
    global threadLock
    global text_input
    
    message = text_input.get('0.0','end').encode('utf-8')
    text_input.delete(1.0, tk.END)

    message = ('1' + format(len(message), 4)).encode('utf-8') + message

    threadLock.acquire()
    messages.append(message)
    threadLock.release()

    return 'break' 

# 用于发送信息的线程方法
def Send(client): 
    global messages
    global threadLock # 线程锁 防止多个线程同时修改数据造成错误

    while True:
        if len(messages):
            threadLock.acquire() # 锁定全局资源
            message = messages[0]
            del messages[0]
            threadLock.release() # 释放全局资源

            try:
                client.sendall(message)
            except:
                print('Error: server closed!')
                return
        
        else:
            time.sleep(0.1)

# 用于接收信息的线程方法
def Recv(client): 
    global text_show

    while True:
        try: 
            h = client.recvall(1).decode('utf-8')
            if h =='1':
                length = int(client.recvall(2).decode('utf-8'))
                username = client.recvall(length).decode('utf-8') # 信息的发送者
                length = int(client.recvall(2).decode('utf-8'))
                cur_time = client.recvall(length).decode('utf-8') # 信息的发送时间
                length = int(client.recvall(4).decode('utf-8'))
                message = client.recvall(length).decode('utf-8') # 信息的内容
                print('REC a message!')
                text_show['state'] = tk.NORMAL 
                text_show.insert("end", username + ' ', 'username') # 最后一个参数看116到122行
                text_show.insert("end", cur_time + '\n', 'time')
                text_show.insert("end", message, 'message')
                text_show['state'] = tk.DISABLED
            

            elif h =='2':
                #接受报头，包含文件名字和大小
                head_len = int(client.recvall(4).decode('utf-8'))
                head_struct = json.loads(client.recvall(head_len).decode('utf-8'))
                filepath = head_struct['filepath']
                filesize = head_struct['filesize']
                
                filename = os.path.basename(filepath)
             
                print('Received a file',filename,)
                a = input('input A to receive\n')
                #接受文件内容
                if a== 'A':
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
            
            elif h =='3': #接受语音
                 #接受报头，包含文件名字和大小
                head_len = int(client.recvall(4).decode('utf-8'))
                head_struct = json.loads(client.recvall(head_len).decode('utf-8'))
                filename = head_struct['filename']
                filesize = head_struct['filesize']
                
             
                print('Received a sound',filename,)
                a = input('input B to rec and play\n')
                 #接受文件内容
                if a== 'B':
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
                    f.close()
                data, fs = sf.read(filename, dtype='float32') 
                sd.play(data, fs)
                status = sd.wait() 
                now = time.time()
                stamp = int(now - old)
                print('总共用时%ds' % stamp)  

        except:
            return

def to_login():
    global root
    global frame_login
    global frame_chatroom

    global thread_send
    global thread_recv

    # 设定窗口的长度和宽度，并在屏幕中居中显示
    width = 215
    height = 90
    screenwidth = root.winfo_screenwidth() 
    screenheight = root.winfo_screenheight()
    alignstr = '%dx%d+%d+%d' % (width, height, (screenwidth-width)/2, (screenheight-height)/2)
    root.geometry(alignstr)

    # 将聊天室界面(初始时为空)改为登陆界面
    frame_login.grid()
    frame_chatroom.grid_forget()

def to_chatroom(event=None):
    global host, port
    global root
    global frame_login
    global frame_chatroom
    global entry_username

    # 设定窗口的长度和宽度，并在屏幕中居中显示
    width = 716
    height = 600
    screenwidth = root.winfo_screenwidth() 
    screenheight = root.winfo_screenheight()
    alignstr = '%dx%d+%d+%d' % (width, height, (screenwidth-width)/2, (screenheight-height)/2)
    root.geometry(alignstr)

    send_username(entry_username.get())

    # 将登陆界面改为聊天室界面
    frame_login.grid_forget()
    frame_chatroom.grid()

    client.connect((host, port)) #发起TCP连接！！！！

    thread_send.start()
    thread_recv.start()

host = '127.0.0.1' # 服务器ip地址，如果在本机上测试可以使用 '127.0.0.1'
port = 32540          # 端口，与server.py中设定相同的端口
messages = [] # 储存将要发送的信息
threadLock = threading.Lock() # 线程锁 防止多个线程同时修改数据造成错误

#UI设计
root = tk.Tk()

ft = tf.Font(size=10)

root.title('小飞猪聊天室')

frame_login = tk.Frame(root)
frame_chatroom = tk.Frame(root)

label_username = tk.Label(frame_login, text='用户名')
entry_username = tk.Entry(frame_login)
btn_login = tk.Button(frame_login, text='登录', command=lambda :to_chatroom())
text_show = tk.Text(frame_chatroom, width=100, height=30, state=tk.DISABLED)  #显示框，用于显示信息， 用户不能修改里面的内容
text_input = tk.Text(frame_chatroom, width=100, height=11)                    #输入框，用于输入信息
btn_sendfile = tk.Button(frame_chatroom, text='文件', width=8,command=lambda :send_filenamesize())
btn_sendsound = tk.Button(frame_chatroom, text='语音', width=8,command=lambda :send_sound())
btn_send = tk.Button(frame_chatroom, text='发送', width=8, command=lambda :send_message()) #发送按钮，发送输入框中的信息并清空输入框


label_username.grid(row=0, column=0, padx=5, pady=10)
entry_username.grid(row=0, column=1, padx=5, pady=10)
btn_login.grid(row=1, column=0, columnspan=2, padx=5, pady=5)
text_show.grid(row=0, column=0, padx=5, pady=5)
text_input.grid(row=1, column=0, padx=5, pady=5)
btn_sendfile.grid(row=2, column=0, padx=15, pady=3, sticky=tk.SW)
btn_sendsound.grid(row=2, column=0, padx=15, pady=3)

btn_send.grid(row=2, column=0, padx=15, pady=3, sticky=tk.E)

entry_username.bind('<Return>', to_chatroom)
text_input.bind('<Control-Return>', send_message) # 绑定事件：按下CTRL+Enter后发送信息

#三种不同的字体格式， 在这个例子里仅有颜色不同
text_show.tag_add('username', 0.0)
text_show.tag_config('username', foreground='green',font =ft) # 用户名用绿色
text_show.tag_add('time', 0.0)
text_show.tag_config('time', foreground='blue',font =ft)      # 时间用蓝色
text_show.tag_add('message', 0.0)
text_show.tag_config('message', foreground='black',font =ft)  # 信息内容用默认的黑色

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  #！创建客户套接字！！！！

thread_send = threading.Thread(target=Send, args=(client, ))
thread_recv = threading.Thread(target=Recv, args=(client, ))
# 设置为守护线程，这样当窗口关闭时两个线程也会关闭
thread_send.setDaemon(True)
thread_recv.setDaemon(True)

to_login()

root.mainloop()
