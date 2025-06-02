from geopy.distance import distance
from shapely.geometry import Point
from rssi_provider import predict_rssi
import math

def heuristic(a1, a2):
    if isinstance(a1, dict):
        a1 = (float(a1['lat']), float(a1['lon']))
    if isinstance(a2, dict):
        a2 = (float(a2['lat']), float(a2['lon']))
    return distance(a1,a2).meters

def get_neighbors(pos, obstacles, step=2/111320): # ~ 2m
    x,y=pos
    step_lon = step / math.cos(math.radians(x))
    directions = [
        (1, 0), (-1, 0),
        (0, 1), (0, -1),
        (1, 1), (-1, 1),
        (1, -1), (-1, -1)
    ]
    result=[]
    for dx,dy in directions:
        if dx != 0 and dy != 0:
            step_x = step / math.sqrt(2)
            step_y = step_lon / math.sqrt(2)
        else:
            step_x = step
            step_y = step_lon
        new=(x+dx*step_x,y+dy*step_y)
        in_obstacle = any(poly.contains(Point(new[1], new[0])) for poly in obstacles)
        print(f"Sprawdzam sąsiada: {new}, przeszkoda: {in_obstacle}")
        if not in_obstacle:
            result.append(new)
    return result

def is_in_obstacle(point, obstacles):
    point_geom= Point(point)
    return any(poly.contains(point_geom) for poly in obstacles)

import math
from shapely.geometry import Point

def is_in_obstacle(point, obstacles):
    if not isinstance(obstacles, list):
        print(f"[BŁĄD] obstacles nie jest listą: {type(obstacles)} -> {obstacles}")
        return False
    pt = Point(point[1], point[0])
    return any(poly.contains(pt) for poly in obstacles)

def points_are_close(p1, p2, threshold_m=0.5):
    from geopy.distance import distance
    return distance(p1, p2).meters < threshold_m

def is_in_forbidden(next_point, forbidden_positions):
    return any(points_are_close(next_point, p) for p in forbidden_positions)

def algorithm_A_step(start, goal, obstacles, target_pos, alpha=0.05, forbidden_positions=None):
    if forbidden_positions is None:
        forbidden_positions = []
    best_neighbor = None
    best_score = float('inf')
    rssi_current = predict_rssi(start, target_pos)
    neighbors = get_neighbors(start, obstacles)
    neighbors = [n for n in neighbors if not is_in_forbidden(n, forbidden_positions)]

    for neighbor in neighbors:
        rssi_neighbor = predict_rssi(neighbor, target_pos)
        signal_drop = max(0, rssi_current - rssi_neighbor)
        signal_penalty = alpha * signal_drop
        cost = heuristic(start, neighbor) + heuristic(neighbor, goal) + signal_penalty

        if cost < best_score:
            best_score = cost
            best_neighbor = neighbor

    if best_neighbor:
        return [start, best_neighbor]
    else:
        return [start]



        