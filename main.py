from qgis.PyQt import QtCore
from qgis.core import QgsApplication
from PyQt5.QtCore import Qt
import os
import traceback
from mainWindow import MainWindow

if __name__ == '__main__':
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