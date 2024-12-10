from qgis.PyQt import QtCore
from qgis.core import QgsApplication
from PyQt5.QtCore import Qt
import os
import traceback
from mainWindow import MainWindow
import sys


def global_exception_handler(type, value, traceback):
    # 全局异常处理器，忽略所有异常
    print(f"捕获到异常: {value}, 但已被忽略")

if __name__ == '__main__':

    # 设置全局异常处理器
    sys.excepthook = global_exception_handler

    try:
        QgsApplication.setPrefixPath(r'D:\gongju\qgis\apps\qgis', True)
        QgsApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
        app = QgsApplication([], True)

        t = QtCore.QTranslator()
        t.load(r'.\zh-Hans.qm')
        app.installTranslator(t)

        app.initQgis()

        mainWindow = MainWindow()
        mainWindow.show()
        # tif = r"D:\test.tif"
        # mainWindow.addRasterLayer(tif)
        # shp = r"D:\gongju\DiTuWenJian\china_SHP\国界_Project.shp"
        # mainWindow.addVectorLayer(shp)


        app.exec_()
        app.exitQgis()

    except Exception as e:
        # 如果出现任何异常，将被捕获并打印（但不会停止程序）
        print(f"捕获到异常: {e}, 但已被忽略")

    finally:
        # 确保在程序退出时退出 QGIS
        app.exitQgis()
        print("QGIS 退出")


