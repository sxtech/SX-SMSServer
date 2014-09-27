# -*- coding: cp936 -*-
from PyQt4 import QtGui, QtCore
import time,sys,os
import logging
import logging.handlers
import gl
from mser import SMSSer
from singleinstance import singleinstance
    
def initLogging(logFilename):
    """Init for logging"""
    path = os.path.split(logFilename)
    if os.path.isdir(path[0]):
        pass
    else:
        os.makedirs(path[0])
    logger = logging.getLogger('root')
    
    Rthandler = logging.handlers.RotatingFileHandler(logFilename, maxBytes=10*1024*1024,backupCount=5)
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(filename)s[line:%(lineno)d] [%(levelname)s] %(message)s',
                                  datefmt='%Y-%m-%d %H:%M:%S')
    Rthandler.setFormatter(formatter)
    logger.addHandler(Rthandler)
    
#版本号
def version():
    return 'SX-SMSServer V0.2.0'
 
class MyThread(QtCore.QThread):
    trigger = QtCore.pyqtSignal(str)
 
    def __init__(self, parent=None):
        super(MyThread, self).__init__(parent)
 
    def run(self):
        gl.TRIGGER = self.trigger
        m = dcmain(self.trigger)
        m.mainloop()
        del m

class dcmain:
    def __init__(self,trigger):
        gl.TRIGGER.emit("<font size=6 font-weight=bold face=arial color=tomato>%s</font>"%('Welcome to use '+version()))
        self.sms = SMSSer()

    def __del__(self):
        del self.sms

    def mainloop(self):
        self.sms.main()

#主窗口类
class MainWindow(QtGui.QMainWindow):
    def __init__(self, parent=None):  
        super(MainWindow, self).__init__(parent)
        self.resize(650, 450)
        self.setWindowTitle(version())
        
        self.text_area = QtGui.QTextBrowser()
 
        central_widget = QtGui.QWidget()
        central_layout = QtGui.QHBoxLayout()
        central_layout.addWidget(self.text_area)
        central_widget.setLayout(central_layout)
        self.setCentralWidget(central_widget)

        exit = QtGui.QAction(QtGui.QIcon('icons/exit.png'), 'Exit', self)
        exit.setShortcut('Ctrl+Q')
        exit.setStatusTip('Exit application')
        self.connect(exit, QtCore.SIGNAL('triggered()'), self.closeGUI)

        self.statusBar()

        menubar = self.menuBar()
        file = menubar.addMenu('&File')
        file.addAction(exit)
        
        toolbar = self.addToolBar('Exit')
        toolbar.addAction(exit)
        
        self.setWindowIcon(QtGui.QIcon('icons/logo.png'))

        self.count = 0
        
        self.createActions()
        self.createTray()
        
        self.start_threads()
        
    def closeEvent(self, event):
        event.ignore()
        self.hide()

    #创建托盘菜单动作
    def createActions(self):    
        self.restoreAction = QtGui.QAction(u"显示|隐藏", self)
        self.connect(self.restoreAction, QtCore.SIGNAL('triggered()'), self.show_hide)
        
        self.quitAction = QtGui.QAction(QtGui.QIcon( 'icons/exit.png' ), u'退出', self)
        self.connect(self.quitAction, QtCore.SIGNAL('triggered()'), self.logout)

    #创建系统托盘
    def createTray(self):
        # 创建托盘
        self.icon = QtGui.QIcon("icons\logo.png")
         
        self.trayIcon = QtGui.QSystemTrayIcon(self)
        self.trayIcon.setIcon(self.icon)
        self.trayIcon.show()

        # 托盘菜单
        self.menu = QtGui.QMenu(self)
        self.menu.addAction(self.restoreAction)
        self.menu.addSeparator()
        self.menu.addAction(self.quitAction)
        self.trayIcon.setContextMenu(self.menu)

    def show_hide(self):
        if self.isHidden():
            self.showNormal()
        else:
            self.hide()
            
    #托盘菜单退出
    def logout(self):
        gl.QTFLAG = False
        while gl.DCFLAG == True:
            time.sleep(1)
        sys.exit()

    #退出GUI
    def closeGUI(self):
        reply = QtGui.QMessageBox.question(self, 'Message',
            u"确定要退出吗?", QtGui.QMessageBox.Yes |
            QtGui.QMessageBox.No, QtGui.QMessageBox.No)
        if reply == QtGui.QMessageBox.Yes:
            gl.QTFLAG = False
            while gl.DCFLAG == True:
                time.sleep(1)
            sys.exit()
        else:
            pass
        
    def start_threads(self):
        self.threads = []              # this will keep a reference to threads
        thread = MyThread(self)        # create a thread
        thread.trigger.connect(self.update_text)  # connect to it's signal
        thread.start()                 # start the thread
        self.threads.append(thread)    # keep a reference      
 
    def update_text(self, message):
        self.count += 1
        if self.count >1000:
            self.text_area.clear()
            self.count = 0
        self.text_area.append(unicode(message, 'gbk'))
        
if __name__ == '__main__':
    myapp = singleinstance()
    if myapp.aleradyrunning():
        print version(),'已经启动!3秒后自动退出...'
        time.sleep(3)
        sys.exit(0)

    initLogging(r'log\sms.log')
    logger = logging.getLogger('root')
    
    app = QtGui.QApplication(sys.argv)
 
    mainwindow = MainWindow()
    mainwindow.show()
 
    sys.exit(app.exec_())

