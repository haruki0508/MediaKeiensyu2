# common.py
import os
import random
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime

import pygame


# ====================================================
# Shared State: シーン間で引き継ぐ値
# ====================================================
@dataclass
class GameState:
    theme: str = ""
    player_turn: int = 1
    shutter_paths: list[str] = field(default_factory=list)


game_state = GameState()


# ====================================================
# 1. Config: 設定・定数管理 (Magic Numberの排除)
# ====================================================
class Config:
    # 画面設定
    SCREEN_WIDTH = 800
    SCREEN_HEIGHT = 600
    FPS = 60
    CAPTION = "Pose Battle Game - Refactored"

    # パス設定 (絶対パス)
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    HARUKI_ASSET_DIR = os.path.join(BASE_DIR, "..", "haruki's program")
    PATH_FONT_IOEI = os.path.join(BASE_DIR, "font", "IoEI.ttf")
    PATH_FONT_PAINTBALL = os.path.join(BASE_DIR, "font", "Paintball_Beta_3.ttf")
    PATH_IMG_BOMB = os.path.join(HARUKI_ASSET_DIR, "bakudan-white.JPG")
    PATH_SHUTTER_DIR = os.path.join(BASE_DIR, "shuttered")

    # 色定義
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    RED = (255, 50, 50)
    BLUE = (50, 50, 255)
    GRAY = (100, 100, 100)
    ORANGE = (255, 165, 0)
    YELLOW = (255, 255, 0)
    DUMMY_BG = (50, 50, 50)

    # ★追加: 未定義だった色
    LIGHT_BLUE = (120, 180, 255)
    DARK_BLUE = (70, 120, 200)

    # ゲームパラメータ
    ROULETTE_ITEM_HEIGHT = 110
    ROULETTE_SPIN_MIN = 1.5
    ROULETTE_SPIN_MAX = 3.0
    FUSE_DURATION = 3.0
    COUNTDOWN_SECONDS = 5.0

    # お題リスト
    THEMES = [
        "グリコ",
        "かんがえるひと",
        "シェー",
        "かめはめは",
        "ジョジョだち",
        "ダブルピース",
        "どげざ",
        "コマネチ",
        "いのち",
        "ごろうまる",
    ]

    # ==================================================
    # 以下はチュートリアル版（Phase2）にあったレイアウト設定
    # ==================================================
    PATH_IMG_BOMB_GRAY = os.path.join(HARUKI_ASSET_DIR, "bakudan-gray.JPG")
    PATH_CHAR_RED = os.path.join(HARUKI_ASSET_DIR, "char_red.jpg")
    PATH_CHAR_BLUE = os.path.join(HARUKI_ASSET_DIR, "char_blue.jpg")

    CREAM = (255, 250, 220)
    FUSE_BROWN = (80, 60, 40)

    PHASE2_TITLE_Y = 60
    PHASE2_TITLE_BG_HEIGHT = 70
    PHASE2_MONITOR_Y = 150
    PHASE2_MONITOR_MARGIN = 40
    PHASE2_LABEL_OFFSET_Y = -20
    PHASE2_ARROW_OFFSET_Y = 0
    PHASE2_FOOTER_HEIGHT = 120

    MINI_BOMB_Y = 40
    MINI_FUSE_OFFSET_Y = -10
    MINI_FUSE_THICKNESS = 1
    MINI_FUSE_START_X = 40
    MINI_FUSE_END_X = 270
    MINI_BOX_WIDTH = 200
    MINI_BOX_HEIGHT = 50
    MINI_ROULETTE_OFFSET_Y = 15


# ====================================================
# 2. Utils: 便利関数群 (Easingなど)
# ====================================================
class Utils:
    @staticmethod
    def cvimage_to_pygame(image):
        """OpenCV(BGR)画像をPygame(RGB)画像に変換"""
        import cv2

        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        height, width = image_rgb.shape[:2]
        return pygame.image.frombuffer(image_rgb.tobytes(), (width, height), "RGB")

    @staticmethod
    def ease_out_cubic(x):
        """イージング関数: 急速に始まり、ゆっくり終わる"""
        return 1 - pow(1 - x, 3)


