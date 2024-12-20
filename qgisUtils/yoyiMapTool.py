# -*- coding: utf-8 -*-
# @Author  : yoyi
# @Time    : 2024/12/20 15:32

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
from PyQt5.QtWidgets import QInputDialog
import math

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


class PointMapTool(QgsMapToolEmitPoint):
    def __init__(self, canvas, layer, mainWindow=None):
        super(PointMapTool, self).__init__(canvas)
        self.canvas = canvas
        self.rubberBand = QgsRubberBand(self.canvas, QgsWkbTypes.PointGeometry)
        self.rubberBand.setColor(QColor(255, 0, 0, 150))  # 设置点的颜色
        self.rubberBand.setWidth(5)  # 设置点的大小
        self.editLayer: QgsVectorLayer = layer
        self.caps = self.editLayer.dataProvider().capabilities()
        self.mainWindow = mainWindow
        self.reset()

    def reset(self):
        """ 重置状态 """
        self.cursor_point = None
        self.rubberBand.reset(True)

    def canvasPressEvent(self, event):
        """ 当鼠标按下时，开始绘制点 """
        if event.button() == Qt.LeftButton:
            self.cursor_point = event.mapPoint()  # 获取点击位置的地图坐标
            self.addFeature()

    def addFeature(self):
        """ 向图层添加点要素，并手动输入 id """
        if self.caps & QgsVectorDataProvider.AddFeatures:
            # 获取用户输入的 id
            id, ok = QInputDialog.getInt(None, "输入ID", "请输入点的ID:", 1, 0, 1000000, 1)
            if not ok:
                return  # 如果用户取消输入，不添加要素

            # 创建一个新的要素
            feature = QgsFeature(self.editLayer.fields())
            point = QgsGeometry.fromPointXY(self.cursor_point)
            feature.setGeometry(point)

            # 设置属性 (x, y, id)
            feature.setAttributes([self.cursor_point.x(), self.cursor_point.y(), id])

            # 添加到图层
            self.editLayer.dataProvider().addFeature(feature)
            self.editLayer.updateExtents()
            self.canvas.refresh()

    def canvasMoveEvent(self, event):
        """ 当鼠标移动时，显示点 """
        self.cursor_point = event.mapPoint()
        self.show_point()

    def show_point(self):
        """ 在鼠标移动时显示点的 rubberBand 效果 """
        self.rubberBand.reset(QgsWkbTypes.PointGeometry)
        self.rubberBand.addPoint(self.cursor_point, True)
        self.rubberBand.show()

    def deactivate(self):
        """ 当工具停用时，重置状态 """
        super(PointMapTool, self).deactivate()
        self.reset()
        self.deactivated.emit()



class LineMapTool(QgsMapToolEmitPoint):
    def __init__(self, canvas, layer, mainWindow, otherCanvas=None):
        super(LineMapTool, self).__init__(canvas)
        self.canvas = canvas
        self.rubberBand = QgsRubberBand(self.canvas, QgsWkbTypes.LineGeometry)
        self.rubberBand.setColor(QColor(0, 0, 255, 150))
        self.rubberBand.setWidth(2)
        self.editLayer: QgsVectorLayer = layer
        self.caps = self.editLayer.dataProvider().capabilities()
        self.mainWindow = mainWindow
        self.otherCanvas = otherCanvas
        self.reset()

    def reset(self):
        self.is_start = False  # 是否开始绘图
        self.points = []
        self.rubberBand.reset(True)

    def canvasPressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.points.append(event.mapPoint())
            self.is_start = True
        elif event.button() == Qt.RightButton:
            # 右键结束绘制
            if self.is_start:
                self.is_start = False
                self.p = self.line()
                if self.p is not None:
                    if self.p.isGeosValid():
                        self.addFeature()
                    else:
                        QMessageBox.about(self.mainWindow, '错误', "线要素拓扑逻辑错误")
                        self.reset()
                else:
                    self.reset()

    def addFeature(self):
        if self.caps & QgsVectorDataProvider.AddFeatures:
            feat = QgsFeature(self.editLayer.fields())
            feat.setGeometry(self.p)
            self.editLayer.addFeature(feat)
            self.canvas.refresh()
            if self.otherCanvas:
                self.otherCanvas.refresh()
            self.reset()

    def canvasMoveEvent(self, event):
        if not self.is_start:
            return
        self.rubberBand.reset(QgsWkbTypes.LineGeometry)
        self.points.append(event.mapPoint())
        for point in self.points:
            self.rubberBand.addPoint(point, False)
        self.rubberBand.addPoint(event.mapPoint(), True)
        self.rubberBand.show()

    def line(self):
        if len(self.points) < 2:
            return None
        pointList = [QgsPointXY(p.x(), p.y()) for p in self.points]
        return QgsGeometry.fromPolylineXY(pointList)

    def deactivate(self):
        super(LineMapTool, self).deactivate()
        self.deactivated.emit()
        self.reset()


