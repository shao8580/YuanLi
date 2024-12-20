def create_polygon(self, angle=0):
    """
    创建多边形几何并支持旋转
    :param angle: 多边形的旋转角度，单位为度
    :return: QgsGeometry 对应的多边形几何
    """
    if not self.center_point or not self.radius_point:
        return None

    import math
    radius = self.center_point.distance(self.radius_point)  # 计算半径
    sides = self.bian  # 用户输入的边数

    # 计算旋转角度的弧度
    angle_radians = math.radians(angle)

    # 生成多边形的顶点
    points = []
    for i in range(sides):
        theta = 2 * math.pi * i / sides + angle_radians  # 顶点的角度位置
        x = self.center_point.x() + radius * math.cos(theta)
        y = self.center_point.y() + radius * math.sin(theta)
        points.append(QgsPointXY(x, y))

    # 闭合多边形
    points.append(points[0])

    return QgsGeometry.fromPolylineXY(points)