# ====================================================
# 3. Managers: リソース・テキスト・ハードウェア
# ====================================================
class ResourceManager:
    """リソース管理とフォールバック処理"""

    def __init__(self):
        self.fonts_ioei = {}
        self.fonts_paintball = {}
        self.fonts_system = {}

        # 優先: 白爆弾（元の game1.py）
        self.bomb_img = self._load_image(
            Config.PATH_IMG_BOMB, size=(100, 100), transparent=True
        )

        # チュートリアル用（存在しないなら None）
        self.bomb_img_gray = self._load_image(
            Config.PATH_IMG_BOMB_GRAY, size=(100, 100), transparent=False
        )
        self.char_red = self._load_image(
            Config.PATH_CHAR_RED, target_height=190, transparent=True
        )
        self.char_blue = self._load_image(
            Config.PATH_CHAR_BLUE, target_height=190, transparent=True
        )

        self._check_files()

    def _check_files(self):
        print("--- Resource Check ---")
        for name, path in [
            ("Paintball", Config.PATH_FONT_PAINTBALL),
            ("IoEI", Config.PATH_FONT_IOEI),
            ("Bomb(white)", Config.PATH_IMG_BOMB),
            ("Bomb(gray)", Config.PATH_IMG_BOMB_GRAY),
            ("CharRed", Config.PATH_CHAR_RED),
            ("CharBlue", Config.PATH_CHAR_BLUE),
        ]:
            status = "OK" if os.path.exists(path) else "MISSING"
            print(f"[{status}] {name}: {path}")
        print("----------------------")

    def _load_image(self, path, size=None, target_height=None, transparent=False):
        try:
            if not os.path.exists(path):
                return None
            loaded = pygame.image.load(path)

            # 透過指定: アルファ有なら尊重。無ければ左上色を抜く
            has_alpha = loaded.get_alpha() is not None or loaded.get_masks()[3] != 0
            if transparent and has_alpha:
                img = loaded.convert_alpha()
            else:
                img = loaded.convert()
                if transparent:
                    colorkey = img.get_at((0, 0))
                    img.set_colorkey(colorkey, pygame.RLEACCEL)

            if size:
                img = pygame.transform.scale(img, size)
            elif target_height:
                rect = img.get_rect()
                ratio = target_height / rect.height
                new_width = int(rect.width * ratio)
                img = pygame.transform.scale(img, (new_width, target_height))
            return img
        except Exception:
            return None

    def get_font_object(self, path, size, cache_dict, fallback_sysfont="meiryo"):
        """フォント取得（キャッシュ＆フォールバック付き）"""
        if size in cache_dict:
            return cache_dict[size]

        try:
            font = pygame.font.Font(path, size)
        except OSError:
            print(f"Warning: Font {path} not found. Using fallback '{fallback_sysfont}'.")
            try:
                font = pygame.font.SysFont(fallback_sysfont, size)
            except Exception:
                font = pygame.font.Font(None, int(size * 1.5))

        cache_dict[size] = font
        return font

    def get_system_font(self, size, bold=False):
        key = (size, bold)
        if key in self.fonts_system:
            return self.fonts_system[key]
        try:
            font = pygame.font.SysFont("meiryo", size, bold=bold)
        except Exception:
            font = pygame.font.Font(None, size)
            font.set_bold(bold)
        self.fonts_system[key] = font
        return font


