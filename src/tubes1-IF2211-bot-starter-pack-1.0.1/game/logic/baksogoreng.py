from typing import Optional
from game.logic.base import BaseLogic
from game.models import Board, GameObject, Position
from game.util import get_direction

class baksogorengg(BaseLogic):
    static_goals: list[Position] = []
    static_goal_teleport: Optional[GameObject] = None
    static_temp_goals: Optional[Position] = None
    static_direct_to_base_via_teleporter: bool = False

    def __init__(self) -> None:
        self.directions = [(1, 0), (0, 1), (-1, 0), (0, -1)]
        self.goal_position: Optional[Position] = None
        self.current_direction = 0
        self.distance = 0

    def next_move(self, board_bot: GameObject, board: Board):
        props = board_bot.properties
        self.board = board
        self.board_bot = board_bot
        self.diamonds = board.diamonds
        self.teleporter = [d for d in board.game_objects if d.type == "TeleportGameObject"]
        self.redButton = [d for d in board.game_objects if d.type == "DiamondButtonGameObject"]

        if board_bot.position == props.base:
            self.static_goals.clear()
            self.static_goal_teleport = None
            self.static_temp_goals = None
            self.static_direct_to_base_via_teleporter = False

        if self.static_goal_teleport and board_bot.position == self.find_other_teleport(self.static_goal_teleport):
            self.static_goals.remove(self.static_goal_teleport.position)
            self.static_goal_teleport = None
        if not self.static_goal_teleport and board_bot.position in self.static_goals:
            self.static_goals.remove(board_bot.position)
        if board_bot.position == self.static_temp_goals:
            self.static_temp_goals = None

        if props.diamonds == 5 or (props.milliseconds_left < 5000 and props.diamonds > 1):
            self.goal_position = self.find_best_way_to_base()
            if not self.static_direct_to_base_via_teleporter:
                self.static_goals.clear()
                self.static_goal_teleport = None
        else:
            if not self.static_goals:
                self.find_nearest_diamond()
            self.goal_position = self.static_goals[0]

        if self.calculate_near_base() and props.diamonds > 2:
            self.goal_position = self.find_best_way_to_base()
            if not self.static_direct_to_base_via_teleporter:
                self.static_goals.clear()
                self.static_goal_teleport = None

        if self.static_temp_goals:
            self.goal_position = self.static_temp_goals

        if self.goal_position:
            if not self.static_temp_goals:
                self.check_obstacle('teleporter')
            if props.diamonds == 4:
                self.check_obstacle('redDiamond')
            dx, dy = get_direction(board_bot.position.x, board_bot.position.y,
                                   self.goal_position.x, self.goal_position.y)
        else:
            dx, dy = self.directions[self.current_direction]
            self.current_direction = (self.current_direction + 1) % len(self.directions)

        if dx == 0 and dy == 0:
            self.static_goals.clear()
            self.static_goal_teleport = None
            self.static_temp_goals = None
            self.goal_position = None
            dx, dy = self.next_move(board_bot, board)

        return dx, dy

    def find_best_way_to_base(self):
        cur = self.board_bot.position
        base = self.board_bot.properties.base
        base_pos = Position(base.y, base.x)
        dist_direct = abs(base.x - cur.x) + abs(base.y - cur.y)

        tp_in, tp_out, tp_obj = self.find_nearest_teleport()
        if not tp_in or not tp_out:
            return base_pos

        dist_tp = (abs(tp_in.x - cur.x) + abs(tp_in.y - cur.y) +
                   abs(tp_out.x - base.x) + abs(tp_out.y - base.y))

        if dist_direct <= dist_tp:
            return base_pos

        self.static_direct_to_base_via_teleporter = True
        self.static_goal_teleport = tp_obj
        self.static_goals = [tp_in, base_pos]
        return tp_in

    def calculate_near_base(self):
        cur = self.board_bot.position
        base = self.board_bot.properties.base
        dist_direct = abs(base.x - cur.x) + abs(base.y - cur.y)
        dist_tp = self.find_base_distance_teleporter()
        return min(dist_direct, dist_tp) < self.distance

    def find_base_distance_teleporter(self):
        cur = self.board_bot.position
        tp_in, tp_out, _ = self.find_nearest_teleport()
        if not tp_in or not tp_out:
            return float("inf")
        base = self.board_bot.properties.base
        return (abs(tp_in.x - cur.x) + abs(tp_in.y - cur.y) +
                abs(tp_out.x - base.x) + abs(tp_out.y - base.y))

    def find_nearest_diamond(self):
        direct_dist, direct_pos = self.find_nearest_diamond_direct()
        tp_dist, tp_path, tp_obj = self.find_nearest_diamond_teleport()
        red_dist, red_pos = self.find_nearest_red_button()

        if direct_dist <= tp_dist and direct_dist <= red_dist:
            self.static_goals = [direct_pos]
            self.distance = direct_dist
        elif tp_dist <= red_dist:
            self.static_goals = tp_path
            self.static_goal_teleport = tp_obj
            self.distance = tp_dist
        else:
            self.static_goals = [red_pos]
            self.distance = red_dist

    def find_nearest_red_button(self):
        cur = self.board_bot.position
        btn = self.redButton[0]
        dist = abs(btn.position.x - cur.x) + abs(btn.position.y - cur.y)
        return dist, btn.position

    def find_nearest_teleport(self):
        cur = self.board_bot.position
        min_dist = float("inf")
        best_tp, tp_in, tp_out = None, None, None
        for tp in self.teleporter:
            dist = abs(tp.position.x - cur.x) + abs(tp.position.y - cur.y)
            if dist and dist < min_dist:
                min_dist = dist
                best_tp = tp
                tp_in = tp.position
                tp_out = self.find_other_teleport(tp)
        return tp_in, tp_out, best_tp

    def find_other_teleport(self, tp: GameObject):
        return next((t.position for t in self.teleporter if t.id != tp.id), None)

    def find_nearest_diamond_teleport(self):
        cur = self.board_bot.position
        tp_in, tp_out, tp_obj = self.find_nearest_teleport()
        if not tp_in or not tp_out:
            return float("inf"), [], None

        best_diamond, min_dist = None, float("inf")
        for d in self.diamonds:
            if d.properties.points == 2 and self.board_bot.properties.diamonds == 4:
                continue
            dist = (abs(tp_in.x - cur.x) + abs(tp_in.y - cur.y) +
                    abs(d.position.x - tp_out.x) + abs(d.position.y - tp_out.y)) / d.properties.points
            if dist < min_dist:
                min_dist = dist
                best_diamond = d
        if best_diamond:
            return min_dist, [tp_in, best_diamond.position], tp_obj
        return float("inf"), [], None

    def find_nearest_diamond_direct(self):
        cur = self.board_bot.position
        best_diamond, min_dist = None, float("inf")
        for d in self.diamonds:
            if d.properties.points == 2 and self.board_bot.properties.diamonds == 4:
                continue
            dist = (abs(d.position.x - cur.x) + abs(d.position.y - cur.y)) / d.properties.points
            if dist < min_dist:
                min_dist = dist
                best_diamond = d
        return min_dist, best_diamond.position if best_diamond else None

    def check_obstacle(self, obj_type):
        cur = self.board_bot.position
        dest = self.goal_position

        if obj_type == 'teleporter':
            objs = self.teleporter
        elif obj_type == 'redDiamond':
            objs = [d for d in self.diamonds if d.properties.points == 2]
        else:
            return

        for o in objs:
            pos = o.position
            if pos == cur:
                continue
            if (pos.x == dest.x and min(cur.y, dest.y) < pos.y < max(cur.y, dest.y)):
                alt_x = dest.x + 1 if dest.x <= 1 else dest.x - 1
                self.static_temp_goals = Position(dest.y, alt_x)
                self.goal_position = self.static_temp_goals
                return
            if (pos.y == dest.y and min(cur.x, dest.x) < pos.x < max(cur.x, dest.x)):
                alt_y = dest.y + 1 if dest.y <= 1 else dest.y - 1
                self.static_temp_goals = Position(alt_y, dest.x)
                self.goal_position = self.static_temp_goals
                return
