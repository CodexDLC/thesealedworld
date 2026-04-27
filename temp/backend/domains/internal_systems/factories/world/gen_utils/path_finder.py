import heapq


class PathFinder:
    def __init__(self, world_matrix: dict):
        """
        :param world_matrix: Полная матрица мира {(x, y): cell_data}
        Теперь мы просто храним ссылку на данные. Это не жрет память.
        """
        self.matrix = world_matrix

    def get_path(self, start: tuple[int, int], end: tuple[int, int]) -> list[tuple[int, int]]:
        """
        Ищет путь A* (4 направления: Крест).
        """
        # Проверка валидности старта и финиша
        if start not in self.matrix or end not in self.matrix:
            return []

        # Если конечная точка непроходима (Стена), путь невозможен
        # (Хотя можно искать до ближайшей точки, но пока так)
        end_cell = self.matrix[end]
        if end_cell["flags"].get("travel_cost", 1) >= 999:
            return []

        frontier: list[tuple[float, tuple[int, int]]] = []
        heapq.heappush(frontier, (0, start))
        came_from: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
        cost_so_far = {start: 0.0}

        while frontier:
            _, current = heapq.heappop(frontier)

            if current == end:
                break

            # 4 НАПРАВЛЕНИЯ (КРЕСТ)
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                next_node = (current[0] + dx, current[1] + dy)

                # Проверка: есть ли такая клетка в мире
                if next_node not in self.matrix:
                    continue

                cell = self.matrix[next_node]

                # 🔥 ЧИТАЕМ ЦЕНУ ИЗ ФЛАГА (Быстро и просто)
                # Если флага нет, берем дефолт 1.0. Если стена, там будет 999.
                move_cost = cell["flags"].get("travel_cost", 1.0)

                if move_cost >= 999:  # Непроходимо
                    continue

                new_cost = cost_so_far[current] + move_cost

                if next_node not in cost_so_far or new_cost < cost_so_far[next_node]:
                    cost_so_far[next_node] = new_cost
                    priority = new_cost + (abs(end[0] - next_node[0]) + abs(end[1] - next_node[1]))
                    heapq.heappush(frontier, (priority, next_node))
                    came_from[next_node] = current

        # Восстановление пути
        if end not in came_from:
            return []

        path = []
        curr: tuple[int, int] | None = end
        while curr:
            path.append(curr)
            curr = came_from[curr]
        return path[::-1]
