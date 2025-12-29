import pygame
from core.manager import SceneManager
from scenes.title_scene_class import TitleScene
from scenes.pose_scene import PoseEstimationScene
from scenes.ex_game_scene_class import ExGameScene      ##例（本番は使わない）
from scenes.ex_result_scene_class import ExResultScene  ##例（本番は使わない）
##ここに自分のクラス名とファイル名を追加してください！
from scenes.score_screen import ScoreScene
from common import AppContext, game_state

from scenes.howto_scene_class import HowToScene
from scenes.roulette_scene_class import RouletteScene
from scenes.camera_scene_class import CameraScene

from scenes.round_result_scene_class import RoundResultScene
from scenes.final_result_scene_class import FinalResultScene


def create_scene_factory(app):
    def create_scene(name: str):
        ##ここに自分のクラス名とシーン名を追加してください！
        ##シーンの順番通りに並んでると、わかりやすくて嬉しいです！
        ##request_nextで指定する文字列はここを参照！
        """名前→シーンの生成（Factory）"""
        
        # タイトル
        if name == "title":
            return TitleScene()

        # 工藤が追加
        # ルール説明
        elif name == "howto":
            return HowToScene(app)
        # お題決め
        elif name == "roulette":
            return RouletteScene(app)
        # 撮影
        elif name == "camera":
            return CameraScene(app)
        
        # 車戸が追加
        # ポーズ推定
        elif name == "pose_estimate_multi":
            #image_dir = Path("game_test/assets/images")    # 実在するフォルダに合わせる
            #save_dir  = Path("game_test/output")          # 書き込み可能なフォルダに合わせる
            #next_scene_name = "title"
            
            image_list = [
                        ##ここに画像ファイルを追加してください！->下のif文で最新の撮影画像も追加されます
                        "pose_examples/pose_example.jpg",
                        "pose_examples/pose_example2.jpg"
                    ]

            if game_state.last_shutter_path: # 最新の撮影画像を追加
                image_list.append(game_state.last_shutter_path)

            return PoseEstimationScene(app, image_paths=image_list, on_black=True, save_dir="game_test/outputs_estimated")
        
        # モデルを使って得点を計算するファイルが必要？

        # 得点中間発表 
        elif name == "score":
            return ScoreScene()
        
        # 川島が追加
        # 細かい点数発表(得点中間発表の前？)
        elif name == "round_result":
            return RoundResultScene()
        # 最終結果発表
        elif name == "final_result":
            return FinalResultScene()

        # 例（本番は使わない）
        elif name == "ex_game":
            return ExGameScene()
        elif name == "ex_result":
            return ExResultScene()

        else:
            raise ValueError(f"Unknown scene name: {name}")

    return create_scene

def main():
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    clock = pygame.time.Clock()

    app = AppContext(screen)
    manager = SceneManager(
        initial_scene=TitleScene(),
        scene_factory=create_scene_factory(app),
    )

    
    #scene = PoseEstimationScene(app=None, image_path="pose_examples/", on_black=True)
    #scene.on_enter()


    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        running = manager.run_frame(screen, dt)
        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