class TextRenderer:
    """文字単位でフォントを切り替えて合成描画するクラス"""

    def __init__(self, resource_manager: ResourceManager):
        self.rm = resource_manager

    def is_ascii_symbol_or_digit(self, ch):
        return re.match(r"^[a-zA-Z0-9\s\.\:\!\-]+$", ch) is not None

    def render(self, text, size, color):
        if text == "":
            return pygame.Surface((0, 0), pygame.SRCALPHA)

        font_ioei = self.rm.get_font_object(
            Config.PATH_FONT_IOEI, size, self.rm.fonts_ioei, "meiryo"
        )
        font_paint = self.rm.get_font_object(
            Config.PATH_FONT_PAINTBALL, size, self.rm.fonts_paintball, "impact"
        )

        glyphs = []
        total_width = 0
        max_height = 0

        for ch in text:
            target_font = font_paint if self.is_ascii_symbol_or_digit(ch) else font_ioei
            g_surf = target_font.render(ch, True, color)
            w, h = g_surf.get_size()
            glyphs.append(g_surf)
            total_width += w
            max_height = max(max_height, h)

        surface = pygame.Surface((total_width, max_height), pygame.SRCALPHA)
        x = 0
        for g_surf in glyphs:
            h = g_surf.get_height()
            surface.blit(g_surf, (x, max_height - h))
            x += g_surf.get_width()

        return surface

    def render_system(self, text, size, color, bold=False):
        font = self.rm.get_system_font(size, bold=bold)
        return font.render(text, True, color)


class HardwareManager:
    """カメラとMediaPipeの管理（自動検出＆エラーハンドリング）"""

    def __init__(self):
        self.cap = None
        self.cv2 = None
        self.mp_pose = None
        self.pose = None
        self.mp_drawing = None
        self.draw_spec = None

    def start_camera(self):
        if self.cap is not None and self.cap.isOpened():
            return True

        try:
            import cv2
            import mediapipe as mp
        except ImportError as e:
            print(f"Camera dependencies missing: {e}")
            return False

        self.cv2 = cv2
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            enable_segmentation=False,
            min_detection_confidence=0.5,
        )
        self.mp_drawing = mp.solutions.drawing_utils
        self.draw_spec = self.mp_drawing.DrawingSpec(
            color=(0, 255, 0), thickness=2, circle_radius=2
        )

        print("Searching for camera...")
        preferred_flags = [self.cv2.CAP_DSHOW, None] if sys.platform.startswith("win") else [None]

        for cam_id in range(4):
            for flag in preferred_flags:
                cap = self.cv2.VideoCapture(cam_id, flag) if flag is not None else self.cv2.VideoCapture(cam_id)
                backend_name = "CAP_DSHOW" if flag == self.cv2.CAP_DSHOW else "default"
                if cap.isOpened():
                    print(f"Camera found at index {cam_id} (backend: {backend_name})")
                    self.cap = cap
                    self.cap.set(self.cv2.CAP_PROP_FRAME_WIDTH, Config.SCREEN_WIDTH)
                    self.cap.set(self.cv2.CAP_PROP_FRAME_HEIGHT, Config.SCREEN_HEIGHT)
                    return True
                cap.release()

        print("Error: No working camera found.")
        return False

    def read_frame(self):
        if self.cap:
            ret, frame = self.cap.read()
            return ret, frame
        return False, None

    def process_pose(self, frame):
        if frame is None:
            return None
        if not self.cv2 or not self.pose:
            return frame

        frame.flags.writeable = False
        image_rgb = self.cv2.cvtColor(frame, self.cv2.COLOR_BGR2RGB)
        results = self.pose.process(image_rgb)
        frame.flags.writeable = True

        if results.pose_landmarks:
            self.mp_drawing.draw_landmarks(
                image=frame,
                landmark_list=results.pose_landmarks,
                connections=self.mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=self.draw_spec,
                connection_drawing_spec=self.draw_spec,
            )
        return frame

    def release(self):
        if self.cap:
            self.cap.release()
            self.cap = None


# ====================================================
# 4. AppContext: core側を触らずに、必要な依存をまとめる
# ====================================================
class AppContext:
    """
    core/manager.py が渡してくる app の代わりに、
    game_main.py 側で組み立てて scenes に渡すことを想定。
    """
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.resource_manager = ResourceManager()
        self.text_renderer = TextRenderer(self.resource_manager)
        self.hardware = HardwareManager()
