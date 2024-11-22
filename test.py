import os
from qgis.core import (
    QgsVectorLayer,
    QgsField,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsVectorFileWriter,
    QgsWkbTypes,
    QgsCoordinateReferenceSystem,
)
from PyQt5.QtCore import QVariant

# 初始化 QGIS 应用程序
from qgis.gui import QgsMapCanvas
from qgis.PyQt.QtWidgets import QApplication

app = QApplication([])

# 创建一个空白的点图层 (记得修改为你的CRS)
layer = QgsVectorLayer('Point?crs=EPSG:4326', 'LayerName', 'memory')

# 添加字段
pr = layer.dataProvider()
pr.addAttributes([
    QgsField("ID", QVariant.Int),
    QgsField("Name", QVariant.String)
])
layer.updateFields()

# 创建一个示例点要素
feature = QgsFeature()
point = QgsPointXY(120.0, 30.0)  # 设置点的经纬度
feature.setGeometry(QgsGeometry.fromPointXY(point))
feature.setAttributes([1, "Sample Point"])
pr.addFeature(feature)

# 保存为 .shp 文件 (确保路径有效)
file_path = r'D:\gongju\pycharm\wenjian\HaiTu\testdata\point_layer.shp'
if os.path.exists(file_path):
    os.remove(file_path)  # 如果文件已存在，先删除它
QgsVectorFileWriter.writeAsVectorFormat(layer, file_path, 'utf-8', layer.crs(), 'ESRI Shapefile')

print(f"已将图层保存为: {file_path}")

# 退出应用程序
app.exit()
