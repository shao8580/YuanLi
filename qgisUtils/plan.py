from qgis.core import QgsGeometry, QgsPointXY, QgsFeature, QgsSpatialIndex,QgsProject
from qgis.core import QgsPointXY, QgsGeometry
import numpy as np
from scipy.interpolate import BarycentricInterpolator
import sympy as sp
from math import comb
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
import time
def generate_neighbors(point,step=0.3):
    """生成当前点的邻近点"""
    # step_size = 0.5  调整步长以增加精度
    # print(time.time())
    step_size = max(0.01,step*0.25)
    # step_size = 0.001
    neighbors = [
        QgsPointXY(point.x() + step_size, point.y()),
        QgsPointXY(point.x() - step_size, point.y()),
        QgsPointXY(point.x(), point.y() + step_size),
        QgsPointXY(point.x(), point.y() - step_size),
        QgsPointXY(point.x() + step_size/1.2, point.y() + step_size/1.2),
        QgsPointXY(point.x() + step_size/1.2, point.y() - step_size/1.2),
        QgsPointXY(point.x() - step_size/1.2, point.y() + step_size/1.2),
        QgsPointXY(point.x() - step_size/1.2, point.y() - step_size/1.2)
    ]

    return neighbors

def has_forced_neighbors(point,direction,land_layer,restricted_layer):
    """
    检查当前节点是否有强迫邻居
    :param point: 当前节点 (QgsPointXY)
    :param direction: 当前跳跃的方向 (tuple: dx, dy)
    :param restricted_layer: 禁行区域 (QgsVectorLayer)
    :param land_layer: 陆地区域 (QgsVectorLayer)
    :return: bool 是否存在强迫邻居
    """
    dx, dy = direction
    x, y = point.x(), point.y()

    # 当前位置的邻居坐标
    neighbors = [
        QgsPointXY(x + dx * 0.05, y),  # 水平邻居
        QgsPointXY(x, y + dy * 0.05),  # 垂直邻居
        QgsPointXY(x + dx * 0.05, y + dy * 0.05)  # 对角线邻居
    ]

    # 检查是否与障碍物相交
    for neighbor in neighbors:
        geom = QgsGeometry.fromPointXY(neighbor)
        if any([geom.intersects(feature.geometry()) for feature in restricted_layer.getFeatures()]) or \
                any([geom.intersects(feature.geometry()) for feature in land_layer.getFeatures()]):
            return True  # 存在障碍

    return False  # 没有强迫邻居
def reconstruct_path(node):
    """从目标节点向回追踪路径"""
    path = []
    while node:
        path.append(node['point'])
        node = node.get('parent', None)
    return path[::-1]  # 返回从起点到终点的路径

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


def smooth_path_with_bspline(control_points, restricted_layer,num_points=100):
    """
    计算贝塞尔曲线并检查每一段是否与禁行区域相交
    control_points: 控制点列表 [QgsPointXY, ...]
    num_points: 曲线上的点的数量
    restricted_layer: 禁行区域图层
    返回一个列表，包含贝塞尔曲线上的所有点
    """
    n = len(control_points) - 1  # 控制点数目
    t = np.linspace(0, 1, num_points)  # t 的取值范围

    # 获取控制点的 x 和 y 坐标
    x_coords = [point.x() for point in control_points]
    y_coords = [point.y() for point in control_points]

    # 使用贝塞尔曲线公式计算曲线坐标
    bezier_x = sum(comb(n, i) * ((1 - t) ** (n - i)) * (t ** i) * x_coords[i] for i in range(n + 1))
    bezier_y = sum(comb(n, i) * ((1 - t) ** (n - i)) * (t ** i) * y_coords[i] for i in range(n + 1))

    print_bezier_equation(control_points)

    # 生成曲线上的点
    bezier_path = [QgsPointXY(x, y) for x, y in zip(bezier_x, bezier_y)]

    # 检查曲线上的每个小段是否与禁行区域相交
    filtered_bezier_path = [bezier_path[0]]  # 将第一个点加入路径

    for i in range(1, len(bezier_path)):
        # 当前段的起点和终点
        start_point = bezier_path[i - 1]
        end_point = bezier_path[i]

        # 检查线段是否与禁行区域相交
        if not check_segment_intersects_with_restricted_area(start_point, end_point, restricted_layer):
            filtered_bezier_path.append(end_point)  # 如果没有相交，则加入路径

    return filtered_bezier_path


