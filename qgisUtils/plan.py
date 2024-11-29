from qgis.core import QgsGeometry, QgsPointXY, QgsFeature, QgsSpatialIndex,QgsProject
from qgis.core import QgsPointXY, QgsGeometry
import numpy as np
from scipy.interpolate import BarycentricInterpolator
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

def generate_neighbors(point,step_size=0.5):
    """生成当前点的邻近点"""
    # step_size = 0.5  调整步长以增加精度
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
        print("点数量不足")
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
'''
def smooth_path_with_bspline(path, num_points=100):
    """
    使用 B样条曲线对路径进行平滑
    :param path: 需要平滑的路径，类型为 [QgsPointXY, ...]
    :param num_points: 生成平滑曲线的点数
    :return: 平滑后的路径
    """
    # 将路径中的点坐标提取出来
    x_coords = [point.x() for point in path]
    y_coords = [point.y() for point in path]

    # 使用 scipy 的 BarycentricInterpolator 拟合 B样条曲线
    interpolator_x = BarycentricInterpolator(range(len(x_coords)), x_coords)
    interpolator_y = BarycentricInterpolator(range(len(y_coords)), y_coords)

    # 根据插值生成平滑路径
    smooth_x = interpolator_x(np.linspace(0, len(x_coords) - 1, num_points))
    smooth_y = interpolator_y(np.linspace(0, len(y_coords) - 1, num_points))

    # 将平滑后的坐标转换为 QgsPointXY
    smooth_path = [QgsPointXY(x, y) for x, y in zip(smooth_x, smooth_y)]

    return smooth_path
'''

import numpy as np
from scipy.special import comb


def smooth_path_with_bspline(control_points, num_points=100):
    """
    生成三次贝塞尔曲线
    :param control_points: 控制点的列表 [QgsPointXY, ...]
    :param num_points: 曲线上的点数
    :return: 曲线的点列表
    """
    n = len(control_points) - 1  # 控制点数目
    t = np.linspace(0, 1, num_points)  # t 的取值范围

    # 获取控制点的 x 和 y 坐标
    x_coords = [point.x() for point in control_points]
    y_coords = [point.y() for point in control_points]

    # 使用贝塞尔曲线公式计算曲线坐标
    bezier_x = sum(comb(n, i) * ((1 - t) ** (n - i)) * (t ** i) * x_coords[i] for i in range(n + 1))
    bezier_y = sum(comb(n, i) * ((1 - t) ** (n - i)) * (t ** i) * y_coords[i] for i in range(n + 1))

    # 生成曲线上的点
    bezier_path = [QgsPointXY(x, y) for x, y in zip(bezier_x, bezier_y)]

    return bezier_path
