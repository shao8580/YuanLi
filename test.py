nearest_ids = spatial_index.nearestNeighbor(current_node['point'], 1)  # 找到最近的一个障碍物
if nearest_ids:
    nearest_feature = next(layer.getFeatures(QgsFeatureRequest(nearest_ids[0])))
    nearest_distance = current_node['point'].distance(nearest_feature.geometry().nearestPoint(QgsGeometry.fromPointXY(current_node['point'])).asPoint())
else:
    nearest_distance = 0.01  # 设定一个最小步长