def check_segment_intersects_with_restricted_area(start_point, end_point, restricted_layer):
    """
    检查从起点到终点的线段是否与禁行区域相交
    :param start_point: 起点 QgsPointXY
    :param end_point: 终点 QgsPointXY
    :param restricted_layer: 禁行区域图层
    :return: 如果相交，返回 True；否则返回 False
    """
    # 创建从起点到终点的线段
    segment = QgsGeometry.fromPolylineXY([start_point, end_point])

    # 检查该线段是否与禁行区域相交
    for restricted in restricted_layer.getFeatures():
        restricted_geom = restricted.geometry()
        if segment.intersects(restricted_geom):
            return True  # 如果线段与禁行区域相交，返回 True

    return False  # 如果没有相交，返回 False

def print_bezier_equation(control_points):
    n = len(control_points) - 1  # 控制点数目
    t = sp.symbols('t')

    # 获取控制点的 x 和 y 坐标
    x_coords = [control_points[i].x() for i in range(len(control_points))]
    y_coords = [control_points[i].y() for i in range(len(control_points))]

    # 计算贝塞尔曲线方程
    bezier_x_eq = sum(comb(n, i) * ((1 - t) ** (n - i)) * (t ** i) * x_coords[i] for i in range(n + 1))
    bezier_y_eq = sum(comb(n, i) * ((1 - t) ** (n - i)) * (t ** i) * y_coords[i] for i in range(n + 1))

    # 打印贝塞尔曲线的方程
    print(f"贝塞尔曲线的x方程: {bezier_x_eq}")
    print(f"贝塞尔曲线的y方程: {bezier_y_eq}")


