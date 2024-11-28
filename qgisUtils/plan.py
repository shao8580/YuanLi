from qgis.core import QgsGeometry, QgsPointXY, QgsFeature, QgsSpatialIndex,QgsProject

'''
def find_path(start_point, end_point, land_layer, restricted_layer):
    """
    使用A*算法找到不与陆地和禁行区域相交的路径
    start_point, end_point: QgsPointXY类型，表示路径的起点和终点
    land_layer: 陆地区域图层
    restricted_layer: 禁行区域图层
    """
    open_set = []  # 存储待探索的节点
    closed_set = []  # 存储已经探索过的节点

    # 初始化起点
    start_node = {'point': start_point, 'g': 0, 'h': start_point.distance(end_point)}
    open_set.append(start_node)

    while open_set:
        # 按照f = g + h的值排序，选择最优节点
        current_node = min(open_set, key=lambda node: node['g'] + node['h'])
        open_set.remove(current_node)

        # 如果到达终点，则返回路径
        if current_node['point'].distance(end_point) < 10:  # 允许一定范围内到达
            return reconstruct_path(current_node)

        # 将当前节点加入已探索的节点
        closed_set.append(current_node)

        # 生成邻近节点，并检查是否与陆地或禁行区域相交
        neighbors = generate_neighbors(current_node['point'])
        for neighbor in neighbors:
            if any([neighbor.intersects(land.geometry()) for land in land_layer.getFeatures()]) or \
                    any([neighbor.intersects(restricted.geometry()) for restricted in restricted_layer.getFeatures()]):
                continue  # 如果相交，跳过该节点

            g_score = current_node['g'] + current_node['point'].distance(neighbor)
            h_score = neighbor.distance(end_point)
            neighbor_node = {'point': neighbor, 'g': g_score, 'h': h_score, 'parent': current_node}

            if neighbor_node not in closed_set:
                open_set.append(neighbor_node)

    return None  # 未找到有效路径
'''

def generate_neighbors(point):
    """生成当前点的邻近点"""
    step_size = 0.05 # 调整步长以增加精度
    neighbors = [
        QgsPointXY(point.x() + step_size, point.y()),
        QgsPointXY(point.x() - step_size, point.y()),
        QgsPointXY(point.x(), point.y() + step_size),
        QgsPointXY(point.x(), point.y() - step_size),
        QgsPointXY(point.x() + step_size, point.y() + step_size),
        QgsPointXY(point.x() - step_size, point.y() - step_size),
        QgsPointXY(point.x() + step_size, point.y() - step_size),
        QgsPointXY(point.x() - step_size, point.y() + step_size),
    ]
    return neighbors


def reconstruct_path(node):
    """从目标节点向回追踪路径"""
    path = []
    while node:
        path.append(node['point'])
        node = node.get('parent', None)
    return path[::-1]  # 返回从起点到终点的路径
'''
def add_path_to_map(path, line_layer):
    """将生成的路径添加到地图中"""
    if len(path) < 2:
        return  # 路径点不足无法生成线

    line_feature = QgsFeature()
    line_geom = QgsGeometry.fromPolylineXY(path)
    line_feature.setGeometry(line_geom)

    line_layer.dataProvider().addFeature(line_feature)
    line_layer.updateExtents()
    QgsProject.instance().addMapLayer(line_layer)
'''
from qgis.core import QgsVectorLayer, QgsFeature, QgsGeometry, QgsProject

def add_path_to_map(path):
    """将生成的路径添加到新的线图层"""
    if len(path) < 2:
        print("未找到")
        return  # 路径点不足无法生成线

    # 创建一个新的线图层 (记得设置坐标参考系统 CRS)
    line_layer = QgsVectorLayer("LineString?crs=EPSG:4326", "Generated Path", "memory")
    if not line_layer.isValid():
        print("图层创建失败!")
        return

    # 获取数据提供者
    line_provider = line_layer.dataProvider()

    # 创建线要素
    line_feature = QgsFeature()
    line_geom = QgsGeometry.fromPolylineXY(path)
    line_feature.setGeometry(line_geom)

    # 将线要素添加到图层
    line_provider.addFeature(line_feature)
    line_layer.updateExtents()  # 更新图层的范围

    # 将图层添加到 QGIS 项目
    QgsProject.instance().addMapLayer(line_layer)
