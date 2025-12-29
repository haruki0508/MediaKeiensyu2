# scenes/camera_scene_class.py
import os
from datetime import datetime

import pygame
from core.scene import Scene

from common import Config, Utils, game_state


class CameraScene(Scene):
    """Phase4: カメラ・撮影"""

    def __init__(self, app):
        super().__init__(app)
        self.theme = game_state.theme or "（おだい未設定）"
        self.player_turn = game_state.player_turn

        self.latest_frame = None
        self.camera_ready = False

        self.anim_timer = 0.0
        self.wait_duration = 1.0
        self.anim_duration = 2.0

        self.is_counting = False
        self.countdown_timer = Config.COUNTDOWN_SECONDS

        self.time_speed = 0.7
        self.after_shutter = False
        self.after_shutter_timer = 0.0
        self.after_shutter_delay = 0.5

        self.dummy_surf = pygame.Surface((Config.SCREEN_WIDTH, Config.SCREEN_HEIGHT))
        self.dummy_surf.fill(Config.DUMMY_BG)

        t_theme = self.renderer.render(f"おだい: {self.theme}", 40, Config.WHITE)
        self.dummy_surf.blit(
            t_theme,
            t_theme.get_rect(center=(Config.SCREEN_WIDTH // 2, Config.SCREEN_HEIGHT // 2 - 30)),
        )

        t_info = self.renderer.render("ここに カメラが うつります", 24, Config.GRAY)
        self.dummy_surf.blit(
            t_info,
            t_info.get_rect(center=(Config.SCREEN_WIDTH // 2, Config.SCREEN_HEIGHT // 2 + 30)),
        )

    def on_enter(self):
        # 再入場用リセット
        self.anim_timer = 0.0
        self.is_counting = False
        self.countdown_timer = Config.COUNTDOWN_SECONDS
        self.latest_frame = None
        self.after_shutter = False
        self.after_shutter_timer = 0.0
        self.dummy_surf.set_alpha(255)

        self.camera_ready = self.app.hardware.start_camera()
        if not self.camera_ready:
            print("Failed to start camera.")

    def on_exit(self):
        if hasattr(self.app.hardware, "release"):
            self.app.hardware.release()

    def update(self, dt):
        if not self.camera_ready:
            return

        if self.after_shutter:
            self.after_shutter_timer += dt
            if self.after_shutter_timer >= self.after_shutter_delay:
                if hasattr(self, "request_next"):
                    self.request_next("pose_estimate_multi")
                else:
                    self.next_scene = "pose_estimate_multi"
            return

        if self.anim_timer < (self.wait_duration + self.anim_duration):
            self.anim_timer += dt
        else:
            if not self.is_counting:
                self.is_counting = True

            if self.countdown_timer > 0:
                self.countdown_timer -= dt * self.time_speed

                if self.countdown_timer <= 0:
                    self.countdown_timer = 0
                    print("SHUTTER!")
                    self._capture_shutter()

    def draw(self, surface):
        self.screen = surface
        self.dummy_surf.set_alpha(255)

        # 1) カメラ映像
        if self.camera_ready:
            ret, frame = self.app.hardware.read_frame()
        else:
            ret, frame = False, None

        if ret and frame is not None:
            cv2 = self.app.hardware.cv2
            flipped = cv2.flip(frame, 1) if cv2 else frame
            self.latest_frame = flipped.copy()
            cam_surf = Utils.cvimage_to_pygame(flipped)
            cam_surf = pygame.transform.scale(cam_surf, (Config.SCREEN_WIDTH, Config.SCREEN_HEIGHT))
            self.screen.blit(cam_surf, (0, 0))
        else:
            self.screen.blit(self.dummy_surf, (0, 0))

        # 2) 蓋アニメ
        if self.anim_timer < (self.wait_duration + self.anim_duration):
            if self.anim_timer < self.wait_duration:
                self.screen.blit(self.dummy_surf, (0, 0))
            else:
                progress = (self.anim_timer - self.wait_duration) / self.anim_duration
                eased = Utils.ease_out_cubic(progress)
                self.dummy_surf.set_alpha(int(255 * (1.0 - eased)))
                scale = 1.0 - (eased * 0.8)

                nw = int(Config.SCREEN_WIDTH * scale)
                nh = int(Config.SCREEN_HEIGHT * scale)
                scaled = pygame.transform.scale(self.dummy_surf, (nw, nh))
                tx = -nw * 0.5 * eased
                ty = -nh * 0.5 * eased
                self.screen.blit(scaled, (int(tx), int(ty)))

        # 3) UI
        self._draw_ui()

    def _draw_ui(self):
        t_theme = self.renderer.render(f"おだい: {self.theme}", 24, Config.WHITE)
        t_shadow = self.renderer.render(f"おだい: {self.theme}", 24, Config.BLACK)
        self.screen.blit(t_shadow, (22, 22))
        self.screen.blit(t_theme, (20, 20))

        self._draw_turn()

        if not self.camera_ready:
            msg = self.renderer.render("カメラが見つかりません。接続を確認してください。", 24, Config.RED)
            shadow = self.renderer.render("カメラが見つかりません。接続を確認してください。", 24, Config.BLACK)
            self.screen.blit(shadow, (22, Config.SCREEN_HEIGHT - 62))
            self.screen.blit(msg, (20, Config.SCREEN_HEIGHT - 64))

        if self.is_counting and self.countdown_timer > 0:
            display_num = int(self.countdown_timer) + 1
            progress = self.countdown_timer - int(self.countdown_timer)

            alpha = int(255 * (progress**0.5))
            scale = 1.0 + (1.0 - progress) * 0.8
            base_size = 500

            t_timer = self.renderer.render(str(display_num), base_size, Config.RED)
            new_w = int(t_timer.get_width() * scale)
            new_h = int(t_timer.get_height() * scale)

            if new_w < Config.SCREEN_WIDTH * 3:
                t_timer_scaled = pygame.transform.smoothscale(t_timer, (new_w, new_h))
                t_timer_scaled.set_alpha(alpha)
                cx = (Config.SCREEN_WIDTH - new_w) // 2
                cy = (Config.SCREEN_HEIGHT - new_h) // 2
                self.screen.blit(t_timer_scaled, (cx, cy))

    def _capture_shutter(self):
        if not self.camera_ready:
            print("Camera not ready, skip shutter.")
            return
        if self.latest_frame is None:
            print("No frame available to save.")
            return
        cv2 = self.app.hardware.cv2
        if not cv2:
            print("OpenCV not available, cannot save frame.")
            return

        try:
            os.makedirs(Config.PATH_SHUTTER_DIR, exist_ok=True)
        except OSError as e:
            print(f"Failed to create directory '{Config.PATH_SHUTTER_DIR}': {e}")
            return

        filename = datetime.now().strftime("shutter_%Y%m%d_%H%M%S_%f.jpg")
        save_path = os.path.join(Config.PATH_SHUTTER_DIR, filename)

        ok = False
        try:
            # Use imencode to support non-ASCII paths on Windows
            ext = os.path.splitext(save_path)[1] or ".jpg"
            enc_ok, buf = cv2.imencode(ext, self.latest_frame)
            if enc_ok:
                buf.tofile(save_path)
                ok = True
        except Exception as e:
            print(f"Failed to save shutter frame via imencode: {e}")

        if not ok:
            ok = cv2.imwrite(save_path, self.latest_frame)

        if ok:
            print(f"Saved shutter frame: {save_path}")
            game_state.last_shutter_path = save_path
        else:
            print(f"Failed to save shutter frame: {save_path}")

        self.after_shutter = True

    def _draw_turn(self):
        bx, by = 20, 65
        bw, bh = 80, 35

        p1 = pygame.Surface((bw, bh))
        p1.fill(Config.RED)
        t1 = self.renderer.render("せんこう", 20, Config.WHITE)
        p1.blit(t1, t1.get_rect(center=(bw // 2, bh // 2)))

        p2 = pygame.Surface((bw, bh))
        p2.fill(Config.BLUE)
        t2 = self.renderer.render("こうこう", 20, Config.WHITE)
        p2.blit(t2, t2.get_rect(center=(bw // 2, bh // 2)))

        if self.player_turn == 1:
            p1.set_alpha(255)
            p2.set_alpha(80)
            pygame.draw.rect(p1, Config.WHITE, (0, 0, bw, bh), 2)
        else:
            p1.set_alpha(80)
            p2.set_alpha(255)
            pygame.draw.rect(p2, Config.WHITE, (0, 0, bw, bh), 2)

        self.screen.blit(p1, (bx, by))
        self.screen.blit(p2, (bx + bw + 10, by))