def a_star_search_1(self,direction=0):
    """
    使用 A* 算法搜索路径，并检查每个邻近点是否与禁行区域相交。

    参数:
    start_point (QgsPointXY): 起点
    end_point (QgsPointXY): 终点
    restricted_layer (QgsVectorLayer): 禁行区域图层
    land_layer (QgsVectorLayer): 陆地图层

    返回:
    list: 生成的路径列表，或者 None（如果没有找到路径）
    """


    a = 0;
    b = 0;
    c = 0;
    d = 0;  # a为文本打印耗时,b为生成节点并判断是否相交时长,c为A*计算
    point_layer = self.layerTreeView.currentLayer()
    provider = point_layer.dataProvider()

    # 获取所有点要素
    all_features = [feat for feat in provider.getFeatures()]
    # 过滤掉 id 属性为 NULL 的点 (假设 id 在第3列索引为2)
    # 过滤掉 id 属性为 NULL 的点 (假设 id 在第3列索引为2)
    valid_features = [feat for feat in all_features if
                      not feat.attribute(2) is None and not feat.attribute(2) == "Standard"]
    # 按 id 属性排序点要素 (假设 id 在第3列索引为2)
    sorted_features = sorted(valid_features, key=lambda f: f.attribute(2))  # 这里 2 是 id 列的索引
    print(sorted_features)
    # start_point = QgsPointXY(121.98, 38.80)  # 起点坐标 (经度: 118.15, 纬度: 24.45)
    # end_point = QgsPointXY(122.25, 38.99)  # 终点坐标 (经度: 119.5, 纬度: 25.0)
    # print(start_point, end_point)
    if direction == 0:
        start_point = sorted_features[0].geometry().asPoint()
        end_point = sorted_features[-1].geometry().asPoint()
    if direction == 1:
        start_point = sorted_features[-1].geometry().asPoint()
        end_point = sorted_features[0].geometry().asPoint()
    print("起始点")
    print(start_point)
    print("终点")
    print(end_point)
    # start_point = start_point_1
    # end_point = sorted_features[1]

    all_layers = [layer for layer in QgsProject.instance().mapLayers().values()]
    matching_layers = [index for index, layer in enumerate(all_layers)
                       if 'LNDARE' in layer.name() or 'RESARE' in layer.name()]

    # spatial_indexes = {}
    # for layer in matching_layers:
    #     spatial_index = QgsSpatialIndex(all_layers[layer])
    #     spatial_indexes[all_layers[layer].name()] = spatial_index  # 存储索引
    #     print(f"空间索引已创建：{all_layers[layer].name()}")
    # print("全图层如下",all_layers)

    # land_layer_list=[]
    # restricted_layer_list=[]
    # for i in range(0,len(matching_layers),2):
    #     land_layer_list.append(all_layers[matching_layers[i]])
    #     restricted_layer_list.append(all_layers[matching_layers[i+1]])
    # print("陆地图层有",land_layer_list)
    #

    land_layer = all_layers[matching_layers[0]]
    restricted_layer = all_layers[matching_layers[1]]


    open_set = []  # 存储待探索的节点
    closed_set = []  # 存储已经探索过的节点

    # 初始化起点
    start_node = {'point': start_point, 'g': 0, 'h': start_point.distance(end_point)}
    open_set.append(start_node)

    while open_set:
        c_time_start = time.time()
        # 按照f = g + h的值排序，选择最优节点
        current_node = min(open_set, key=lambda node: node['g'] + node['h'])
        open_set.remove(current_node)
        c_time_end = time.time()
        c += c_time_end - c_time_start

        # 如果到达终点，则返回路径
        if current_node['point'].distance(end_point) < 0.6:  # 允许一定范围内到达

            while open_set:
                c_time_start = time.time()
                # 按照f = g + h的值排序，选择最优节点
                current_node = min(open_set, key=lambda node: node['g'] + node['h'])
                open_set.remove(current_node)
                c_time_end = time.time()
                c += c_time_end - c_time_start
                # 如果到达终点，则返回路径
                if current_node['point'].distance(end_point) < 0.01:  # 允许一定范围内到达

                    print("已找到路径")

                    list1 = reconstruct_path(current_node)
                    list2 = smooth_path_with_bspline(list1, restricted_layer)

                    add_path_to_map(list1)
                    add_path_to_map(list2)

                    print(f"生产临近点耗时{a:.3f}")
                    print(f"路径计算耗时{b:.3f}")
                    print(f"A*计算权值耗时{c:.3f}")
                    print(f"计算是否接触耗时{d:.3f}")
                    return reconstruct_path(current_node)

                print(current_node['point'].distance(end_point))

                # 将当前节点加入已探索的节点
                closed_set.append(current_node)
                b_time_start = time.time()
                # 生成邻近节点，并检查是否与陆地或禁行区域相交
                a_time_start = time.time()
                neighbors = generate_neighbors(current_node['point'], current_node['point'].distance(end_point))
                a_time_end = time.time()
                a += a_time_end - a_time_start

                for neighbor in neighbors:
                    # 将 QgsPointXY 转换为 QgsGeometry
                    neighbor_geom = QgsGeometry.fromPointXY(neighbor)
                    d_time_start = time.time()
                    # 检查邻近点是否与陆地或禁行区域相交

                    if check_segment_intersects_with_restricted_area(current_node['point'], neighbor, restricted_layer):
                        continue  # 如果相交，跳过该节点
                    if check_segment_intersects_with_restricted_area(current_node['point'], neighbor, land_layer):
                        continue
                    d_time_end = time.time()
                    d += d_time_end - d_time_start

                    # g_score = current_node['g'] + current_node['point'].distance(neighbor)
                    h_score = neighbor.distance(end_point)
                    neighbor_node = {'point': neighbor, 'g': 0, 'h': h_score, 'parent': current_node}

                    if neighbor_node not in closed_set:
                        open_set.append(neighbor_node)
                b_time_end = time.time()
                b += b_time_end - b_time_start

        print(current_node['point'].distance(end_point))

        b_time_start = time.time()
        # 将当前节点加入已探索的节点
        closed_set.append(current_node)

        # 生成邻近节点，并检查是否与陆地或禁行区域相交
        a_time_start = time.time()
        neighbors = generate_neighbors(current_node['point'], current_node['point'].distance(end_point))
        a_time_end = time.time()
        a += a_time_end - a_time_start
        for neighbor in neighbors:
            # 将 QgsPointXY 转换为 QgsGeometry
            neighbor_geom = QgsGeometry.fromPointXY(neighbor)
            d_time_start = time.time()

            # 检查邻近点是否与陆地或禁行区域相交
            if check_segment_intersects_with_restricted_area(current_node['point'], neighbor, restricted_layer):
                continue  # 如果相交，跳过该节点
            if check_segment_intersects_with_restricted_area(current_node['point'], neighbor, land_layer):
                continue
            d_time_end = time.time()
            d += d_time_end - d_time_start

            g_score = current_node['g'] + current_node['point'].distance(neighbor)
            h_score = neighbor.distance(end_point)
            neighbor_node = {'point': neighbor, 'g': g_score, 'h': h_score, 'parent': current_node}

            if neighbor_node not in closed_set:
                open_set.append(neighbor_node)
        b_time_end = time.time()
        b += b_time_end - b_time_start
    print("未找到合适路径")
    return None  # 未找到有效路径



