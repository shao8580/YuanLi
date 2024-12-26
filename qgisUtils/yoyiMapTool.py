# -*- coding: utf-8 -*-
# @Author  : yoyi
# @Time    : 2024/12/20 15:31

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
from math import sin, cos, radians
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
                self.drawLinesInsidePolygon()

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

    def drawLinesInsidePolygon_1(self, line_layer_name="Generated Lines", spacing=0.1):
        if not self.p:
            QMessageBox.warning(self.mainWindow, "警告", "请先绘制多边形")
            return

        polygon_geom = self.p
        bounding_box = polygon_geom.boundingBox()
        min_x, max_x = bounding_box.xMinimum(), bounding_box.xMaximum()
        min_y, max_y = bounding_box.yMinimum(), bounding_box.yMaximum()

        start_y = min_y
        crs = self.editLayer.crs().authid()
        line_layer = QgsVectorLayer(f"LineString?crs={crs}", line_layer_name, "memory")
        line_provider = line_layer.dataProvider()

        previous_end_point = None  # 记录上一条线的终点

        while start_y <= max_y:
            # 根据当前行的奇偶性决定方向
            if int((start_y - min_y) / spacing) % 2 == 0:
                # 偶数行，从左到右
                line_points = [previous_end_point, QgsPointXY(max_x, start_y)] if previous_end_point else [
                    QgsPointXY(min_x, start_y), QgsPointXY(max_x, start_y)]
            else:
                # 奇数行，从右到左
                line_points = [previous_end_point, QgsPointXY(min_x, start_y)] if previous_end_point else [
                    QgsPointXY(max_x, start_y), QgsPointXY(min_x, start_y)]

            # 创建线几何
            line_geom = QgsGeometry.fromPolylineXY(line_points)
            clipped_line = line_geom.intersection(polygon_geom)  # 裁剪多边形内部部分

            if not clipped_line.isEmpty():
                # 处理裁剪结果可能为多段线的情况
                if clipped_line.type() == QgsWkbTypes.MultiLineString:
                    for part in clipped_line.asGeometryCollection():
                        feature = QgsFeature()
                        feature.setGeometry(part)
                        line_provider.addFeature(feature)
                else:
                    feature = QgsFeature()
                    feature.setGeometry(clipped_line)
                    line_provider.addFeature(feature)

                # 更新终点为当前线段的终点
                previous_end_point = line_points[-1]

            start_y += spacing  # 更新到下一行

        line_layer.updateExtents()
        QgsProject.instance().addMapLayer(line_layer)
        QMessageBox.information(self.mainWindow, "完成", f"成功生成线图层 {line_layer_name}")

    from PyQt5.QtCore import Qt
    from qgis.core import QgsPointXY, QgsGeometry, QgsFeature, QgsVectorLayer, QgsProject
    from PyQt5.QtWidgets import QMessageBox

    from PyQt5.QtWidgets import QMessageBox
    from qgis.core import QgsPointXY, QgsGeometry, QgsFeature, QgsVectorLayer, QgsProject
    from PyQt5.QtCore import Qt

    from PyQt5.QtWidgets import QMessageBox
    from qgis.core import QgsPointXY, QgsGeometry, QgsFeature, QgsVectorLayer, QgsProject
    from PyQt5.QtCore import Qt

    from PyQt5.QtWidgets import QMessageBox
    from qgis.core import QgsPointXY, QgsGeometry, QgsFeature, QgsVectorLayer, QgsProject
    from PyQt5.QtCore import Qt

    def drawLinesInsidePolygon(self, line_layer_name="Generated Lines", spacing=0.1):
        """
        生成一条连续的蛇形折返路径，遍历多边形区域，确保路径在边界内并保持连续。
        :param line_layer_name: str，生成的线图层名称。
        :param spacing: float，路径之间的间距。
        """
        if not self.p:  # 检查当前是否已经绘制了多边形
            QMessageBox.warning(self.mainWindow, "警告", "请先绘制多边形")
            return

        # 获取多边形的几何信息
        polygon_geom = self.p
        bounding_box = polygon_geom.boundingBox()  # 获取多边形的外包矩形

        min_x, max_x = bounding_box.xMinimum(), bounding_box.xMaximum()
        min_y, max_y = bounding_box.yMinimum(), bounding_box.yMaximum()

        # 初始化路径起点、方向和间距
        current_y = min_y
        direction = 1  # 1 表示向右，-1 表示向左

        # 存储生成的路径点
        path_points = []

        while current_y <= max_y:
            if direction == 1:  # 向右
                start_point = QgsPointXY(min_x, current_y)
                end_point = QgsPointXY(max_x, current_y)
            else:  # 向左
                start_point = QgsPointXY(max_x, current_y)
                end_point = QgsPointXY(min_x, current_y)

            # 创建当前路径段的几何
            line_geom = QgsGeometry.fromPolylineXY([start_point, end_point])

            # 检查路径段是否在多边形内
            if polygon_geom.contains(line_geom):
                path_points.extend([start_point, end_point])
            else:
                # 如果路径段不完全在多边形内，需要调整路径，确保只生成在多边形内的路径段
                clipped_line = line_geom.intersection(polygon_geom)
                if not clipped_line.isEmpty():
                    # 检查是否为折线，而非点
                    if clipped_line.isMultipart() or clipped_line.type() == QgsWkbTypes.LineGeometry:
                        points = clipped_line.asPolyline()
                        if len(points) > 1:
                            path_points.extend(points)
                    else:
                        print("Clipped geometry is not a line.")

            # 更新Y值，移动到下一条线的位置
            current_y += spacing
            # 改变方向，实现蛇形折返
            direction *= -1

        # 创建一个新的内存线图层
        crs = self.editLayer.crs().authid()  # 获取当前图层的坐标系
        line_layer = QgsVectorLayer(f"LineString?crs={crs}", line_layer_name, "memory")
        line_provider = line_layer.dataProvider()

        # 创建线要素
        if len(path_points) > 1:
            line_feature = QgsFeature()
            line_geom = QgsGeometry.fromPolylineXY(path_points)
            line_feature.setGeometry(line_geom)
            line_provider.addFeature(line_feature)

        line_layer.updateExtents()

        # 将新创建的线图层添加到地图中
        QgsProject.instance().addMapLayer(line_layer)

        QMessageBox.information(self.mainWindow, "完成", f"成功生成线图层 {line_layer_name}")

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
        super(DuoMianTiMapTool, self).deactivate()
        self.deactivated.emit()
        self.reset()
