import sys
import os
import traceback
import time
from qgis.core import QgsProject, QgsLayerTreeModel, QgsCoordinateReferenceSystem, QgsMapSettings, QgsMapLayer, \
    QgsVectorLayer, QgsMapLayerType, QgsField,QgsVectorFileWriter,QgsFeature,QgsPointXY,QgsGeometry,QgsFields,QgsWkbTypes,QgsSpatialIndex
from qgis.gui import QgsLayerTreeView, QgsMapCanvas, QgsLayerTreeMapCanvasBridge, QgsMapToolIdentifyFeature,QgsMapToolPan
from PyQt5.QtCore import QUrl, QSize, QMimeData, QUrl, Qt,QVariant,QMetaType
from ui.myWindow import Ui_MainWindow
from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QHBoxLayout, QFileDialog, QMessageBox, QStatusBar, QLabel, \
    QComboBox,QInputDialog
from qgisUtils import addMapLayer, readVectorFile, readRasterFile, menuProvider, readS57File,list_layers_in_s57,PolygonMapTool,PointMapTool,LineMapTool,\
    generate_neighbors,reconstruct_path,add_path_to_map,smooth_path_with_bspline,check_segment_intersects_with_restricted_area,has_forced_neighbors,a_star_search
PROJECT = QgsProject.instance()
#12.18.13:51更改,修改A*起点和终点读取
# 完整图层
s57_layer_sheet = [
"ACHARE",
"ACHARE",
"BCNSPP",
"BRIDGE",
"BRIDGE",
"BUISGL",
"BUAARE",
"BOYCAR",
"BOYISD",
"BOYLAT",
"BOYSPP",
"CBLSUB ",
"CAUSWY",
"CTNARE",
"COALNE",
"DEPARE",
"DEPCNT",
"DMPGRD",
"DYKCON",
"FSHFAC",
"FOGSIG",
"HRBARE",
"LAKARE",
"LNDARE",
"LNDELV",
"LNDELV",
"LNDRGN",
"LNDRGN",
"LNDMRK",
"LIGHTS",
"MAGVAR",
"MARCUL",
"OBSTRN",
"OBSTRN",
"OFSPLF",
"PILBOP",
"PRCARE",
"RTPBCN",
"RDOCAL",
"RDOSTA",
"RAILWY",
"RESARE",
"RIVERS",
"ROADWY",
"SEAARE",
"SEAARE",
"SBDARE",
"SBDARE",
"SLCONS",
"SLCONS",
"SOUNDG",
"SWPARE",
"TS_PAD",
"TOPMAR",
"TSSBND",
"TSSLPT",
"TSEZNE",
"TUNNEL",
"UWTROC",
"WATTUR",
"WRECKS",
"TS_FEB",
"M_COVR",
"M_NSYS",
"M_QUAL",
"DSID"


]
s57_layer_sheet.reverse()

# s57_layer_sheet = ['LIGHTS','LNDARE','DEPARE',"ADMARE","RESARE"]
# 部分图层
s57_layer_sheet_1 = ['LNDARE',"RESARE"]