def check_segment_intersects_with_restricted_area_1(start_point, end_point, spatial_indexes):
    """
    检查线段是否与多个限制区域的图层相交。

    :param start_point: 起点 (QgsPointXY)
    :param end_point: 终点 (QgsPointXY)
    :param spatial_indexes: 包含图层和对应空间索引的字典
    :return: 如果相交返回 True，否则返回 False
    """
    # 创建线段几何
    segment = QgsGeometry.fromPolylineXY([start_point, end_point])
    segment_bbox = segment.boundingBox()  # 获取线段的边界框

    # 遍历每个空间索引进行检查
    for layer_name, index_info in spatial_indexes.items():
        layer = index_info["layer"]
        spatial_index = index_info["spatial_index"]

        # 在空间索引中快速找到与线段边界框可能相交的要素 ID
        potential_ids = spatial_index.intersects(segment_bbox)

        # 遍历可能相交的要素，检查精确的几何相交情况
        for fid in potential_ids:
            feature = layer.getFeature(fid)
            if segment.intersects(feature.geometry()):
                print(f"线段与图层 {layer_name} 的要素 ID {fid} 相交")
                return True  # 如果找到相交的要素，立即返回 True

    return False  # 如果所有图层均未相交，返回 False

def a_star_search(self,direction=0):
    """
    使用 A* 算法搜索路径，使用空间矢量索引优化大区域计算

    参数:
    start_point (QgsPointXY): 起点
    end_point (QgsPointXY): 终点
    restricted_layer (QgsVectorLayer): 禁行区域图层
    land_layer (QgsVectorLayer): 陆地图层

    返回:
    list: 生成的路径列表，或者 None（如果没有找到路径）
    """
    a = 0;
    b = 0;
    c = 0;
    d = 0;  # a为文本打印耗时,b为生成节点并判断是否相交时长,c为A*计算
    point_layer = self.layerTreeView.currentLayer()
    provider = point_layer.dataProvider()

    # 获取所有点要素
    all_features = [feat for feat in provider.getFeatures()]
    # 过滤掉 id 属性为 NULL 的点 (假设 id 在第3列索引为2)
    # 过滤掉 id 属性为 NULL 的点 (假设 id 在第3列索引为2)
    valid_features = [feat for feat in all_features if
                      not feat.attribute(2) is None and not feat.attribute(2) == "Standard"]
    # 按 id 属性排序点要素 (假设 id 在第3列索引为2)
    sorted_features = sorted(valid_features, key=lambda f: f.attribute(2))  # 这里 2 是 id 列的索引
    print(sorted_features)
    if direction == 0:
        start_point = sorted_features[0].geometry().asPoint()
        end_point = sorted_features[-1].geometry().asPoint()
    if direction == 1:
        start_point = sorted_features[-1].geometry().asPoint()
        end_point = sorted_features[0].geometry().asPoint()
    print("起始点")
    print(start_point)
    print("终点")
    print(end_point)
    # 优化all_layers为字典，创建空间索引
    all_layers = {layer.name(): layer for layer in QgsProject.instance().mapLayers().values()}
    matching_layers = [layer for layer in all_layers.values() if 'LNDARE' in layer.name() or 'RESARE' in layer.name()]

    spatial_indexes = {}  # 用于存储每个图层的空间索引

    for layer in matching_layers:
        spatial_index = QgsSpatialIndex(layer.getFeatures())  # 基于所有要素创建空间索引
        spatial_indexes[layer.name()] = {"layer": layer, "spatial_index": spatial_index}  # 存储索引与图层
        print(f"空间索引已创建：{layer.name()}")

    print("全图层如下",spatial_indexes)
    open_set = []  # 存储待探索的节点
    closed_set = []  # 存储已经探索过的节点
    # 初始化起点
    start_node = {'point': start_point, 'g': 0, 'h': start_point.distance(end_point)}
    open_set.append(start_node)

    while open_set:
        c_time_start = time.time()
        # 按照f = g + h的值排序，选择最优节点
        current_node = min(open_set, key=lambda node: node['g'] + node['h'])
        open_set.remove(current_node)
        c_time_end = time.time()
        c += c_time_end - c_time_start

        # 如果到达终点，则返回路径
        if current_node['point'].distance(end_point) < 0.6:  # 允许一定范围内到达

            while open_set:
                c_time_start = time.time()
                # 按照f = g + h的值排序，选择最优节点
                current_node = min(open_set, key=lambda node: node['g'] + node['h'])
                open_set.remove(current_node)
                c_time_end = time.time()
                c += c_time_end - c_time_start
                # 如果到达终点，则返回路径
                if current_node['point'].distance(end_point) < 0.01:  # 允许一定范围内到达

                    print("已找到路径")

                    list1 = reconstruct_path(current_node)
                    add_path_to_map(list1)

                    print(f"生产临近点耗时{a:.3f}")
                    print(f"路径计算耗时{b:.3f}")
                    print(f"A*计算权值耗时{c:.3f}")
                    print(f"计算是否接触耗时{d:.3f}")
                    return reconstruct_path(current_node)

                print(current_node['point'].distance(end_point))

                # 将当前节点加入已探索的节点
                closed_set.append(current_node)
                b_time_start = time.time()
                # 生成邻近节点，并检查是否与陆地或禁行区域相交
                a_time_start = time.time()
                neighbors = generate_neighbors(current_node['point'], current_node['point'].distance(end_point))
                a_time_end = time.time()
                a += a_time_end - a_time_start

                for neighbor in neighbors:
                    # 将 QgsPointXY 转换为 QgsGeometry
                    neighbor_geom = QgsGeometry.fromPointXY(neighbor)
                    d_time_start = time.time()
                    # 检查邻近点是否与陆地或禁行区域相交

                    if check_segment_intersects_with_restricted_area_1(current_node['point'], neighbor, spatial_indexes):
                        continue  # 如果相交，跳过该节点

                    d_time_end = time.time()
                    d += d_time_end - d_time_start

                    # g_score = current_node['g'] + current_node['point'].distance(neighbor)
                    h_score = neighbor.distance(end_point)
                    neighbor_node = {'point': neighbor, 'g': 0, 'h': h_score, 'parent': current_node}

                    if neighbor_node not in closed_set:
                        open_set.append(neighbor_node)
                b_time_end = time.time()
                b += b_time_end - b_time_start

        print(current_node['point'].distance(end_point))

        b_time_start = time.time()
        # 将当前节点加入已探索的节点
        closed_set.append(current_node)

        # 生成邻近节点，并检查是否与陆地或禁行区域相交
        a_time_start = time.time()
        neighbors = generate_neighbors(current_node['point'], current_node['point'].distance(end_point))
        a_time_end = time.time()
        a += a_time_end - a_time_start
        for neighbor in neighbors:
            # 将 QgsPointXY 转换为 QgsGeometry
            neighbor_geom = QgsGeometry.fromPointXY(neighbor)
            d_time_start = time.time()

            # 检查邻近点是否与陆地或禁行区域相交
            if check_segment_intersects_with_restricted_area_1(current_node['point'], neighbor, spatial_indexes):
                continue  # 如果相交，跳过该节点

            d_time_end = time.time()
            d += d_time_end - d_time_start

            g_score = current_node['g'] + current_node['point'].distance(neighbor)
            h_score = neighbor.distance(end_point)
            neighbor_node = {'point': neighbor, 'g': g_score, 'h': h_score, 'parent': current_node}

            if neighbor_node not in closed_set:
                open_set.append(neighbor_node)
        b_time_end = time.time()
        b += b_time_end - b_time_start
    print("未找到合适路径")
    return None  # 未找到有效路径

