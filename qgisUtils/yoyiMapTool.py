# -*- coding: utf-8 -*-
# @Author  : yoyi
# @Time    : 2023/6/7 15:30

from osgeo import gdal
import affine
import numpy as np
from qgis.PyQt.QtCore import Qt,QRectF, QPointF,QPoint
from qgis.PyQt.QtGui import QCursor,QPixmap,QPen, QColor
from qgis.PyQt.QtWidgets import QMessageBox,QUndoStack,QComboBox,QMenu,QAction
from qgis.core import QgsMapLayer,QgsRectangle,QgsPoint,QgsDistanceArea,QgsCircle,QgsPointXY, QgsWkbTypes,QgsVectorLayer,\
    QgsVectorDataProvider,QgsFeature,QgsGeometry,QgsPolygon,QgsLineString,QgsRasterLayer,QgsProject,QgsMapSettings, \
    QgsMapRendererParallelJob,QgsWkbTypes,QgsFeatureRequest,QgsMultiPolygon,QgsMapToPixel,QgsMultiLineString
from qgis.gui import QgsMapToolEmitPoint, QgsRubberBand, QgsVertexMarker,QgsMapToolIdentify,QgsMapTool,QgsMapToolIdentifyFeature,QgsMapCanvas,QgsMapCanvasItem,QgsMapToolPan

from widgetAndDialog.mapTool_InputAttrWindow import inputAttrWindowClass

class PolygonMapTool(QgsMapToolEmitPoint):
    def __init__(self, canvas,layer,mainWindow,preField=None,preFieldValue=None,recExtent=None,otherCanvas=None,fieldValueDict=None,dialogMianFieldName=None):
        super(PolygonMapTool, self).__init__(canvas)
        self.canvas = canvas
        self.rubberBand = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry)
        self.rubberBand.setColor(QColor(255, 0, 0, 50))
        self.rubberBand.setWidth(1)
        self.wkbType = "polygon"
        self.editLayer: QgsVectorLayer = layer
        self.caps = self.editLayer.dataProvider().capabilities()
        self.mainWindow = mainWindow
        self.preField = preField
        self.preFieldValue = preFieldValue
        self.fieldValueDict = fieldValueDict
        self.dialogMianFieldName= dialogMianFieldName
        self.recExtent: QgsRectangle = recExtent
        self.otherCanvas = otherCanvas
        self.reset()

    def reset(self):
        self.is_start = False  # 开始绘图
        self.is_vertical = False  # 垂直画线
        self.cursor_point = None
        self.points = []
        self.rubberBand.reset(True)

    def changeRubberBandColor(self,r,g,b):
        self.rubberBand.setColor(QColor(r,g,b,50))

    def changeFieldValue(self,fieldValue):
        self.preFieldValue = fieldValue

    def canvasPressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.points.append(self.cursor_point)
            self.is_start = True
        elif event.button() == Qt.RightButton:
            # 右键结束绘制
            if self.is_start:
                self.is_start = False
                self.cursor_point = None
                self.p = self.polygon()

                if self.recExtent and not QgsGeometry.fromRect(self.recExtent).contains(self.p):
                    QMessageBox.about(self.mainWindow, '错误', "面矢量与图层范围不相交")
                    self.reset()
                else:
                    if self.p is not None:
                        if self.p.isGeosValid():
                            self.addFeature()
                        else:
                            QMessageBox.about(self.mainWindow, '错误', "面矢量拓扑逻辑错误")
                            self.reset()
                    else:
                        self.reset()
                #self.show_polygon()
                self.points = []
            else:
                pass

    def addFeature(self):
        if self.caps & QgsVectorDataProvider.AddFeatures:
            feat = QgsFeature(self.editLayer.fields())
            #print("可编辑？",self.editLayer.isEditable())
            inputAttrWindows = inputAttrWindowClass(self,feat,self.mainWindow)
            inputAttrWindows.exec()

    def addFeatureByDict(self,resDict:dict):
        if resDict:
            feat = QgsFeature(self.editLayer.fields())
            feat.setGeometry(self.p)
            feat.setAttributes(list(resDict.values()))
            self.editLayer.addFeature(feat)
            self.canvas.refresh()
            if self.otherCanvas:
                self.otherCanvas.refresh()
            self.reset()
            self.mainWindow.updateShpUndoRedoButton()
        else:
            self.reset()

    def canvasMoveEvent(self, event):
        self.cursor_point = event.mapPoint()
        if not self.is_start:
            return
        self.show_polygon()

    def show_polygon(self):
        if self.points:
            self.rubberBand.reset(QgsWkbTypes.PolygonGeometry)  # 防止拖影
            first_point = self.points[0]
            last_point = self.points[-1]
            if first_point and last_point:
                self.rubberBand.addPoint(first_point, False)
                for point in self.points[1:-1]:
                    self.rubberBand.addPoint(point, False)
                if self.cursor_point:
                    self.rubberBand.addPoint(QgsPointXY(last_point.x(), last_point.y()), False)
                else:
                    self.rubberBand.addPoint(QgsPointXY(last_point.x(), last_point.y()), True)
                    self.rubberBand.show()
                    return
                self.rubberBand.addPoint(self.cursor_point, True)
                self.rubberBand.show()

    def polygon(self):
        if len(self.points) <= 2:
            return None
        pointList = []
        for point in self.points:
            pointList.append(QgsPointXY(point[0],point[1]))
        return QgsGeometry.fromMultiPolygonXY([[pointList]])

    def deactivate(self):
        super(PolygonMapTool, self).deactivate()
        self.deactivated.emit()
        self.reset()
