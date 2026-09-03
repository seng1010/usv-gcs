# -*- coding: utf-8 -*-
# usv_gui(DONGWON21)의 tkinter 데스크톱 프로토타입 원본. web/ 아래 index.html+script.js로
# 대체되었지만 참고용으로 보존. ROS2 빌드/실행 경로에는 포함되지 않음.
import tkinter as tk
from tkinter import messagebox
import random
import os
import math
from PIL import Image, ImageTk

# 📂 현재 파이썬 파일이 위치한 경로를 기준으로 자동 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class RealPixelArtBoatGame:
    def __init__(self, root, return_to_main_callback):
        self.root = root
        self.return_to_main = return_to_main_callback
        self.root.title("Pixel Art Boat Simulator v23.2 - Fast Keyboard Edition")
        self.root.geometry("800x600") 
        self.root.resizable(False, False)

        # 🎯 목표 시스템 상태 변수 (90초 플레이 타임 기준 최적화)
        self.initial_time = 90  
        self.time_limit = self.initial_time  
        self.target_score = 10000 
        self.is_game_over = False

        self.cheat_click_count = 0
        self.water_quality = 70.0
        self.max_water_quality = 100.0

        self.gold = 300  
        self.score = 0
        self.fish_count = 4  
        self.owned_special_fishes = {"witch": 0, "ghost": 0, "santa": 0, "pumpkin": 0}
        self.ghost_gold_timer = 0 

        # 🗺️ 통짜 맵 전체 크기 정의 (1140 x 1200)
        self.map_width = 1140
        self.map_height = 1200
        
        # 보트의 맵 내 절대 좌표 (초기 위치: 중앙 부근)
        self.target_x = 570
        self.target_y = 600
        self.boat_angle = 0.0  
        self.is_pumping = False 
        
        # 키보드 입력 상태 저장용 딕셔너리
        self.key_states = {"w": False, "a": False, "s": False, "d": False, "shift": False}
        
        self.monsters = []
        self.monster_spawn_timer = 0

        self.message_hide_timer = None
        self.active_card_shown = False
        self.card_auto_close_timer = None

        self.canvas = tk.Canvas(self.root, width=800, height=600, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.SPECIAL_FISH_TEMPLATES = {
            "witch": {"idx": 1, "name": "WITCH FISH", "kor_name": "마녀 피쉬", "price": 90, "score_val": 15, "desc": "쓰레기 패널티 30% 완화 🎩"},
            "ghost": {"idx": 19, "name": "GHOST LOBSTER", "kor_name": "유령 가재", "price": 130, "score_val": 25, "desc": "10초마다 +15G 생산 👻"},
            "santa": {"idx": 28, "name": "SANTA GOLDFISH", "kor_name": "산타 금붕어", "price": 170, "score_val": 35, "desc": "적정 수질 시 점수 1.4배 🎅"},
            "pumpkin": {"idx": 54, "name": "PUMPKIN FISH", "kor_name": "호박 왕관피쉬", "price": 220, "score_val": 50, "desc": "초당 기본 점수 든든하게 +50점 👑"}
        }

        self.load_pixel_assets()
        self.load_and_slice_ai_cards()
        
        self.fishes = []
        for _ in range(self.fish_count): self.spawn_random_normal_fish()

        self.setup_ui()
        self.setup_bindings()
        
        self.update_game_logic()
        self.animate_sub_engine()

    def setup_bindings(self):
        # 키보드 입력 및 상점 버튼 바인딩
        self.root.bind("<KeyPress>", self.handle_key_press)
        self.root.bind("<KeyRelease>", self.handle_key_release)

        self.canvas.tag_bind("buy_witch", "<Button-1>", lambda e: self.buy_special_fish("witch"))
        self.canvas.tag_bind("buy_ghost", "<Button-1>", lambda e: self.buy_special_fish("ghost"))
        self.canvas.tag_bind("buy_santa", "<Button-1>", lambda e: self.buy_special_fish("santa"))
        self.canvas.tag_bind("buy_pumpkin", "<Button-1>", lambda e: self.buy_special_fish("pumpkin"))
        self.canvas.tag_bind("card_layer", "<Button-1>", lambda e: self.hide_fish_card_popup())
        self.canvas.tag_bind("cheat_box", "<Button-1>", self.trigger_ending_cheat)

    def handle_key_press(self, event):
        if self.is_game_over: return
        key = event.keysym.lower()
        if key in ["w", "z"]: 
            self.key_states["w"] = True
        elif key in ["a", "q"]: 
            self.key_states["a"] = True
        elif key == "s": 
            self.key_states["s"] = True
        elif key == "d": 
            self.key_states["d"] = True
        elif "shift" in key:
            self.key_states["shift"] = True
            self.is_pumping = True

    def handle_key_release(self, event):
        key = event.keysym.lower()
        if key in ["w", "z"]: 
            self.key_states["w"] = False
        elif key in ["a", "q"]: 
            self.key_states["a"] = False
        elif key == "s": 
            self.key_states["s"] = False
        elif key == "d": 
            self.key_states["d"] = False
        elif "shift" in key:
            self.key_states["shift"] = False
            self.is_pumping = False

    def find_file_path(self, filename):
        path = os.path.join(BASE_DIR, filename)
        if os.path.exists(path):
            return path
        return None

    def load_pixel_assets(self):
        lake_path = self.find_file_path("lake.png")
        if lake_path:
            try:
                img = Image.open(lake_path).convert("RGBA").resize((1140, 1200), Image.Resampling.LANCZOS)
                self.full_map_image = ImageTk.PhotoImage(img)
                mini_img = img.resize((130, 137), Image.Resampling.LANCZOS)
                self.minimap_base_image = ImageTk.PhotoImage(mini_img)
            except Exception:
                self.full_map_image = None
                self.minimap_base_image = None
        
        if not self.full_map_image:
            fallback_bg = Image.new("RGBA", (1140, 1200), (40, 120, 180, 255))
            self.full_map_image = ImageTk.PhotoImage(fallback_bg)
            fallback_mini = Image.new("RGBA", (130, 137), (40, 120, 180, 255))
            self.minimap_base_image = ImageTk.PhotoImage(fallback_mini)

        ending_path = self.find_file_path("ending.png")
        if ending_path:
            try:
                ending_raw = Image.open(ending_path).convert("RGBA")
                ending_resized = ending_raw.resize((800, 600), Image.Resampling.LANCZOS)
                self.ending_photo = ImageTk.PhotoImage(ending_resized)
            except Exception:
                self.ending_photo = None
        else:
            self.ending_photo = None

        ship_path = self.find_file_path("ship.jpg") or self.find_file_path("ship.png")
        self.boat_photos = []
        if ship_path:
            try:
                sheet = Image.open(ship_path).convert("RGBA")
                datas = sheet.getdata()
                new_data = []
                for item in datas:
                    if item[0] > 230 and item[1] > 230 and item[2] > 230:
                        new_data.append((255, 255, 255, 0))
                    else:
                        new_data.append(item)
                sheet.putdata(new_data)
                sw, sh = sheet.size
                frame_w = sw // 16
                for i in range(16):
                    frame = sheet.crop((i * frame_w, 0, (i + 1) * frame_w, sh))
                    frame_resized = frame.resize((54, 54), Image.Resampling.NEAREST)
                    self.boat_photos.append(ImageTk.PhotoImage(frame_resized))
            except Exception: pass

        if not self.boat_photos:
            fallback_boat = Image.new("RGBA", (48, 48), (200, 100, 50, 255))
            self.boat_photos = [ImageTk.PhotoImage(fallback_boat)] * 16

        fish_sheet_path = self.find_file_path("PixelFishes.png")
        self.fish_photos_right, self.fish_photos_left = [], []
        if fish_sheet_path:
            fish_sheet = Image.open(fish_sheet_path).convert("RGBA")
            cols, rows = 9, 8
            sheet_w, sheet_h = fish_sheet.size
            cell_w, cell_h = sheet_w / cols, sheet_h / rows
            for r in range(rows):
                for c in range(cols):
                    left, top = int(c * cell_w), int(r * cell_h)
                    right, bottom = int((c + 1) * cell_w), int((r + 1) * cell_h)
                    fish_crop = fish_sheet.crop((left, top, right, bottom))
                    if fish_crop.getbbox():
                        fish_scaled_r = fish_crop.resize((24, 24), Image.Resampling.NEAREST)
                        fish_scaled_l = fish_scaled_r.transpose(Image.FLIP_LEFT_RIGHT)
                        self.fish_photos_right.append(ImageTk.PhotoImage(fish_scaled_r))
                        self.fish_photos_left.append(ImageTk.PhotoImage(fish_scaled_l))
        
        if not self.fish_photos_right:
            temp_fish = Image.new("RGBA", (24, 24), (255, 200, 0, 255))
            tk_f = ImageTk.PhotoImage(temp_fish)
            self.fish_photos_right = [tk_f]
            self.fish_photos_left = [tk_f]

        arrow_path = self.find_file_path("Water Arrow Preview.gif")
        self.water_arrow_frames = []
        if arrow_path:
            try:
                gif_img = Image.open(arrow_path)
                try:
                    while True:
                        frame = gif_img.copy().convert("RGBA")
                        datas = frame.getdata()
                        new_data = []
                        for item in datas:
                            if item[0] < 30 and item[1] < 30 and item[2] < 30:
                                new_data.append((0, 0, 0, 0))
                            else: 
                                new_data.append(item)
                        frame.putdata(new_data)
                        resized_frame = frame.resize((140, 50), Image.Resampling.NEAREST)
                        self.water_arrow_frames.append(resized_frame)
                        gif_img.seek(len(self.water_arrow_frames))
                except EOFError:
                    pass
            except Exception:
                pass
        
        if not self.water_arrow_frames:
            fallback_gif = Image.new("RGBA", (140, 50), (0, 180, 252, 255))
            self.water_arrow_frames.append(fallback_gif)

        garbage_filenames = ["garbage bag 1.png", "garbage bag 2.png", "garbage bag small 1.png", "garbage bag small 2.png", "garbage bag small 3.png"]
        self.garbage_photos = []
        for g_file in garbage_filenames:
            g_path = self.find_file_path(g_file)
            if g_path:
                try:
                    img = Image.open(g_path).convert("RGBA").resize((28, 28), Image.Resampling.NEAREST)
                    self.garbage_photos.append(ImageTk.PhotoImage(img))
                except Exception: pass
        if not self.garbage_photos:
            fallback = Image.new("RGBA", (28, 28), (120, 120, 120, 255))
            self.garbage_photos.append(ImageTk.PhotoImage(fallback))

    def load_and_slice_ai_cards(self):
        self.ai_card_images = {}
        target_path = self.find_file_path("4fish.png")
        if target_path:
            try:
                full_img = Image.open(target_path).convert("RGBA")
                w, h = full_img.size
                mid_x, mid_y = w // 2, h // 2
                crop_boxes = {"witch": (0, 0, mid_x, mid_y), "ghost": (mid_x, 0, w, mid_y), "santa": (0, mid_y, mid_x, h), "pumpkin": (mid_x, mid_y, w, h)}
                for key, box in crop_boxes.items():
                    cropped = full_img.crop(box)
                    cropped.thumbnail((180, 180), Image.Resampling.LANCZOS)
                    self.ai_card_images[key] = ImageTk.PhotoImage(cropped)
                return
            except Exception: pass
        for key in ["witch", "ghost", "santa", "pumpkin"]:
            fallback = Image.new("RGBA", (180, 180), (30, 20, 15, 255))
            self.ai_card_images[key] = ImageTk.PhotoImage(fallback)

    def spawn_random_normal_fish(self):
        special_indices = [info["idx"] for info in self.SPECIAL_FISH_TEMPLATES.values()]
        available_indices = [i for i in range(len(self.fish_photos_right)) if i not in special_indices]
        if not available_indices: available_indices = [0]
        fish_type_index = random.choice(available_indices)
        self.fishes.append({
            "x": random.randint(100, self.map_width - 100), 
            "y": random.randint(100, self.map_height - 100), 
            "dir": random.choice([-1, 1]), 
            "type": fish_type_index, 
            "is_special": False
        })

    def spawn_special_fish(self, fish_key):
        fish_info = self.SPECIAL_FISH_TEMPLATES[fish_key]
        self.fishes.append({
            "x": random.randint(150, self.map_width - 150), 
            "y": random.randint(150, self.map_height - 150), 
            "dir": random.choice([-1, 1]), 
            "type": fish_info["idx"], 
            "is_special": True, 
            "key": fish_key, 
            "name": fish_info["kor_name"]
        })

    def spawn_monster(self):
        chosen_photo = random.choice(self.garbage_photos)
        self.monsters.append({
            "x": random.randint(100, self.map_width - 100), 
            "y": random.randint(100, self.map_height - 100), 
            "photo": chosen_photo, 
            "hp": 3
        })

    def show_in_game_message(self, text, is_error=False):
        if self.message_hide_timer: self.root.after_cancel(self.message_hide_timer)
        text_color, border_color = ("#f43f5e", "#f43f5e") if is_error else ("#4ade80", "#22c55e")
        self.canvas.itemconfig(self.msg_bg, state="normal", outline=border_color)
        self.canvas.itemconfig(self.msg_txt, state="normal", text=text, fill=text_color)
        self.canvas.tag_raise("game_notification")
        self.message_hide_timer = self.root.after(2000, self.hide_in_game_message)

    def hide_in_game_message(self):
        self.canvas.itemconfig(self.msg_bg, state="hidden")
        self.canvas.itemconfig(self.msg_txt, state="hidden")

    def show_fish_card_popup(self, fish_key):
        self.active_card_shown = True
        fish_info = self.SPECIAL_FISH_TEMPLATES[fish_key]
        if self.card_auto_close_timer: self.root.after_cancel(self.card_auto_close_timer)
        self.canvas.itemconfig("card_layer", state="normal")
        self.canvas.itemconfig(self.popup_title_text, text=fish_info['name'])
        self.canvas.itemconfig(self.popup_desc_text, text=fish_info['desc'])
        self.canvas.itemconfig(self.popup_card_image_node, image=self.ai_card_images.get(fish_key))
        self.canvas.tag_raise("card_layer")
        self.card_auto_close_timer = self.root.after(1500, self.hide_fish_card_popup)

    def hide_fish_card_popup(self):
        if self.active_card_shown:
            self.canvas.itemconfig("card_layer", state="hidden")
            self.active_card_shown = False

    def buy_special_fish(self, fish_key):
        if self.active_card_shown or self.is_game_over: return
        fish_info = self.SPECIAL_FISH_TEMPLATES[fish_key]
        price = fish_info["price"]
        if self.gold >= price:
            self.gold -= price
            self.fish_count += 1
            self.owned_special_fishes[fish_key] += 1
            self.spawn_special_fish(fish_key)
            self.canvas.itemconfig(self.gold_lbl, text=f"💰 {self.gold} G")
            self.canvas.itemconfig(self.fish_lbl, text=f"물고기: {self.fish_count}마리")
            self.show_in_game_message(f"🎉 {fish_info['kor_name']} 영입 완료! (-{price}G)")
            self.show_fish_card_popup(fish_key)
        else:
            self.show_in_game_message(f"❌ 골드가 부족합니다! (필요: {price}G)", is_error=True)

    def setup_ui(self):
        self.bg_image_node = self.canvas.create_image(0, 0, image=self.full_map_image, anchor="nw", tags="bg_layer")
        
        # 🗺️ 왼쪽 상단 미니맵 GUI 영역 구성 (X: 10~150, Y: 10~175)
        self.canvas.create_rectangle(10, 10, 150, 175, fill="#1c100a", outline="#ffd166", width=2)
        self.minimap_bg_node = self.canvas.create_image(15, 15, image=self.minimap_base_image, anchor="nw", tags="minimap_layer")
        
        self.coord_lbl = self.canvas.create_text(80, 162, text="X: 570, Y: 600", font=("Courier New", 9, "bold"), fill="#55ff55")

        self.canvas.create_rectangle(0, 0, 40, 40, fill="", outline="", tags="cheat_box")
        self.canvas.create_rectangle(570, 0, 800, 600, fill="#2c1a11", outline="#1c100a", width=5)
        
        self.timer_lbl = self.canvas.create_text(685, 25, text="⏱️ 01:30", font=("Courier New", 14, "bold"), fill="#ff4757")
        self.score_lbl = self.canvas.create_text(685, 50, text=f"🏆 {self.score} / {self.target_score}", font=("맑은 고딕", 10, "bold"), fill="#2ed573")
        self.gold_lbl = self.canvas.create_text(685, 75, text=f"💰 {self.gold} G", font=("맑은 고딕", 11, "bold"), fill="#ffffff")

        self.canvas.create_rectangle(585, 95, 785, 185, fill="#1c100a", outline="#ffd166", width=2)
        self.canvas.create_text(685, 110, text="[ 호수 수질 청정도 ]", font=("맑은 고딕", 10, "bold"), fill="#a5a5a5")
        self.do_label = self.canvas.create_text(685, 135, text=f"{self.water_quality:.1f}%", font=("Courier New", 15, "bold"), fill="#4cc9f0")
        self.canvas.create_rectangle(605, 155, 765, 170, fill="#0f0906", outline="#8b5a2b")
        self.gauge_bar = self.canvas.create_rectangle(606, 156, 764, 169, fill="#06d6a0", outline="")

        self.status_lbl = self.canvas.create_text(685, 205, text="정화 보트: 대기 중", font=("맑은 고딕", 10), fill="#cbd5e1", justify="center")
        self.fish_lbl = self.canvas.create_text(685, 230, text=f"물고기: {self.fish_count}마리", font=("맑은 고딕", 10), fill="#ffd166")

        self.canvas.create_rectangle(585, 260, 785, 420, fill="#150d08", outline="#e29578", width=2)
        self.canvas.create_text(685, 275, text="✨ 특별 물고기 분양 상점 ✨", font=("맑은 고딕", 9, "bold"), fill="#ffd166")
        
        self.canvas.create_rectangle(595, 292, 775, 317, fill="#3a2214", outline="#e29578", tags="buy_witch")
        self.canvas.create_text(685, 304, text="🎩 마녀 (90G) +15점/초", font=("맑은 고딕", 8), fill="#ffffff", tags="buy_witch")

        self.canvas.create_rectangle(595, 325, 775, 350, fill="#3a2214", outline="#e29578", tags="buy_ghost")
        self.canvas.create_text(685, 337, text="👻 유령 (130G) +25점/초", font=("맑은 고딕", 8), fill="#ffffff", tags="buy_ghost")

        self.canvas.create_rectangle(595, 358, 775, 383, fill="#3a2214", outline="#e29578", tags="buy_santa")
        self.canvas.create_text(685, 370, text="🎅 산타 (170G) +35점/초", font=("맑은 고딕", 8), fill="#ffffff", tags="buy_santa")

        self.canvas.create_rectangle(595, 391, 775, 416, fill="#3a2214", outline="#e29578", tags="buy_pumpkin")
        self.canvas.create_text(685, 403, text="👑 호박 (220G) +50점/초", font=("맑은 고딕", 8), fill="#ffffff", tags="buy_pumpkin")

        # 키보드 조작 안내 패널 (우측 하단)
        self.canvas.create_rectangle(585, 440, 785, 560, fill="#1c100a", outline="#38bdf8", width=2)
        self.canvas.create_text(685, 460, text="[ 조작 방법 가이드 ]", font=("맑은 고딕", 10, "bold"), fill="#38bdf8")
        self.canvas.create_text(685, 490, text="이동: W A S D", font=("맑은 고딕", 10, "bold"), fill="#ffffff")
        self.canvas.create_text(685, 520, text="물대포 발사: [ Shift ]", font=("맑은 고딕", 10, "bold"), fill="#f43f5e")

        self.msg_bg = self.canvas.create_rectangle(60, 515, 510, 565, fill="#150d08", outline="#4ade80", width=2, state="hidden", tags="game_notification")
        self.msg_txt = self.canvas.create_text(285, 540, text="", font=("맑은 고딕", 12, "bold"), fill="#ffffff", state="hidden", tags="game_notification")

        self.popup_dim_bg = self.canvas.create_rectangle(0, 0, 570, 600, fill="#000000", stipple="gray50", state="hidden", tags="card_layer")
        self.popup_frame = self.canvas.create_rectangle(175, 105, 395, 495, fill="#110a05", outline="#e29578", width=3, state="hidden", tags="card_layer")
        self.popup_star_decor = self.canvas.create_text(285, 125, text="★  XVII  ★", font=("Courier New", 10, "bold"), fill="#ffd166", state="hidden", tags="card_layer")
        self.popup_title_text = self.canvas.create_text(285, 150, text="CARD NAME", font=("Courier New", 12, "bold"), fill="#ffffff", state="hidden", tags="card_layer")
        self.popup_card_image_node = self.canvas.create_image(285, 260, image=None, state="hidden", tags="card_layer")
        self.popup_desc_text = self.canvas.create_text(285, 385, text="설명", font=("맑은 고딕", 9, "bold"), fill="#a5a5a5", state="hidden", tags="card_layer")
        self.popup_bottom_line = self.canvas.create_line(205, 435, 365, 435, fill="#e29578", width=1, state="hidden", tags="card_layer")
        self.popup_close_tip = self.canvas.create_text(285, 465, text="- 1.5초 후 자동 닫힘 -", font=("맑은 고딕", 8, "italic"), fill="#f43f5e", state="hidden", tags="card_layer")

        self.redraw_all_elements()

    def trigger_ending_cheat(self, event):
        if self.is_game_over: return
        self.cheat_click_count += 1
        remaining = 5 - self.cheat_click_count
        if remaining > 0:
            self.show_in_game_message(f"✨ 엔딩 치트: {remaining}번 더 누르면 엔딩!")
        else:
            self.show_in_game_message("🚀 엔딩 치트 활성화 완료!")
            self.score = self.target_score
            self.show_happy_ending_screen()

    def redraw_all_elements(self):
        camera_x = max(0, min(self.target_x - 285, self.map_width - 570))
        camera_y = max(0, min(self.target_y - 300, self.map_height - 600))

        self.canvas.coords(self.bg_image_node, -camera_x, -camera_y)

        # 🗺️ 미니맵에 찍히는 쓰레기 및 보트 위치 실시간 갱신
        self.canvas.delete("minimap_dot")
        
        for m in self.monsters:
            mx_mini = 15 + (m["x"] / self.map_width) * 130
            my_mini = 15 + (m["y"] / self.map_height) * 137
            self.canvas.create_oval(mx_mini - 2, my_mini - 2, mx_mini + 2, my_mini + 2, fill="#ff4757", outline="", tags="minimap_dot")

        bx_mini = 15 + (self.target_x / self.map_width) * 130
        by_mini = 15 + (self.target_y / self.map_height) * 137
        self.canvas.create_oval(bx_mini - 3, by_mini - 3, bx_mini + 3, by_mini + 3, fill="#38bdf8", outline="#ffffff", width=1, tags="minimap_dot")

        if hasattr(self, "coord_lbl"):
            self.canvas.itemconfig(self.coord_lbl, text=f"X: {int(self.target_x)}, Y: {int(self.target_y)}")
            self.canvas.tag_raise("minimap_layer")
            self.canvas.tag_raise("minimap_dot")
            self.canvas.tag_raise(self.coord_lbl)

        self.canvas.delete("boat_sprite")
        angle_deg = math.degrees(self.boat_angle) % 360
        frame_idx = int((angle_deg + 11.25) // 22.5) % 16
        screen_boat_x = self.target_x - camera_x
        screen_boat_y = self.target_y - camera_y
        self.canvas.create_image(screen_boat_x, screen_boat_y, image=self.boat_photos[frame_idx], tags="boat_sprite")

    def process_keyboard_movement(self):
        if self.is_game_over: return
        
        dx, dy = 0, 0
        if self.key_states["w"]: dy -= 1
        if self.key_states["s"]: dy += 1
        if self.key_states["a"]: dx -= 1
        if self.key_states["d"]: dx += 1

        if dx != 0 or dy != 0:
            if self.active_card_shown: self.hide_fish_card_popup()
            self.boat_angle = math.atan2(dy, dx)
            
            # 🚀 속도가 느리다는 피드백을 반영하여 속도 상향 (기존 3.5 -> 6.0)
            speed_factor = 6.0 
            length = math.sqrt(dx**2 + dy**2)
            
            next_x = self.target_x + (dx / length) * speed_factor
            next_y = self.target_y + (dy / length) * speed_factor

            self.target_x = max(30, min(next_x, self.map_width - 30))
            self.target_y = max(30, min(next_y, self.map_height - 30))
            self.redraw_all_elements()

    def show_happy_ending_screen(self):
        self.is_game_over = True
        self.canvas.delete("all")
        
        if hasattr(self, "ending_photo") and self.ending_photo:
            self.canvas.create_image(0, 0, image=self.ending_photo, anchor="nw")
        else:
            self.canvas.create_rectangle(0, 0, 800, 600, fill="#1890ff", outline="")

        elapsed_seconds = self.initial_time - self.time_limit
        m_min, m_sec = divmod(elapsed_seconds, 60)
        time_str = f"{m_min}분 {m_sec}초" if m_min > 0 else f"{m_sec}초"

        self.canvas.create_rectangle(230, 320, 570, 440, fill="#1c100a", outline="#ffd166", width=3)

        self.canvas.create_text(402, 362, text=f"🏆 최종 점수 : {self.score:,}점", font=("맑은 고딕", 18, "bold"), fill="#000000")
        self.canvas.create_text(400, 360, text=f"🏆 최종 점수 : {self.score:,}점", font=("맑은 고딕", 18, "bold"), fill="#ffd166")

        self.canvas.create_text(402, 402, text=f"⏱️ 소요 시간 : {time_str}", font=("맑은 고딕", 16, "bold"), fill="#000000")
        self.canvas.create_text(400, 400, text=f"⏱️ 소요 시간 : {time_str}", font=("맑은 고딕", 16, "bold"), fill="#4cc9f0")

        btn = self.canvas.create_rectangle(260, 480, 540, 540, fill="#1e293b", outline="#38bdf8", width=3, tags="exit_end_btn")
        self.canvas.create_text(400, 510, text="🏠 메인 화면으로 돌아가기", font=("맑은 고딕", 15, "bold"), fill="#ffffff", tags="exit_end_btn")
        
        self.canvas.tag_bind("exit_end_btn", "<Button-1>", lambda e: [self.root.destroy(), self.return_to_main()])

    def update_game_logic(self):
        if self.is_game_over: return

        self.time_limit -= 1
        mins, secs = divmod(self.time_limit, 60)
        self.canvas.itemconfig(self.timer_lbl, text=f"⏱️ {mins:02d}:{secs:02d}")

        current_tick_score = 0
        
        pumpkin_count = self.owned_special_fishes["pumpkin"]
        pumpkin_bonus_score = 50 * pumpkin_count

        for fish in self.fishes:
            if fish["is_special"]:
                f_key = fish["key"]
                val = self.SPECIAL_FISH_TEMPLATES[f_key]["score_val"]
                if f_key == "pumpkin":
                    val += pumpkin_bonus_score
                current_tick_score += val
            else:
                current_tick_score += 5

        santa_count = self.owned_special_fishes["santa"]
        if self.water_quality >= 60.0:
            score_multiplier = 1.0 + (santa_count * 0.4)
            current_tick_score = int(current_tick_score * score_multiplier)

        if self.water_quality >= 100.0:
            current_tick_score += 30
            self.show_in_game_message("🌟 완벽한 수질 유지 중! 보너스 점수 (+30점)")

        self.score += current_tick_score

        if self.score >= self.target_score:
            self.show_happy_ending_screen()
            return

        if self.time_limit <= 0:
            self.is_game_over = True
            messagebox.showwarning("TIME OVER ⏳", f"시간 초과!\n최종 점수: {self.score}점")
            self.root.destroy()
            self.return_to_main()
            return

        nearby_garbage_count = sum(1 for m in self.monsters if math.sqrt((self.target_x - m["x"])**2 + (self.target_y - m["y"])**2) < 300)
        witch_count = self.owned_special_fishes["witch"]

        if nearby_garbage_count > 0:
            drain_rate = 1.2 * nearby_garbage_count * max(0.2, 1.0 - (witch_count * 0.3))
            self.water_quality -= drain_rate
        else:
            self.water_quality += random.uniform(1.2, 2.5)

        if self.is_pumping:
            self.water_quality += random.uniform(2.5, 4.0)
            self.gold += 1
        else:
            self.gold += 2

        self.water_quality = max(0.0, min(self.max_water_quality, self.water_quality))

        self.monster_spawn_timer += 1
        if self.monster_spawn_timer >= 6:
            self.monster_spawn_timer = 0
            if len(self.monsters) < 15:
                self.spawn_monster()

        ghost_count = self.owned_special_fishes["ghost"]
        if ghost_count > 0:
            self.ghost_gold_timer += 1
            if self.ghost_gold_timer >= 10:
                self.ghost_gold_timer = 0
                bonus_income = 15 * ghost_count
                self.gold += bonus_income
                self.show_in_game_message(f"👻 유령 가재 청소 보너스! (+{bonus_income}G)")

        ratio = self.water_quality / 100.0
        self.canvas.coords(self.gauge_bar, 606, 156, 606 + int(158 * ratio), 169)
        
        if self.water_quality >= 100.0:
            self.canvas.itemconfig(self.gauge_bar, fill="#ffd166")
            self.canvas.itemconfig(self.do_label, fill="#ffd166", text=f"{self.water_quality:.1f}% MAX")
        elif self.water_quality >= 80.0:
            self.canvas.itemconfig(self.gauge_bar, fill="#06d6a0")
            self.canvas.itemconfig(self.do_label, fill="#4cc9f0", text=f"{self.water_quality:.1f}%")
        elif self.water_quality >= 40.0:
            self.canvas.itemconfig(self.gauge_bar, fill="#e29578")
            self.canvas.itemconfig(self.do_label, fill="#e29578", text=f"{self.water_quality:.1f}%")
        else:
            self.canvas.itemconfig(self.gauge_bar, fill="#ef4444")
            self.canvas.itemconfig(self.do_label, fill="#f43f5e", text=f"{self.water_quality:.1f}% (위험)")

        self.canvas.itemconfig(self.score_lbl, text=f"🏆 {self.score} / {self.target_score}")
        self.canvas.itemconfig(self.gold_lbl, text=f"💰 {self.gold} G")
        self.canvas.itemconfig(self.fish_lbl, text=f"물고기: {self.fish_count}마리")
        self.canvas.itemconfig(self.status_lbl, text="정화 보트 상태:\n⚡ 물대포 가동 중!" if self.is_pumping else "정화 보트 상태:\n순항 대기 중", fill="#4ade80" if self.is_pumping else "#f87171")

        self.root.after(1000, self.update_game_logic)

    def animate_sub_engine(self):
        if self.is_game_over: return
        
        # 프레임 단위로 키보드 이동 체크를 수행하여 반응 속도를 극대화
        self.process_keyboard_movement()
        self.redraw_all_elements()
        
        self.canvas.delete("fish_sprites")
        self.canvas.delete("monster_sprites")
        self.canvas.delete("beam_sprite")
        
        if not hasattr(self, "anim_timer"): self.anim_timer = 0
        self.anim_timer += 0.2

        camera_x = max(0, min(self.target_x - 285, self.map_width - 570))
        camera_y = max(0, min(self.target_y - 300, self.map_height - 600))

        for fish in self.fishes:
            fish["x"] += 1.2 * fish["dir"]
            if fish["x"] > self.map_width - 50: fish["dir"] = -1
            elif fish["x"] < 50: fish["dir"] = 1

            fish["y"] += math.sin(fish["x"] * 0.05 + self.anim_timer) * 0.3

            fx, fy = fish["x"] - camera_x, fish["y"] - camera_y
            if -30 <= fx <= 600 and -30 <= fy <= 630:
                tk_photo = self.fish_photos_right[fish["type"]] if fish["dir"] == 1 else self.fish_photos_left[fish["type"]]
                self.canvas.create_image(fx, fy, image=tk_photo, tags="fish_sprites")

        if self.is_pumping:
            deg = -math.degrees(self.boat_angle)
            
            if not hasattr(self, "gif_frame_idx"): self.gif_frame_idx = 0
            self.gif_frame_idx = (self.gif_frame_idx + 1) % len(self.water_arrow_frames)
            current_raw_frame = self.water_arrow_frames[self.gif_frame_idx]

            rot_beam = current_raw_frame.rotate(deg, resample=Image.Resampling.NEAREST, expand=True)
            self.beam_photo_tk = ImageTk.PhotoImage(rot_beam)

            beam_dist = 85
            beam_world_x = self.target_x + math.cos(self.boat_angle) * beam_dist
            beam_world_y = self.target_y + math.sin(self.boat_angle) * beam_dist

            beam_screen_x = beam_world_x - camera_x
            beam_screen_y = beam_world_y - camera_y
            self.canvas.create_image(beam_screen_x, beam_screen_y, image=self.beam_photo_tk, tags="beam_sprite")

            for m in list(self.monsters):
                dist = math.sqrt((beam_world_x - m["x"])**2 + (beam_world_y - m["y"])**2)
                if dist < 75:
                    m["hp"] -= 1
                    if m["hp"] <= 0:
                        self.monsters.remove(m)
                        reward = random.randint(15, 30)
                        self.gold += reward
                        self.show_in_game_message(f"✨ 쓰레기 수거 성공! (+{reward}G)")

        for m in self.monsters:
            mx, my = m["x"] - camera_x, m["y"] - camera_y
            if -30 <= mx <= 600 and -30 <= fy <= 630:
                self.canvas.create_image(mx, my, image=m["photo"], tags="monster_sprites")

        if self.active_card_shown:
            self.canvas.tag_raise("card_layer")

        self.root.after(16, self.animate_sub_engine)


class MainMenuApp:
    def __init__(self, root):
        self.root = root
        self.root.title("My Little Ecoboat - Main")
        self.root.geometry("800x600")
        self.root.resizable(False, False)
        
        self.canvas = tk.Canvas(self.root, width=800, height=600, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.bg_main_photo = None
        for filename in ["mainstart.png", "mainstart.jpg"]:
            path = os.path.join(BASE_DIR, filename)
            if os.path.exists(path):
                try:
                    img = Image.open(path).convert("RGBA").resize((800, 600), Image.Resampling.LANCZOS)
                    self.bg_main_photo = ImageTk.PhotoImage(img)
                    break
                except Exception:
                    pass

        if self.bg_main_photo:
            self.canvas.create_image(0, 0, image=self.bg_main_photo, anchor="nw")
        else:
            self.canvas.create_rectangle(0, 0, 800, 600, fill="#1a1a1a")

        self.canvas.create_text(401, 91, text="마이 리틀 에코보트", font=("맑은 고딕", 36, "bold"), fill="#fff3d1")
        self.canvas.create_text(400, 90, text="마이 리틀 에코보트", font=("맑은 고딕", 36, "bold"), fill="#2c1a11")

        self.canvas.create_text(401, 151, text="🎯 쓰레기는 시원하게 치우고, 물고기 친구들을 데려오자!", font=("맑은 고딕", 12, "bold"), fill="#ffffff")
        self.canvas.create_text(400, 150, text="🎯 쓰레기는 시원하게 치우고, 물고기 친구들을 데려오자!", font=("맑은 고딕", 12, "bold"), fill="#150d08")

        self.start_btn = self.canvas.create_rectangle(300, 190, 500, 260, fill="#3a2214", outline="#e29578", width=3, tags="start_btn")
        self.canvas.create_text(400, 225, text="게임 화면 시작", font=("맑은 고딕", 16, "bold"), fill="white", tags="start_btn")
        self.canvas.tag_bind("start_btn", "<Button-1>", self.start_game)

    def start_game(self, event):
        self.root.destroy()
        game_root = tk.Tk()
        RealPixelArtBoatGame(game_root, self.restart_main_menu)
        game_root.mainloop()

    def restart_main_menu(self):
        root = tk.Tk()
        MainMenuApp(root)
        root.mainloop()


if __name__ == "__main__":
    window = tk.Tk()
    app = MainMenuApp(window)
    window.mainloop()