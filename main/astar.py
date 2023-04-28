import heapq


class AStar:
    def __init__(self, grid, start, end):
        self.grid = grid
        self.start = start
        self.end = end

    def find_path(self):
        open_set = PriorityQueue()
        open_set.put(self.start, 0)
        came_from = {self.start: None}
        g_score = {(x, y): float("inf") for y, row in enumerate(self.grid) for x, _ in enumerate(row)}
        g_score[self.start] = 0

        while not open_set.empty():
            current = open_set.get()

            if current == self.end:
                return self.reconstruct_path(came_from, current)

            for neighbor in self.get_neighbors(current):
                tentative_g_score = g_score[current] + 1

                if tentative_g_score < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score = tentative_g_score + self.heuristic(neighbor, self.end)
                    open_set.put(neighbor, f_score)

        return None

    def get_neighbors(self, point):
        neighbors = []
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            x, y = point[0] + dx, point[1] + dy
            if 0 <= x < len(self.grid) and 0 <= y < len(self.grid[0]) and self.grid[y][x] != 1:
                neighbors.append((x, y))
        return neighbors

    def heuristic(self, point1, point2):
        return abs(point1[0] - point2[0]) + abs(point1[1] - point2[1])

    def reconstruct_path(self, came_from, current):
        path = [current]
        while current in came_from:
            current = came_from[current]
            if current:
                path.append(current)
        return path[::-1]


class PriorityQueue:
    def __init__(self):
        self.elements = []

    def empty(self):
        return len(self.elements) == 0

    def put(self, item, priority):
        heapq.heappush(self.elements, (priority, item))

    def get(self):
        return heapq.heappop(self.elements)[1]
