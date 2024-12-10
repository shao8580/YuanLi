from qgis.core import  QgsMapLayer, QgsLineSymbol, QgsSingleSymbolRenderer, QgsFillSymbol, QgsRasterLayer,QgsVectorLayer,QgsProject,QgsRasterDataProvider,QgsVectorDataProvider,Qgis,QgsRectangle,QgsCoordinateReferenceSystem,QgsWkbTypes
from qgis.gui import QgsMapCanvas
import os
import os.path as osp
from qgisUtils.yoyiFile import getFileSize
from osgeo import ogr,gdal


PROJECT = QgsProject.instance()
qgisDataTypeDict = {
    0 : "UnknownDataType",
    1 : "Uint8",
    2 : "UInt16",
    3 : "Int16",
    4 : "UInt32",
    5 : "Int32",
    6 : "Float32",
    7 : "Float64",
    8 : "CInt16",
    9 : "CInt32",
    10 : "CFloat32",
    11 : "CFloat64",
    12 : "ARGB32",
    13 : "ARGB32_Premultiplied"
}

color_LUT = {
    "LNDARE": ("#BF8930", "solid"),
    "ADMARE": ("#5888CA", "f_diagonal"),
    # "ADMARE": ("#284C7E", "f_diagonal"),
    "RESARE": ("#FF0000", "solid"),
}

line_color_LUT = {
    "DEPCNT": ("#CA5888", "solid"),
}

s57_layer_sheet = [
    "ADMARE",
    "LNDARE",
    "RESARE",
    "DEPCNT",
]

def addMapLayer(layer:QgsMapLayer,mapCanvas:QgsMapCanvas,firstAddLayer=False):
    if layer.isValid():
        if firstAddLayer:
            mapCanvas.setDestinationCrs(layer.crs())
            mapCanvas.setExtent(layer.extent())

        while(PROJECT.mapLayersByName(layer.name())):
            layer.setName(layer.name()+"_1")

        PROJECT.addMapLayer(layer)
        layers = [layer] + [PROJECT.mapLayer(i) for i in PROJECT.mapLayers()]
        mapCanvas.setLayers(layers)
        mapCanvas.refresh()


def list_layers_in_s57(file_path):
    # 使用OGR打开文件
    print("获取图层名")
    ds = ogr.Open(file_path)
    if ds is None:
        return "Failed open S57"

    # 列出文件中的所有图层
    layer_names = []
    for i in range(ds.GetLayerCount()):
        layer = ds.GetLayerByIndex(i)
        if layer:
            layer_names.append(layer.GetName())

    return layer_names

'''
def addS57Layers(self, vectorFilePath, layers):
    valid_layers = list_layers_in_s57(vectorFilePath)
    for layer in layers:
        if layer in valid_layers:
            self.addS57Layer(vectorFilePath, layer)
'''
def readRasterFile(rasterFilePath):
    print("读取栅格图层中")
    rasterLayer = QgsRasterLayer(rasterFilePath,osp.basename(rasterFilePath))
    return rasterLayer

def readVectorFile(vectorFilePath):
    print("读取矢量图层中")
    vectorLayer = QgsVectorLayer(vectorFilePath,osp.basename(vectorFilePath),"ogr")
    return vectorLayer


