def actionPLANTriggered(self):
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
    start_point = sorted_features[0].geometry().asPoint()
    end_point = sorted_features[-1].geometry().asPoint()
    print(start_point)
    print(end_point)
    # start_point = start_point_1
    # end_point = sorted_features[1]
    all_layers = [layer for layer in QgsProject.instance().mapLayers().values()]
    land_layer = all_layers[2]
    restricted_layer = all_layers[3]

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
        if current_node['point'].distance(end_point) < 0.5:  # 允许一定范围内到达
            print("已找到路径")
            list1 = reconstruct_path(current_node)
            list2 = smooth_path_with_bspline(list1)

            add_path_to_map(list1)
            add_path_to_map(list2)
            return reconstruct_path(current_node)

        # 将当前节点加入已探索的节点
        closed_set.append(current_node)

        # 生成邻近节点，并检查是否与陆地或禁行区域相交
        neighbors = generate_neighbors(current_node['point'])
        for neighbor in neighbors:
            # 将 QgsPointXY 转换为 QgsGeometry
            neighbor_geom = QgsGeometry.fromPointXY(neighbor)

            # 检查邻近点是否与陆地或禁行区域相交
            if any([neighbor_geom.intersects(land.geometry()) for land in land_layer.getFeatures()]) or \
                    any([neighbor_geom.intersects(restricted.geometry()) for restricted in
                         restricted_layer.getFeatures()]):
                continue  # 如果相交，跳过该节点

            # # 检查邻近点是否与陆地或禁行区域相交
            # if any([neighbor_geom.intersects(land.geometry()) for land in land_layer.getFeatures()]) or \
            #         any([neighbor_geom.intersects(restricted.geometry()) for restricted in
            #              restricted_layer.getFeatures()]):
            #     continue  # 如果相交，跳过该节点
            # # 生成邻近节点，并检查是否与陆地或禁行区域相交
            # neighbors = generate_neighbors(current_node['point'])
            # for neighbor in neighbors:
            #     if any([neighbor.intersects(land.geometry()) for land in land_layer.getFeatures()]) or \
            #             any([neighbor.intersects(restricted.geometry()) for restricted in
            #                  restricted_layer.getFeatures()]):
            #         continue  # 如果相交，跳过该节点

            g_score = current_node['g'] + current_node['point'].distance(neighbor)
            h_score = neighbor.distance(end_point)
            neighbor_node = {'point': neighbor, 'g': g_score, 'h': h_score, 'parent': current_node}

            if neighbor_node not in closed_set:
                open_set.append(neighbor_node)
    print("未找到合适路径")
    return None  # 未找到有效路径
