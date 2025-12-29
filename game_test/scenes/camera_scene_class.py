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
        self.allow_second_shot = self.player_turn == 1

        self.latest_frame = None
        self.camera_ready = False

        self.anim_timer = 0.0
        self.wait_duration = 1.0
        self.anim_duration = 2.0

        self.is_counting = False
        self.first_countdown_seconds = 5.0
        self.second_countdown_seconds = 5.0
        self.interval_seconds = 4.0
        self.second_start_pause = 0.5
        self.second_pause_timer = 0.0
        self.countdown_timer = self.first_countdown_seconds
        self.interval_timer = 0.0
        self.phase = "first_countdown"

        self.time_speed = 1.0
        self.after_shutter = False
        self.after_shutter_timer = 0.0
        self.after_shutter_delay = 0.5
        self.shutter_anim_duration = 0.6
        self.shutter_anim_timer = 0.0
        self.shutter_anim_active = False

        self.dummy_surf = pygame.Surface((Config.SCREEN_WIDTH, Config.SCREEN_HEIGHT))
        self.dummy_surf.fill(Config.DUMMY_BG)

        self.interval_surf = pygame.Surface((Config.SCREEN_WIDTH, Config.SCREEN_HEIGHT))
        self.interval_surf.fill(Config.DARK_BLUE)

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
        self.player_turn = game_state.player_turn
        self.allow_second_shot = self.player_turn == 1
        self.countdown_timer = self.first_countdown_seconds
        self.interval_timer = 0.0
        self.second_pause_timer = 0.0
        self.phase = "first_countdown"
        self.latest_frame = None
        self.after_shutter = False
        self.after_shutter_timer = 0.0
        self.dummy_surf.set_alpha(255)
        game_state.shutter_paths = []
        self.shutter_anim_timer = 0.0
        self.shutter_anim_active = False

        self.camera_ready = self.app.hardware.start_camera()
        if not self.camera_ready:
            print("Failed to start camera.")

    def on_exit(self):
        if hasattr(self.app.hardware, "release"):
            self.app.hardware.release()

    def update(self, dt):
        if not self.camera_ready:
            return

        if self.shutter_anim_active:
            self.shutter_anim_timer += dt
            if self.shutter_anim_timer >= self.shutter_anim_duration:
                self.shutter_anim_active = False

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
            return

        if self.phase == "after_first_shutter":
            if not self.shutter_anim_active:
                self._start_interval()
            return

        if self.phase == "interval":
            self.interval_timer -= dt
            if self.interval_timer <= 0:
                self._start_second_pause()
            return

        if self.phase == "second_pause":
            self.second_pause_timer -= dt
            if self.second_pause_timer <= 0:
                self._start_second_shot()
            return

        if not self.is_counting:
            self.is_counting = True

        if self.countdown_timer > 0:
            self.countdown_timer -= dt * self.time_speed

            if self.countdown_timer <= 0:
                self.countdown_timer = 0
                print("SHUTTER!")
                if self.phase == "first_countdown":
                    if self.allow_second_shot:
                        self._capture_shutter(final_shot=False)
                        self.phase = "after_first_shutter"
                    else:
                        self._capture_shutter(final_shot=True)
                elif self.phase == "second_countdown":
                    self._capture_shutter(final_shot=True)

    def draw(self, surface):
        self.screen = surface
        self.dummy_surf.set_alpha(255)

        if self.phase == "interval":
            self.screen.blit(self.interval_surf, (0, 0))
            self._draw_ui()
            self._draw_shutter_effect()
            return

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
        self._draw_shutter_effect()

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

        if self.phase == "interval":
            msg = self.renderer.render("つぎは こうこう の さつえい", 32, Config.WHITE)
            shadow = self.renderer.render("つぎは こうこう の さつえい", 32, Config.BLACK)
            rect = msg.get_rect(center=(Config.SCREEN_WIDTH // 2, Config.SCREEN_HEIGHT - 80))
            self.screen.blit(shadow, rect.move(2, 2))
            self.screen.blit(msg, rect)
            if self.interval_timer > 0:
                ratio = max(0.0, min(1.0, 1.0 - (self.interval_timer / self.interval_seconds)))
                bar_w = int(Config.SCREEN_WIDTH * 0.7)
                bar_h = 22
                bar_x = (Config.SCREEN_WIDTH - bar_w) // 2
                bar_y = (Config.SCREEN_HEIGHT // 2) + 80
                pygame.draw.rect(self.screen, Config.BLACK, (bar_x - 3, bar_y - 3, bar_w + 6, bar_h + 6))
                pygame.draw.rect(self.screen, Config.GRAY, (bar_x, bar_y, bar_w, bar_h))
                pygame.draw.rect(
                    self.screen,
                    Config.YELLOW,
                    (bar_x, bar_y, int(bar_w * ratio), bar_h),
                )

        if self.phase in ("first_countdown", "second_countdown") and self.is_counting and self.countdown_timer > 0:
            display_num = int(self.countdown_timer) + 1
            progress = self.countdown_timer - int(self.countdown_timer)

            alpha = int(255 * (progress**0.5))
            scale = 1.0 + (1.0 - progress) * 0.8
            base_size = 500

            timer_color = Config.BLUE if self.phase == "second_countdown" else Config.RED
            t_timer = self.renderer.render(str(display_num), base_size, timer_color)
            new_w = int(t_timer.get_width() * scale)
            new_h = int(t_timer.get_height() * scale)

            if new_w < Config.SCREEN_WIDTH * 3:
                t_timer_scaled = pygame.transform.smoothscale(t_timer, (new_w, new_h))
                t_timer_scaled.set_alpha(alpha)
                cx = (Config.SCREEN_WIDTH - new_w) // 2
                cy = (Config.SCREEN_HEIGHT - new_h) // 2
                self.screen.blit(t_timer_scaled, (cx, cy))

    def _capture_shutter(self, final_shot=True):
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
        self.shutter_anim_active = True
        self.shutter_anim_timer = 0.0
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
            game_state.shutter_paths.append(save_path)
        else:
            print(f"Failed to save shutter frame: {save_path}")

        if final_shot:
            self.after_shutter = True

    def _start_interval(self):
        self.phase = "interval"
        self.interval_timer = self.interval_seconds
        self.is_counting = False
        self.player_turn = 2
        game_state.player_turn = 2

    def _start_second_shot(self):
        self.phase = "second_countdown"
        self.player_turn = 2
        game_state.player_turn = 2
        self.is_counting = True
        self.countdown_timer = self.second_countdown_seconds
        self.anim_timer = self.wait_duration + self.anim_duration

    def _start_second_pause(self):
        self.phase = "second_pause"
        self.second_pause_timer = self.second_start_pause
        self.is_counting = False

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

    def _draw_shutter_effect(self):
        if not self.shutter_anim_active:
            return

        progress = min(1.0, self.shutter_anim_timer / self.shutter_anim_duration)
        radius_scale = abs((progress * 2.0) - 1.0)
        radius = int(max(Config.SCREEN_WIDTH, Config.SCREEN_HEIGHT) * (0.2 + 0.8 * radius_scale))
        center_x = Config.SCREEN_WIDTH // 2
        center_y = Config.SCREEN_HEIGHT // 2
        blade_width = 0.6
        rotation = progress * 3.14

        overlay = pygame.Surface((Config.SCREEN_WIDTH, Config.SCREEN_HEIGHT), pygame.SRCALPHA)
        blade_color = (0, 0, 0, 240)
        for i in range(6):
            angle = rotation + (i * 1.047)
            ax = center_x + int(radius * pygame.math.Vector2(1, 0).rotate_rad(angle - blade_width).x)
            ay = center_y + int(radius * pygame.math.Vector2(1, 0).rotate_rad(angle - blade_width).y)
            bx = center_x + int(radius * pygame.math.Vector2(1, 0).rotate_rad(angle + blade_width).x)
            by = center_y + int(radius * pygame.math.Vector2(1, 0).rotate_rad(angle + blade_width).y)
            pygame.draw.polygon(overlay, blade_color, [(center_x, center_y), (ax, ay), (bx, by)])
        pygame.draw.circle(overlay, blade_color, (center_x, center_y), int(radius * 0.1))

        self.screen.blit(overlay, (0, 0))