# s57_layer_sheet = ["DSID","Point","Line","Area","Meta"]


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setupUi(self)
        # 1 修改标题
        self.setWindowTitle("海图")
        # 2 初始化图层树
        vl = QVBoxLayout(self.dockWidgetContents)
        self.layerTreeView = QgsLayerTreeView(self)
        vl.addWidget(self.layerTreeView)
        # 3 初始化地图画布
        self.mapCanvas: QgsMapCanvas = QgsMapCanvas(self)
        self.hl = QHBoxLayout(self.frame)
        self.hl.setContentsMargins(0, 0, 0, 0)  # 设置周围间距
        self.hl.addWidget(self.mapCanvas)

        # 1. 创建地图画布的漫游工具对象
        self.mapCanvasPanTool = QgsMapToolPan(self.mapCanvas)
        # 2. 当需要地图画布漫游的时候，将 mapCavans 的 mapTool 设置为漫游对象
        self.mapCanvas.setMapTool(self.mapCanvasPanTool)
        # 4 设置图层树风格
        self.model = QgsLayerTreeModel(PROJECT.layerTreeRoot(), self)
        self.model.setFlag(QgsLayerTreeModel.AllowNodeRename)  # 允许图层节点重命名
        self.model.setFlag(QgsLayerTreeModel.AllowNodeReorder)  # 允许图层拖拽排序
        self.model.setFlag(QgsLayerTreeModel.AllowNodeChangeVisibility)  # 允许改变图层节点可视性
        self.model.setFlag(QgsLayerTreeModel.ShowLegendAsTree)  # 展示图例
        self.model.setAutoCollapseLegendNodes(10)  # 当节点数大于等于10时自动折叠
        self.layerTreeView.setModel(self.model)
        # 4 建立图层树与地图画布的桥接
        self.layerTreeBridge = QgsLayerTreeMapCanvasBridge(PROJECT.layerTreeRoot(), self.mapCanvas, self)
        # 5 初始加载影像
        self.firstAdd = True
        # 6 允许拖拽文件
        self.setAcceptDrops(True)

        # 7 图层树右键菜单创建
        self.rightMenuProv = menuProvider(self)
        self.layerTreeView.setMenuProvider(self.rightMenuProv)

        # 8.0 提前给予基本CRS
        self.mapCanvas.setDestinationCrs(QgsCoordinateReferenceSystem("EPSG:4326"))

        # 8 状态栏控件
        self.statusBar = QStatusBar()
        self.statusBar.setStyleSheet('color: black; border: none')
        self.statusXY = QLabel('{:<40}'.format(''))  # x y 坐标状态
        self.statusBar.addWidget(self.statusXY, 1)

        self.statusScaleLabel = QLabel('比例尺')
        self.statusScaleComboBox = QComboBox(self)
        self.statusScaleComboBox.setFixedWidth(120)
        self.statusScaleComboBox.addItems(
            ["1:500", "1:1000", "1:2500", "1:5000", "1:10000", "1:25000", "1:100000", "1:500000", "1:1000000"])
        self.statusScaleComboBox.setEditable(True)
        self.statusBar.addWidget(self.statusScaleLabel)
        self.statusBar.addWidget(self.statusScaleComboBox)

        self.statusCrsLabel = QLabel(
            f"坐标系: {self.mapCanvas.mapSettings().destinationCrs().description()}-{self.mapCanvas.mapSettings().destinationCrs().authid()}")
        self.statusBar.addWidget(self.statusCrsLabel)

        self.setStatusBar(self.statusBar)

        # 9 error catch
        self.old_hook = sys.excepthook
        sys.excepthook = self.catch_exceptions

        # A 按钮、菜单栏功能
        self.connectFunc()

        # B 初始设置控件
        self.actionEditShp.setEnabled(False)
        self.editTempLayer: QgsVectorLayer = None  # 初始编辑图层为None

    def connectFunc(self):

        # 每次移动鼠标，坐标和比例尺变化
        self.mapCanvas.xyCoordinates.connect(self.showXY)
        self.mapCanvas.scaleChanged.connect(self.showScale)
        self.mapCanvas.destinationCrsChanged.connect(self.showCrs)
        self.statusScaleComboBox.editTextChanged.connect(self.changeScaleForString)

        # action open
        self.actionOpenRaster.triggered.connect(self.actionOpenRasterTriggered)
        self.actionOpenShp.triggered.connect(self.actionOpenShpTriggered)
        self.actionOpenS57.triggered.connect(self.actionOpenS57Triggered)
        self.actionCreateLayer.triggered.connect(self.actionCreateLayerTriggered)
        self.actionConvert.triggered.connect(self.actionConvertTriggered)
        self.actionCheckLine.triggered.connect(self.check_line_intersects_with_areas)

        # action edit
        self.actionSelectFeature.triggered.connect(self.actionSelectFeatureTriggered)
        self.actionEditShp.triggered.connect(self.actionEditShpTriggered)
        self.actionPolygon.triggered.connect(self.actionPolygonTriggered)
        self.actionPoint.triggered.connect(self.actionPointTriggered)
        self.actionLine.triggered.connect(self.actionLineTriggered)

        # 单击、双击图层 触发事件
        self.layerTreeView.clicked.connect(self.layerClicked)
        # 删除
        self.actionDeleteFeature.triggered.connect(self.actionDeleteFeatureTriggered)
        self.actionPLAN.triggered.connect(self.actionPLANTriggered)


    def actionDeleteFeatureTriggered(self):
        if self.editTempLayer == None:
            QMessageBox.information(self, '警告', '您没有编辑中矢量')
            return
        if len(self.editTempLayer.selectedFeatureIds()) == 0:
            QMessageBox.information(self, '删除选中矢量', '您没有选择任何矢量')
        else:
            self.editTempLayer.deleteSelectedFeatures()

    # action Polygon
    def actionPolygonTriggered(self):
        if self.editTempLayer == None:
            QMessageBox.information(self, '警告', '您没有编辑中矢量')
            return
        if self.mapCanvas.mapTool():
            self.mapCanvas.mapTool().deactivate()
        self.polygonTool = PolygonMapTool(self.mapCanvas, self.editTempLayer, self)
        self.mapCanvas.setMapTool(self.polygonTool)

    def actionPointTriggered(self):
        if self.editTempLayer == None:
            QMessageBox.information(self, '警告', '您没有编辑中矢量')
            return
        if self.mapCanvas.mapTool():
            self.mapCanvas.mapTool().deactivate()
        self.pointTool = PointMapTool(self.mapCanvas, self.editTempLayer, self)
        self.mapCanvas.setMapTool(self.pointTool)

    def actionLineTriggered(self):
        if self.editTempLayer == None:
            QMessageBox.information(self, '警告', '您没有编辑中矢量')
            return
        if self.mapCanvas.mapTool():
            self.mapCanvas.mapTool().deactivate()
        self.lineTool = LineMapTool(self.mapCanvas, self.editTempLayer, self)
        self.mapCanvas.setMapTool(self.lineTool)

    def layerClicked(self):
        curLayer: QgsMapLayer = self.layerTreeView.currentLayer()
        if curLayer and type(curLayer) == QgsVectorLayer and not curLayer.readOnly():
            self.actionEditShp.setEnabled(True)
        else:
            self.actionEditShp.setEnabled(False)

    def showXY(self, point):
        x = point.x()
        y = point.y()
        self.statusXY.setText(f'{x:.6f}, {y:.6f}')

    def showScale(self, scale):
        self.statusScaleComboBox.setEditText(f"1:{int(scale)}")

    def showCrs(self):
        mapSetting: QgsMapSettings = self.mapCanvas.mapSettings()
        self.statusCrsLabel.setText(
            f"坐标系: {mapSetting.destinationCrs().description()}-{mapSetting.destinationCrs().authid()}")

    def changeScaleForString(self, str):
        try:
            left, right = str.split(":")[0], str.split(":")[-1]
            if int(left) == 1 and int(right) > 0 and int(right) != int(self.mapCanvas.scale()):
                self.mapCanvas.zoomScale(int(right))
                self.mapCanvas.zoomWithCenter()
        except:
            print(traceback.format_stack())

    def dragEnterEvent(self, fileData):
        if fileData.mimeData().hasUrls():
            fileData.accept()
        else:
            fileData.ignore()

    # 拖拽文件事件
    def dropEvent(self, fileData):
        mimeData: QMimeData = fileData.mimeData()
        filePathList = [u.path()[1:] for u in mimeData.urls()]
        for filePath in filePathList:
            filePath: str = filePath.replace("/", "//")
            if filePath.split(".")[-1] in ["tif", "TIF", "tiff", "TIFF", "GTIFF", "png", "jpg", "pdf"]:
                self.addRasterLayer(filePath)
            elif filePath.split(".")[-1] in ["shp", "SHP", "gpkg", "geojson", "kml"]:
                self.addVectorLayer(filePath)
            elif filePath.split(".")[-1] in ["000"]:
                self.addS57Layers(filePath, s57_layer_sheet_1)
            elif filePath == "":
                pass
            else:
                QMessageBox.about(self, '警告', f'{filePath}为不支持的文件类型，目前支持栅格影像和shp矢量')

    def catch_exceptions(self, ty, value, trace):
        """
            捕获异常，并弹窗显示
        :param ty: 异常的类型
        :param value: 异常的对象
        :param traceback: 异常的traceback
        """
        traceback_format = traceback.format_exception(ty, value, trace)
        traceback_string = "".join(traceback_format)
        QMessageBox.about(self, 'error', traceback_string)
        self.old_hook(ty, value, trace)

    def actionOpenRasterTriggered(self):
        data_file, ext = QFileDialog.getOpenFileName(self, '打开', '',
                                                     'GeoTiff(*.tif;*tiff;*TIF;*TIFF);;All Files(*);;JPEG(*.jpg;*.jpeg;*.JPG;*.JPEG);;*.png;;*.pdf')
        if data_file:
            self.addRasterLayer(data_file)

    def actionOpenShpTriggered(self):
        data_file, ext = QFileDialog.getOpenFileName(self, '打开', '',
                                                     "ShapeFile(*.shp);;All Files(*);;Other(*.gpkg;*.geojson;*.kml)")
        if data_file:
            self.addVectorLayer(data_file)

    def actionOpenS57Triggered(self):
        data_file, ext = QFileDialog.getOpenFileName(self, '打开', '',
                                                     "S-57 map (*.000);;All Files (*)")
        if data_file:

            item, ok = QInputDialog.getItem(self, "选择打开方式", "请选择一个S57浏览方式:", ["all","section","3"], 0, False)
            if item=="all":
                print("查看全部图层")
                self.addS57Layers(data_file, s57_layer_sheet)
            if item=="section":
                self.addS57Layers(data_file, s57_layer_sheet_1)

    def actionCreateLayerTriggered(self):
        # 创建一个空白的点图层 (记得修改为你的CRS)
        layer = QgsVectorLayer('Point?crs=EPSG:4326', 'LayerName', 'memory')

        # 添加字段
        pr = layer.dataProvider()
        pr.addAttributes([
            QgsField("x", QVariant.String),
            QgsField("y", QVariant.String),
            QgsField("id", QVariant.String),
        ])
        layer.updateFields()

        # 创建一个示例点要素
        feature = QgsFeature()
        point = QgsPointXY(120.0, 30.0)  # 设置点的经纬度
        feature.setGeometry(QgsGeometry.fromPointXY(point))
        feature.setAttributes([120, 30, "Standard"])
        pr.addFeature(feature)

        # 保存为 .shp 文件 (确保路径有效)
        file_path, ext = QFileDialog.getSaveFileName(self, '保存文件', '',
                                                     "ShapeFile(*.shp);;GeoPackage(*.gpkg);;GeoJSON(*.geojson);;KML(*.kml);;All Files(*)")
        # file_path = r'D:\gongju\pycharm\wenjian\HaiTu\testdata\point_layer.shp'
        if os.path.exists(file_path):
            os.remove(file_path)  # 如果文件已存在，先删除它
        QgsVectorFileWriter.writeAsVectorFormat(layer, file_path, 'utf-8', layer.crs(), 'ESRI Shapefile')

        print(f"已将图层保存为: {file_path}")
        if file_path:
            self.addVectorLayer(file_path)


    def actionPLANTriggered(self):

        point_layer = self.layerTreeView.currentLayer()
        provider = point_layer.dataProvider()
        all_features = [feat for feat in provider.getFeatures()]
        # 过滤掉 id 属性为 NULL 的点 (假设 id 在第3列索引为2)
        # 过滤掉 id 属性为 NULL 的点 (假设 id 在第3列索引为2)
        valid_features = [feat for feat in all_features if
                          not feat.attribute(2) is None and not feat.attribute(2) == "Standard"]
        # 按 id 属性排序点要素 (假设 id 在第3列索引为2)
        sorted_features = sorted(valid_features, key=lambda f: f.attribute(2))
        print(sorted_features)
        for i in range(len(sorted_features)-1):
            start_point = sorted_features[i].geometry().asPoint()
            end_point = sorted_features[i+1].geometry().asPoint()

            if a_star_search(self,start_point,end_point,0)==None:
                a_star_search(self, start_point, end_point,1)


    def return_path(self,node):
        """从目标节点向回追踪路径"""
        path = []
        while node:
            path.append(node['point'])
            node = node.get('parent', None)
        return path[::-1]  # 返回从起点到终点的路径

    def actionConvertTriggered(self):
        """ 从点图层生成线图层，连线顺序根据 id 排序 """
        # 获取点图层的数据提供者
        # 获取当前选中的图层
        point_layer = self.layerTreeView.currentLayer()  # 获取当前活动图层

        provider = point_layer.dataProvider()

        # 获取所有点要素
        all_features = [feat for feat in provider.getFeatures()]
        # 过滤掉 id 属性为 NULL 的点 (假设 id 在第3列索引为2)
        # 过滤掉 id 属性为 NULL 的点 (假设 id 在第3列索引为2)
        valid_features = [feat for feat in all_features if
                          not feat.attribute(2) is None and not feat.attribute(2) == "Standard"]
        # valid_features = [feat for feat in all_features if feat.attribute(2) is not None]

        # 按 id 属性排序点要素 (假设 id 在第3列索引为2)
        sorted_features = sorted(valid_features, key=lambda f: f.attribute(2))  # 这里 2 是 id 列的索引

        # 创建一个空白的线图层
        line_layer = QgsVectorLayer("LineString?crs=EPSG:4326", "线图层", "memory")
        line_provider = line_layer.dataProvider()

        # 获取点的几何信息并创建线
        points = [feat.geometry().asPoint() for feat in sorted_features]
        if len(points) < 2:
            QMessageBox.about(self, '警告', f'点数量不足以创建线')
            return

        # 创建线要素
        line = QgsFeature()
        line_geom = QgsGeometry.fromPolylineXY(points)
        line.setGeometry(line_geom)

        # 将线要素添加到线图层
        line_provider.addFeature(line)
        line_layer.updateExtents()
        # 添加前判断是否冲突

        self.check_line_intersects_with_areas()
        # 将线图层添加到地图
        QgsProject.instance().addMapLayer(line_layer)


    def check_line_intersects_with_areas(self):
        """检查线图层和面图层是否相交"""

        # 获取当前活动图层（线图层）
        t = 0 # 存储是否相交

        line_layer = self.layerTreeView.currentLayer()  # 假设这是线图层

        # 获取面图层（可以从已有的面图层选择或其他方式）
        # 假设我们选择了另一个面图层作为目标图层
        # selected_layers = self.layerTreeView.selectedLayers()  # 获取所有选中的图层
        all_layers = [layer for layer in QgsProject.instance().mapLayers().values()]

        area_layer = all_layers
        print(area_layer)
        # 遍历选中的图层，找出面图层

        for layer in all_layers:
            print(layer.crs)
            print(layer.dataProvider)
            print(layer.geometryType())
            if layer.geometryType() == QgsWkbTypes.PolygonGeometry or layer.geometryType() == 0:
                area_layer = layer
                print(area_layer)
                # break  # 假设只选择一个面图层

                if not area_layer:
                    QMessageBox.warning(self, "警告", "未选择面图层!")
                    return

                # 确保线图层和面图层不是同一个图层
                if line_layer == area_layer:
                    QMessageBox.warning(self, "警告", "线图层和面图层不能是同一图层!")
                    return

                # 遍历线图层中的每个线要素
                for line_feature in line_layer.getFeatures():
                    line_geom = line_feature.geometry()

                    # 遍历面图层中的每个面要素
                    for area_feature in area_layer.getFeatures():
                        area_geom = area_feature.geometry()

                        # 检查线与面是否相交
                        if line_geom.intersects(area_geom):
                            QMessageBox.about(self, '提示', f"线 {line_feature.id()} 与 面 {area_feature.id()} 相交，错误航线")
                            print(f"线 {line_feature.id()} 与 面 {area_feature.id()} 相交")
                            t = 1

        if t == 0:
            print("没有相交")
        return t



    # 添加栅格图层
    def addRasterLayer(self, rasterFilePath):
        rasterLayer = readRasterFile(rasterFilePath)
        if self.firstAdd:
            addMapLayer(rasterLayer, self.mapCanvas, True)
            self.firstAdd = False
        else:
            addMapLayer(rasterLayer, self.mapCanvas)

    # 添加矢量图层
    def addVectorLayer(self, vectorFilePath):
        vectorLayer = readVectorFile(vectorFilePath)
        if self.firstAdd:
            addMapLayer(vectorLayer, self.mapCanvas, True)
            self.firstAdd = False
        else:
            addMapLayer(vectorLayer, self.mapCanvas)

    def addS57Layer(self, S57FilePath, layer_name):
        S57Layer = readS57File(S57FilePath, layer_name)
        if self.firstAdd:
            addMapLayer(S57Layer, self.mapCanvas, True)
            self.firstAdd = False
        else:
            addMapLayer(S57Layer, self.mapCanvas)

    def addS57Layers(self, vectorFilePath, layers):
        print("开始添加图层")
        valid_layers = list_layers_in_s57(vectorFilePath)
        # valid_layers = s57_layer_sheet
        for layer in layers:
            if layer in valid_layers:
                self.addS57Layer(vectorFilePath, layer)


    # action Edit
    def actionEditShpTriggered(self):
        if self.actionEditShp.isChecked():
            self.editTempLayer: QgsVectorLayer = self.layerTreeView.currentLayer()
            self.editTempLayer.startEditing()
        else:
            if self.editTempLayer.isModified():
                saveShpEdit = QMessageBox.question(self, '保存编辑', "确定要将编辑内容保存到内存吗？",
                                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if saveShpEdit == QMessageBox.Yes:
                    self.editTempLayer.commitChanges()
                else:
                    self.editTempLayer.rollBack()
            else:
                self.editTempLayer.commitChanges()

            self.mapCanvas.refresh()
            self.editTempLayer = None

    def selectToolIdentified(self, feature):
        print(feature.id())
        layerTemp: QgsVectorLayer = self.layerTreeView.currentLayer()
        if layerTemp.type() == QgsMapLayerType.VectorLayer:
            if feature.id() in layerTemp.selectedFeatureIds():
                layerTemp.deselect(feature.id())
            else:
                layerTemp.removeSelection()
                layerTemp.select(feature.id())

    def actionSelectFeatureTriggered(self):
        if self.actionSelectFeature.isChecked():
            if self.mapCanvas.mapTool():
                self.mapCanvas.unsetMapTool(self.mapCanvas.mapTool())
            self.selectTool = QgsMapToolIdentifyFeature(self.mapCanvas)
            self.selectTool.setCursor(Qt.ArrowCursor)
            self.selectTool.featureIdentified.connect(self.selectToolIdentified)
            layers = self.mapCanvas.layers()
            if layers:
                self.selectTool.setLayer(self.layerTreeView.currentLayer())
            self.mapCanvas.setMapTool(self.selectTool)
        else:
            if self.mapCanvas.mapTool():
                self.mapCanvas.unsetMapTool(self.mapCanvas.mapTool())