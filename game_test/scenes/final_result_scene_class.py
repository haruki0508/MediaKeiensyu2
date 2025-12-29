import pygame
import math
import time
import os
from core.scene import Scene
from pathlib import Path

def get_result_image_path(first_player_win: bool):
    """
    first_player_win:
        True  -> 先攻勝利（2番目に新しい画像）
        False -> 後攻勝利（最も新しい画像）
    """

    # ★ このファイル（final_result_scene_class.py）の場所
    base_dir = os.path.dirname(__file__)

    # ★ scenes/ の1つ上 = game_test/
    game_root = os.path.abspath(os.path.join(base_dir, ".."))

    # ★ outputs_estimated フォルダ
    image_dir = os.path.join(game_root, "outputs_estimated")

    if not os.path.exists(image_dir):
        print("[WARN] outputs_estimated not found:", image_dir)
        return None

    image_files = [
        f for f in os.listdir(image_dir)
        if f.startswith("shutter_") and f.endswith(".jpg")
    ]

    if not image_files:
        return None

    # ファイル名順 = 時刻順
    image_files.sort()

    if first_player_win:
        selected = image_files[-2] if len(image_files) >= 2 else image_files[-1]
    else:
        selected = image_files[-1]

    return os.path.join(image_dir, selected)


class FinalResultScene(Scene):
    def __init__(self):
        super().__init__()

        # ==============================
        # スコア読み込み
        # ==============================
        def load_total_score(filename):
            if not os.path.exists(filename):
                return 0
            total = 0
            with open(filename, "r", encoding="utf-8") as f:
                for line in f:
                    for part in line.strip().split(","):
                        if part.strip().isdigit():
                            total += int(part)
            return total

        def clear_score_file(filename):
            with open(filename, "w", encoding="utf-8") as f:
                f.write("")

        score_1p = load_total_score("1Pscores.txt")
        score_2p = load_total_score("2Pscores.txt")

        clear_score_file("1Pscores.txt")
        clear_score_file("2Pscores.txt")

        self.IS_DRAW = (score_1p == score_2p)
        self.FIRST_PLAYER_WIN = score_1p > score_2p

        # ==============================
        # 画面
        # ==============================
        self.WIDTH = 800
        self.HEIGHT = 600
        self.CENTER = (400, 300)

        self.DRAW_COLOR = (160, 80, 200)

        if self.IS_DRAW:
            self.BACKGROUND_COLOR = self.DRAW_COLOR
            self.IMAGE_FILENAME = None
            self.TEXT_STR = "DRAW"
        elif self.FIRST_PLAYER_WIN:
            self.BACKGROUND_COLOR = (255, 80, 80)
            self.IMAGE_FILENAME = get_result_image_path(first_player_win=True)
            self.TEXT_STR = "WINNER 1P!"
        else:
            self.BACKGROUND_COLOR = (80, 80, 255)
            self.IMAGE_FILENAME = get_result_image_path(first_player_win=False)
            self.TEXT_STR = "WINNER 2P!"

        # ==============================
        # パラメータ（元完全一致）
        # ==============================
        self.initial_width = 4
        self.expand_speed = 900
        self.rotation_speed = 100
        self.pause_time = 0.3
        self.FADE_DURATION = 1.0
        self.PHASE1_THRESHOLD_FACTOR = 1.1

        self.rotation_speed_fast = 720
        self.rotation_speed_slow = 5

        self.DONUT_THICKNESS = 200
        self.DONUT_MAX_RADIUS = int(math.hypot(self.WIDTH, self.HEIGHT) * 2.0)
        self.DONUT_SPEED_STABLE = self.DONUT_MAX_RADIUS / 3.2

        self.FONT_SIZE = 150
        self.TEXT_ANGLE = 12
        self.TEXT_SPEED_FAST = 2200
        self.TEXT_SPEED_SLOW = 60
        self.TEXT_SLOW_RADIUS = self.WIDTH * 0.12
        self.TEXT_START_Y = self.HEIGHT * 0.5 if self.IS_DRAW else self.HEIGHT * 0.68

        self.SHADOW_OFFSET = (6, 6)
        self.SHADOW_ALPHA = 120
        self.OUTLINE_OFFSETS = [
            (-3,0),(3,0),(0,-3),(0,3),
            (-2,-2),(2,-2),(-2,2),(2,2)
        ]

        # ==============================
        # 画像（勝利時のみ）
        # ==============================
        self.photo = None
        if self.IMAGE_FILENAME:
            photo = pygame.image.load(self.IMAGE_FILENAME).convert_alpha()
            r = min(self.WIDTH*0.45/photo.get_width(), self.HEIGHT*0.65/photo.get_height())
            self.photo = pygame.transform.smoothscale(
                photo,
                (int(photo.get_width()*r), int(photo.get_height()*r))
            )

        # ==============================
        # フォント
        # ==============================
        cur = os.path.dirname(__file__)
        main = os.path.join(cur, "../font/Paintball_Beta_3.ttf")
        self.font = pygame.font.Font(main, self.FONT_SIZE)

        base = self.font.render(self.TEXT_STR, True, (255,255,255))
        shadow = self.font.render(self.TEXT_STR, True, (0,0,0))
        shadow.set_alpha(self.SHADOW_ALPHA)

        self.text_surface = pygame.transform.rotate(base, self.TEXT_ANGLE)
        self.shadow_surface = pygame.transform.rotate(shadow, self.TEXT_ANGLE)

        self.outlines = []
        for ox, oy in self.OUTLINE_OFFSETS:
            s = self.font.render(self.TEXT_STR, True, (0,0,0))
            self.outlines.append((pygame.transform.rotate(s, self.TEXT_ANGLE), ox, oy))

        self.text_w, _ = self.text_surface.get_size()
        self.text_x = -self.text_w
        self.text_y = self.TEXT_START_Y
        self.center_target_x = (self.WIDTH - self.text_w) / 2

        rad = math.radians(self.TEXT_ANGLE)
        self.move_dx = math.cos(rad)
        self.move_dy = -math.sin(rad)

        # ==============================
        # ドーナツ
        # ==============================
        class Donut:
            def __init__(self, parent):
                self.parent = parent
                self.start_time = None
                self.active = False
                self.outer = 0
                self.inner = 0

            def start(self):
                self.start_time = time.time()
                self.active = True

            def update(self):
                if not self.active:
                    return False
                e = time.time() - self.start_time
                self.outer = int(e * self.parent.DONUT_SPEED_STABLE)
                if self.outer >= self.parent.DONUT_MAX_RADIUS:
                    self.active = False
                    return False
                self.inner = max(0, self.outer - self.parent.DONUT_THICKNESS)
                return True

        self.donut1 = Donut(self)
        self.donut2 = Donut(self)
        self.donut2_started = False

        # ==============================
        # 状態
        # ==============================
        self.phase = 1
        self.phase_start = time.time()

        self.photo_x = -self.photo.get_width() if self.photo else 0
        self.rotation_angle = 0.0

        self.current_width = self.initial_width
        self.current_angle = 0.0

        self.text_active = False
        self.text_fixed = False

    # ==============================
    # ドーナツ描画
    # ==============================
    def draw_donut(self, surface, inner, outer, alpha):
        tmp = pygame.Surface((self.WIDTH, self.HEIGHT), pygame.SRCALPHA)
        pygame.draw.circle(tmp, (255,255,255,alpha), self.CENTER, outer)
        pygame.draw.circle(tmp, (0,0,0,0), self.CENTER, inner)
        surface.blit(tmp, (0,0))

    # ==============================
    # update
    # ==============================
    def update(self, dt):
        now = time.time()
        elapsed = now - self.phase_start

        # Phase1：白線回転拡大
        if self.phase == 1:
            if elapsed < self.pause_time:
                self.current_width = self.initial_width
            else:
                t = elapsed - self.pause_time
                self.current_width = self.initial_width + self.expand_speed*t
                self.current_angle = self.rotation_speed*t
            if self.current_width >= self.WIDTH * self.PHASE1_THRESHOLD_FACTOR:
                self.phase = 2
                self.phase_start = now

        # Phase2：白 → 背景色フェード
        elif self.phase == 2:
            if elapsed >= self.FADE_DURATION:
                self.phase = 3
                self.phase_start = now

        # Phase3
        elif self.phase == 3:
            if not self.IS_DRAW:
                self.rotation_angle = self.rotation_speed_fast * elapsed
                move_ratio = min(elapsed / (360 / self.rotation_speed_fast), 1.0)
                self.photo_x = (-self.photo.get_width())*(1-move_ratio) + self.CENTER[0]*move_ratio

                if move_ratio >= 1.0:
                    self.donut1.start()
                    self.text_active = True
                    self.text_fixed = False
                    self.text_x = -self.text_w
                    self.phase = 4
                    self.phase_start = now
            else:
                # DRAW：画像移動なし、即テキスト演出へ
                self.donut1.start()
                self.text_active = True
                self.text_fixed = False
                self.text_x = -self.text_w
                self.phase = 4
                self.phase_start = now

        # Phase4
        elif self.phase == 4:
            self.rotation_angle += self.rotation_speed_slow * dt

            alive1 = self.donut1.update()
            if not alive1 and not self.donut2_started:
                self.donut2.start()
                self.donut2_started = True
            self.donut2.update()

            if not self.text_fixed:
                dist = self.center_target_x - self.text_x
                speed = (
                    self.TEXT_SPEED_FAST
                    if abs(dist) > self.TEXT_SLOW_RADIUS
                    else self.TEXT_SPEED_SLOW
                )
                self.text_x += self.move_dx * speed * dt
                self.text_y += self.move_dy * speed * dt

                if self.text_x >= self.center_target_x:
                    self.text_x = self.center_target_x
                    self.text_fixed = True

            if self.donut2_started and not self.donut2.active and self.text_fixed:
                self.phase = 5
                self.phase_start = now

        # Phase5
        elif self.phase == 5:
            if elapsed > 2.0:
                self.request_next("title")

    # ==============================
    # draw
    # ==============================
    def draw(self, surface):

        # Phase1：白線
        if self.phase == 1:
            surface.fill((0,0,0))
            diag = int(math.hypot(self.WIDTH, self.HEIGHT) * 2)
            line = pygame.Surface((max(1,int(self.current_width)), diag), pygame.SRCALPHA)
            line.fill((255,255,255))
            rot = pygame.transform.rotate(line, self.current_angle)
            surface.blit(rot, rot.get_rect(center=self.CENTER))
            return

        # Phase2：フェード
        if self.phase == 2:
            a = min((time.time()-self.phase_start)/self.FADE_DURATION, 1.0)
            col = tuple(int(255*(1-a) + c*a) for c in self.BACKGROUND_COLOR)
            surface.fill(col)
            return

        surface.fill(self.BACKGROUND_COLOR)

        # DRAW演出
        if self.IS_DRAW:
            if self.donut1.active:
                self.draw_donut(surface, self.donut1.inner, self.donut1.outer, 200)
            if self.donut2.active:
                self.draw_donut(surface, self.donut2.inner, self.donut2.outer, 200)

            surface.blit(self.shadow_surface,
                (self.text_x+self.SHADOW_OFFSET[0], self.text_y+self.SHADOW_OFFSET[1]))
            surface.blit(self.text_surface, (self.text_x, self.text_y))


        # 勝利演出（元完全再現）
        else:
            if self.phase >= 4:
                if self.donut1.active:
                    self.draw_donut(surface, self.donut1.inner, self.donut1.outer, 230)
                if self.donut2.active:
                    self.draw_donut(surface, self.donut2.inner, self.donut2.outer, 230)

            rotated = pygame.transform.rotate(self.photo, self.rotation_angle)
            rect = rotated.get_rect(center=(self.photo_x, self.CENTER[1]))
            surface.blit(rotated, rect)

            if self.text_active:
                surface.blit(self.shadow_surface,
                    (self.text_x+self.SHADOW_OFFSET[0], self.text_y+self.SHADOW_OFFSET[1]))
                for s, ox, oy in self.outlines:
                    surface.blit(s, (self.text_x+ox, self.text_y+oy))
                surface.blit(self.text_surface, (self.text_x, self.text_y))
