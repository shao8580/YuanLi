while open_set:
    c_time_start = time.time()
    # 按照 f = g + h 排序，选择最优节点
    current_node = min(open_set, key=lambda node: node['g'] + node['h'])
    open_set.remove(current_node)
    c_time_end = time.time()
    c += c_time_end - c_time_start

    # 如果到达终点，返回路径
    if current_node['point'].distance(end_point) < 0.6:
        print("已找到路径")
        path = reconstruct_path(current_node)
        smooth_path = smooth_path_with_bspline(path, restricted_layer)
        add_path_to_map(path)
        add_path_to_map(smooth_path)
        print(f"生成临近点耗时 {a:.3f}")
        print(f"路径计算耗时 {b:.3f}")
        print(f"A* 计算权值耗时 {c:.3f}")
        print(f"计算是否相交耗时 {d:.3f}")
        return path

    # 将当前节点加入已探索的节点
    closed_set.append(current_node)

    # 定义跳点方向
    directions = [(1, 0), (0, 1), (-1, 0), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]

    for direction in directions:
        jump_point = current_node['point']
        while True:
            # 计算下一个点
            next_point = QgsPointXY(jump_point.x() + direction[0] * 0.05,
                                    jump_point.y() + direction[1] * 0.05)

            # 检查边界条件
            if next_point.distance(end_point) < 0.3:
                # 到达终点
                g_score = current_node['g'] + current_node['point'].distance(next_point)
                h_score = next_point.distance(end_point)
                next_node = {'point': next_point, 'g': g_score, 'h': h_score, 'parent': current_node}
                open_set.append(next_node)
                break

            # 检查是否与禁行区域或陆地相交
            neighbor_geom = QgsGeometry.fromPointXY(next_point)
            d_time_start = time.time()
            if any([neighbor_geom.intersects(land.geometry()) for land in land_layer.getFeatures()]) or \
                    check_segment_intersects_with_restricted_area(jump_point, next_point, restricted_layer):
                break  # 碰到障碍停止跳跃
            d_time_end = time.time()
            d += d_time_end - d_time_start

            # 检查强迫邻居
            if has_forced_neighbors(next_point, direction, restricted_layer, land_layer):
                g_score = current_node['g'] + current_node['point'].distance(next_point)
                h_score = next_point.distance(end_point)
                next_node = {'point': next_point, 'g': g_score, 'h': h_score, 'parent': current_node}
                open_set.append(next_node)
                break

            # 向前跳跃
            jump_point = next_point

print("未找到合适路径")
return None