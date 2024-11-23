import sys
import os
import traceback
from qgis.core import QgsProject, QgsLayerTreeModel, QgsCoordinateReferenceSystem, QgsMapSettings, QgsMapLayer, \
    QgsVectorLayer, QgsMapLayerType, QgsField,QgsVectorFileWriter,QgsFeature,QgsPointXY,QgsGeometry,QgsFields,QgsWkbTypes
from qgis.gui import QgsLayerTreeView, QgsMapCanvas, QgsLayerTreeMapCanvasBridge, QgsMapToolIdentifyFeature,QgsMapToolPan
from PyQt5.QtCore import QUrl, QSize, QMimeData, QUrl, Qt,QVariant,QMetaType
from ui.myWindow import Ui_MainWindow
from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QHBoxLayout, QFileDialog, QMessageBox, QStatusBar, QLabel, \
    QComboBox
from qgisUtils import addMapLayer, readVectorFile, readRasterFile, menuProvider, readS57File,list_layers_in_s57,PolygonMapTool,PointMapTool,LineMapTool

PROJECT = QgsProject.instance()

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
"M_QUAL"


]
s57_layer_sheet.reverse()

s57_layer_sheet = ['LIGHTS','LNDARE','DEPARE',"ADMARE","RESARE"]


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
                self.addS57Layers(filePath, s57_layer_sheet)
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
            self.addS57Layers(data_file, s57_layer_sheet)

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
        feature.setAttributes([1, "Sample Point"])
        pr.addFeature(feature)

        # 保存为 .shp 文件 (确保路径有效)
        file_path = r'D:\gongju\pycharm\wenjian\HaiTu\testdata\point_layer.shp'
        if os.path.exists(file_path):
            os.remove(file_path)  # 如果文件已存在，先删除它
        QgsVectorFileWriter.writeAsVectorFormat(layer, file_path, 'utf-8', layer.crs(), 'ESRI Shapefile')

        print(f"已将图层保存为: {file_path}")
        if file_path:
            self.addVectorLayer(file_path)

    def actionConvertTriggered(self):
        """ 从点图层生成线图层，连线顺序根据 id 排序 """
        # 获取点图层的数据提供者
        # 获取当前选中的图层
        point_layer = self.layerTreeView.currentLayer()  # 获取当前活动图层

        provider = point_layer.dataProvider()

        # 获取所有点要素
        all_features = [feat for feat in provider.getFeatures()]
        # 过滤掉 id 属性为 NULL 的点 (假设 id 在第3列索引为2)
        valid_features = [feat for feat in all_features if feat.attribute(2) is not None]

        # 按 id 属性排序点要素 (假设 id 在第3列索引为2)
        sorted_features = sorted(valid_features, key=lambda f: f.attribute(2))  # 这里 2 是 id 列的索引

        # 创建一个空白的线图层
        line_layer = QgsVectorLayer("LineString?crs=EPSG:4326", "线图层", "memory")
        line_provider = line_layer.dataProvider()

        # 获取点的几何信息并创建线
        points = [feat.geometry().asPoint() for feat in sorted_features]
        if len(points) < 2:
            print("点数不足以创建线段")
            return

        # 创建线要素
        line = QgsFeature()
        line_geom = QgsGeometry.fromPolylineXY(points)
        line.setGeometry(line_geom)

        # 将线要素添加到线图层
        line_provider.addFeature(line)
        line_layer.updateExtents()

        # 将线图层添加到地图
        QgsProject.instance().addMapLayer(line_layer)


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
        valid_layers = list_layers_in_s57(vectorFilePath)
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