class LineMapTool_1(QgsMapToolEmitPoint):
    def __init__(self, canvas, layer, mainWindow, otherCanvas=None):
        super(LineMapTool_1, self).__init__(canvas)
        self.canvas = canvas
        self.rubberBand = QgsRubberBand(self.canvas, QgsWkbTypes.LineGeometry)
        self.rubberBand.setColor(QColor(255, 0, 0, 150))  # 使用红色表示直线
        self.rubberBand.setWidth(2)
        self.editLayer: QgsVectorLayer = layer
        self.caps = self.editLayer.dataProvider().capabilities()
        self.mainWindow = mainWindow
        self.otherCanvas = otherCanvas
        self.reset()

    def reset(self):
        self.is_start = False  # 是否开始绘图
        self.start_point = None  # 起点
        self.end_point = None  # 终点
        self.rubberBand.reset(True)

    def canvasPressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if not self.is_start:
                # 设置起点
                self.start_point = event.mapPoint()
                self.is_start = True
            else:
                # 设置终点
                self.end_point = event.mapPoint()
                self.p = self.line()
                if self.p is not None:
                    if self.p.isGeosValid():
                        self.addFeature()
                    else:
                        QMessageBox.about(self.mainWindow, '错误', "线要素拓扑逻辑错误")
                self.reset()
        elif event.button() == Qt.RightButton:
            # 右键取消绘制
            self.reset()

    def addFeature(self):
        if self.caps & QgsVectorDataProvider.AddFeatures:
            feat = QgsFeature(self.editLayer.fields())
            feat.setGeometry(self.p)
            self.editLayer.addFeature(feat)
            self.canvas.refresh()
            if self.otherCanvas:
                self.otherCanvas.refresh()
            self.reset()

    def canvasMoveEvent(self, event):
        if not self.is_start:
            return
        # 绘制橡皮筋表示直线
        self.rubberBand.reset(QgsWkbTypes.LineGeometry)
        self.rubberBand.addPoint(self.start_point, False)
        self.rubberBand.addPoint(event.mapPoint(), True)
        self.rubberBand.show()

    def line(self):
        if not self.start_point or not self.end_point:
            return None
        # 确保返回一条直线
        return QgsGeometry.fromPolylineXY([QgsPointXY(self.start_point.x(), self.start_point.y()),
                                           QgsPointXY(self.end_point.x(), self.end_point.y())])

    def deactivate(self):
        super(LineMapTool_1, self).deactivate()
        self.deactivated.emit()
        self.reset()



class YuanMapTool(QgsMapToolEmitPoint):
    def __init__(self, canvas, layer, mainWindow, otherCanvas=None):
        super(YuanMapTool, self).__init__(canvas)
        self.canvas = canvas
        self.rubberBand = QgsRubberBand(self.canvas, QgsWkbTypes.LineGeometry)
        self.rubberBand.setColor(QColor(0, 255, 0, 150))
        self.rubberBand.setWidth(2)
        self.editLayer: QgsVectorLayer = layer
        self.caps = self.editLayer.dataProvider().capabilities()
        self.mainWindow = mainWindow
        self.otherCanvas = otherCanvas
        self.reset()

    def reset(self):
        self.is_start = False  # 是否开始绘图
        self.center_point = None  # 圆心
        self.radius_point = None  # 半径点
        self.is_drawing = False
        self.rubberBand.reset(True)

    def canvasPressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if not self.center_point:
                # 第一次点击，设置圆心
                self.center_point = event.mapPoint()
                self.is_start = True
                self.is_drawing = True
            else:
                # 第二次点击，设置半径点并完成圆绘制
                self.radius_point = event.mapPoint()
                self.p = self.create_circle()
                if self.p is not None:
                    if self.p.isGeosValid():
                        self.addFeature()
                    else:
                        QMessageBox.about(self.mainWindow, '错误', "圆形拓扑逻辑错误")
                    self.reset()
        elif event.button() == Qt.RightButton:
            # 右键取消绘制
            self.reset()

    def addFeature(self):
        if self.caps & QgsVectorDataProvider.AddFeatures:
            feat = QgsFeature(self.editLayer.fields())
            feat.setGeometry(self.p)
            self.editLayer.addFeature(feat)
            self.canvas.refresh()
            if self.otherCanvas:
                self.otherCanvas.refresh()
            self.reset()

    def canvasMoveEvent(self, event):
        if not self.is_drawing or not self.center_point:
            return
        # 动态更新圆形的显示
        self.radius_point = event.mapPoint()
        self.rubberBand.reset(QgsWkbTypes.LineGeometry)
        circle = self.create_circle_geometry(self.center_point, self.radius_point)
        if circle:
            for point in circle:
                self.rubberBand.addPoint(point, False)
            self.rubberBand.addPoint(circle[0], True)  # 闭合圆
        self.rubberBand.show()

    def create_circle(self):
        if not self.center_point or not self.radius_point:
            return None
        points = self.create_circle_geometry(self.center_point, self.radius_point)
        if points:
            return QgsGeometry.fromPolylineXY(points)
        return None

    def create_circle_geometry(self, center, radius_point, segments=36):
        """
        根据中心点和半径点生成圆的几何
        :param center: QgsPointXY 圆心
        :param radius_point: QgsPointXY 半径上的点
        :param segments: 圆分割的段数，默认36
        :return: 包含圆几何点的列表
        """
        radius = center.distance(radius_point)  # 计算半径
        if radius <= 0:
            return None
        points = []
        for i in range(segments):
            angle = (2 * math.pi / segments) * i
            x = center.x() + radius * math.cos(angle)
            y = center.y() + radius * math.sin(angle)
            points.append(QgsPointXY(x, y))
        points.append(points[0])
        return points

    def deactivate(self):
        super(YuanMapTool, self).deactivate()
        self.deactivated.emit()
        self.reset()