def readS57File(vectorFilePath, layer_name):
    print("准备加载文件")
    assert vectorFilePath[-3:] == "000"
    print("开始加载文件")

    # 使用 ogr 驱动加载 S57 图层
    vectorLayer = QgsVectorLayer(
        f"{vectorFilePath}|layername={layer_name}",  # 使用正确的路径格式
        osp.basename(vectorFilePath[:-4]) + f"|{layer_name}",
        "ogr"
    )
    if not vectorLayer.isEditable():
        print("The layer is in read-only mode.")
    else:
        print("The layer is editable.")

    # 检查图层是否成功加载
    if vectorLayer.isValid():
        print(f"load layer {layer_name}")
    else:
        print(f"没有成功加载{layer_name}")


    # 如果加载成功，可以在此添加你的渲染器配置
    if layer_name in color_LUT:
        # 创建一个新的填充符号
        color, style = color_LUT[layer_name]
        fill_symbol = QgsFillSymbol.createSimple({'color': color, 'style': style})
        # 创建一个单一符号渲染器并赋予新的填充符号
        renderer = QgsSingleSymbolRenderer(fill_symbol)
        # 将新的渲染器应用于图层
        vectorLayer.setRenderer(renderer)

    if layer_name in line_color_LUT:
        color, style = line_color_LUT[layer_name]
        line_symbol = QgsLineSymbol.createSimple({'color': color, 'style': style})
        renderer = QgsSingleSymbolRenderer(line_symbol)
        vectorLayer.setRenderer(renderer)

    return vectorLayer


def getRasterLayerAttrs(rasterLayer:QgsRasterLayer):

    rdp: QgsRasterDataProvider = rasterLayer.dataProvider()
    crs: QgsCoordinateReferenceSystem = rasterLayer.crs()
    extent: QgsRectangle = rasterLayer.extent()
    resDict = {
        "name": rasterLayer.name(),
        "source": rasterLayer.source(),
        "memory": getFileSize(rasterLayer.source()),
        "extent": f"min:[{extent.xMinimum():.6f},{extent.yMinimum():.6f}]; max:[{extent.xMaximum():.6f},{extent.yMaximum():.6f}]",
        "width": f"{rasterLayer.width()}",
        "height": f"{rasterLayer.height()}",
        "dataType": qgisDataTypeDict[rdp.dataType(1)],
        "bands": f"{rasterLayer.bandCount()}",
        "crs": crs.description()
    }
    return resDict

def getVectorLayerAttrs(vectorLayer:QgsVectorLayer):
    vdp : QgsVectorDataProvider = vectorLayer.dataProvider()
    crs: QgsCoordinateReferenceSystem = vectorLayer.crs()
    extent: QgsRectangle = vectorLayer.extent()
    resDict = {
        "name" : vectorLayer.name(),
        "source" : vectorLayer.source(),
        "memory": getFileSize(vectorLayer.source()),
        "extent" : f"min:[{extent.xMinimum():.6f},{extent.yMinimum():.6f}]; max:[{extent.xMaximum():.6f},{extent.yMaximum():.6f}]",
        "geoType" : QgsWkbTypes.geometryDisplayString(vectorLayer.geometryType()),
        "featureNum" : f"{vectorLayer.featureCount()}",
        "encoding" : vdp.encoding(),
        "crs" : crs.description(),
        "dpSource" : vdp.description()
    }
    return resDict

def list_layers_in_s57(file_path):

    # 查看 GDAL 版本
    print("GDAL Version:", gdal.__version__)
    print(ogr)
    # 使用OGR打开文件
    print("ogr打开海图文件ing")
    ds = ogr.Open(file_path)
    print(ds)
    # 获取数据源格式
    driver = ds.GetDriver()
    print(f"数据源格式: {driver.GetDescription()}")

    # 获取图层数量
    layer_count = ds.GetLayerCount()
    print(f"图层数量: {layer_count}")

    if ds is None:
        print("打开失败")
        return "Failed open S57"
    # 获取数据源描述（文件路径）
    print(f"数据源描述: {ds.GetDescription()}")
    # 获取元数据
    metadata = ds.GetMetadata()
    if metadata:
        print("数据源元数据:")
        for key, value in metadata.items():
            print(f"{key}: {value}")
    else:
        print("没有元数据")

    # 列出文件中的所有图层
    layer_names = []
    for i in range(ds.GetLayerCount()):

        layer = ds.GetLayerByIndex(i)
        if layer:
            layer_names.append(layer.GetName())
            print(layer.GetName())

    return layer_names