class DuoMianTiMapTool(QgsMapToolEmitPoint):
    def __init__(self, canvas, layer, mainWindow, otherCanvas=None):
        super(DuoMianTiMapTool, self).__init__(canvas)
        self.canvas = canvas
        self.rubberBand = QgsRubberBand(self.canvas, QgsWkbTypes.LineGeometry)
        self.rubberBand.setColor(QColor(0, 255, 0, 150))
        self.rubberBand.setWidth(2)
        self.editLayer: QgsVectorLayer = layer
        self.caps = self.editLayer.dataProvider().capabilities()
        self.mainWindow = mainWindow
        self.otherCanvas = otherCanvas
        self.reset()

    def reset(self):
        self.is_start = False  # 是否开始绘图
        self.center_point = None  # 圆心
        self.radius_point = None  # 半径点
        self.is_drawing = False
        self.rubberBand.reset(True)
        self.bian = 0
        self.angle = 0

    def canvasPressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if not self.center_point:
                # 第一次点击，设置圆心
                self.center_point = event.mapPoint()
                self.is_start = True
                self.is_drawing = True
                self.bian, ok = QInputDialog.getInt(None, "多边形", "请输入边的数目:", 1, 0, 1000000, 1)
                print(type(self.bian))
                self.angle, ok = QInputDialog.getInt(None, "多边形", "请输入偏转角度:", 1, 0, 1000000, 1)
            else:
                # 第二次点击，设置半径点并完成圆绘制
                self.radius_point = event.mapPoint()
                self.p = self.create_circle()
                if self.p is not None:
                    if self.p.isGeosValid():
                        self.addFeature()
                    else:
                        QMessageBox.about(self.mainWindow, '错误', "圆形拓扑逻辑错误")
                    self.reset()
        elif event.button() == Qt.RightButton:
            # 右键取消绘制
            self.reset()

    def addFeature(self):
        if self.caps & QgsVectorDataProvider.AddFeatures:
            feat = QgsFeature(self.editLayer.fields())
            feat.setGeometry(self.p)
            self.editLayer.addFeature(feat)
            self.canvas.refresh()
            if self.otherCanvas:
                self.otherCanvas.refresh()
            self.reset()

    def canvasMoveEvent(self, event):
        if not self.is_drawing or not self.center_point:
            return
        # 动态更新圆形的显示
        self.radius_point = event.mapPoint()
        self.rubberBand.reset(QgsWkbTypes.LineGeometry)
        circle = self.create_circle_geometry(self.center_point, self.radius_point, self.bian,self.angle)
        if circle:
            for point in circle:
                self.rubberBand.addPoint(point, False)
            self.rubberBand.addPoint(circle[0], True)  # 闭合圆
        self.rubberBand.show()

    def create_circle(self):
        if not self.center_point or not self.radius_point:
            return None
        points = self.create_circle_geometry(self.center_point, self.radius_point, self.bian,self.angle)
        if points:
            return QgsGeometry.fromPolylineXY(points)
        return None

    def create_circle_geometry(self, center, radius_point, segments=36,angle=0):
        """
        根据中心点和半径点生成圆的几何
        :param center: QgsPointXY 圆心
        :param radius_point: QgsPointXY 半径上的点
        :param segments: 圆分割的段数，默认36
        :return: 包含圆几何点的列表
        """
        radius = center.distance(radius_point)  # 计算半径
        if radius <= 0:
            return None
        angle_radians = math.radians(angle)
        points = []
        for i in range(segments):
            angle = (2 * math.pi / segments) * i +angle_radians
            x = center.x() + radius * math.cos(angle)
            y = center.y() + radius * math.sin(angle)
            points.append(QgsPointXY(x, y))
        points.append(points[0])
        return points

    def deactivate(self):
        super(YuanMapTool, self).deactivate()
        self.deactivated.emit()
        self.reset()