#!../bin/python

import sys
import pygame
import string
import queue
import cv2
import numpy as np 
import heapq
import time
import gc
import tracemalloc
import psutil
import os
from collections import deque

DIRECTIONS = {"u": (-1, 0), "d": (1, 0), "l": (0, -1), "r": (0, 1)}

class game:
    def is_valid_value(self,char):
        if ( char == ' ' or #floor
            char == '#' or #wall
            char == '@' or #worker on floor
            char == '.' or #dock
            char == '*' or #box on dock
            char == '$' or #box
            char == '+' ): #worker on dock
            return True
        else:
            return False
        
    def get_size(self):
        """Trả về kích thước level dưới dạng (số cột, số hàng)"""
        if not self.matrix:
            return 0, 0
        return len(self.matrix[0]), len(self.matrix)
    
    def load_map(self,level):
        self.level = level

        with open('level.txt', 'r') as file:
            maps = file.read().split("\n\n")  # Tách các level bằng dòng trống

        if 1 <= self.level <= len(maps):
            return maps[level - 1].split("\n")  # Trả về map của level đó
        else:
            print("Level không hợp lệ!")
        return None
    
    def add_to_history(self, state):
        """Lưu trạng thái hiện tại vào danh sách lịch sử để có thể undo."""
        self.history.append([row[:] for row in state])  # Lưu bản sao của ma trận

    def on_play_button_click(self):
     print("Trọng số của các hòn đá:")
     boxes = self.get_boxes()  # Lấy danh sách vị trí hộp
     for i, (x, y) in enumerate(boxes):
        weight = self.weights[i] if i < len(self.weights) else 1  # Trọng số mặc định là 1 nếu thiếu
        print(f"- Hòn đá {i+1} tại ({x}, {y}) có trọng số: {weight}")

    def get_weight_at_position(self, a, b):
     """Lấy trọng số của hòn đá tại vị trí (a, b), đảm bảo đồng bộ danh sách hộp và trọng số."""
    
     boxes = self.get_boxes()  # Cập nhật danh sách vị trí hộp
    
    # Kiểm tra nếu danh sách hộp và trọng số không khớp
     if len(self.weights) != len(boxes):
        print(f"⚠️ Cảnh báo: Số lượng hộp ({len(boxes)}) không khớp với số lượng trọng số ({len(self.weights)})!")
        
        # Đảm bảo danh sách trọng số có đúng số phần tử bằng danh sách hộp
        if len(self.weights) < len(boxes):
            self.weights.extend([1] * (len(boxes) - len(self.weights)))  # Thêm weight mặc định
        elif len(self.weights) > len(boxes):
            self.weights = self.weights[:len(boxes)]  # Cắt bớt weight dư thừa
    
     # Duyệt danh sách hộp để tìm hộp tại vị trí (a, b)
     for i, (x, y) in enumerate(boxes):
        if x == a and y == b:  # Nếu tìm thấy hòn đá tại (a, b)
            return self.weights[i]  # Trả về weight tương ứng
    
     return 0  # Không tìm thấy hòn đá tại vị trí này

    def __init__(self, filename, level):
        self.queue = queue.LifoQueue()
        self.level_path = filename  
        self.level = level
        self.weights = []  
        self.history = []  
        self.matrix = []
        self.original_matrix = []  

        if level < 1:
            print(f"ERROR: Level {level} is out of range")
            sys.exit(1)

        # Kiểm tra file có tồn tại không
        if not os.path.exists(filename):
            print(f"ERROR: File '{filename}' not found!")
            sys.exit(1)

        # Đọc dữ liệu từ file
        with open(filename, 'r', encoding='utf-8') as file:
            level_found = False
            reading_matrix = False  # Đánh dấu khi bắt đầu đọc ma trận
            
            for line in file:
                line = line.rstrip()

                if not level_found:
                    if line == f"Level {level}":
                        level_found = True
                elif not self.weights:
                    # Đọc trọng số, KHÔNG kiểm tra bằng is_valid_value
                    try:
                        self.weights = list(map(int, line.split()))
                    except ValueError:
                        print(f"ERROR: Invalid weight format in Level {level}")
                        sys.exit(1)
                else:
                    # Khi đến đây, bắt đầu đọc ma trận
                    reading_matrix = True  
                    
                    if line:  # Nếu không phải dòng trống
                        row = []
                        for c in line:
                            if self.is_valid_value(c):
                                row.append(c)
                            else:
                                print(f"ERROR: Level {level} has invalid value '{c}' in matrix!")
                                sys.exit(1)
                        self.matrix.append(row)
                    else:
                        break  # Gặp dòng trống thì dừng lại

        # Kiểm tra nếu thiếu dữ liệu
        if not level_found:
            print(f"ERROR: Level {level} not found in file")
            sys.exit(1)
        if not self.weights:
            print(f"ERROR: No weights found for Level {level}")
            sys.exit(1)
        if not self.matrix:
            print(f"ERROR: No matrix data found for Level {level}")
            sys.exit(1)

        self.original_matrix = [row[:] for row in self.matrix]  
        self.grid = self.matrix  # Lưu vào grid để sử dụng sau này

    def load_matrix_from_file(self, filename):
     """Loads the matrix from the level file, including weights."""
     matrix = []
     weights = []
     level_found = False

     with open(filename, 'r', encoding='utf-8') as file:
        for line in file:
            line = line.rstrip("\n")  # Chỉ xóa ký tự xuống dòng, giữ khoảng trắng đầu

            if not level_found:
                if line.strip() == f"Level {self.level}":  # Chỉ xóa khoảng trắng cuối dòng
                    level_found = True
            elif not weights:
                # Đọc dòng trọng số
                try:
                    weights = list(map(int, line.split()))
                except ValueError:
                    print(f"ERROR: Invalid weight format in Level {self.level}")
                    sys.exit(1)
            else:
                if line.strip() == "":  # Dòng trống nghĩa là hết level
                    break

                row = list(line)  # Giữ nguyên khoảng trắng đầu dòng
                for c in row:
                    if not self.is_valid_value(c):
                        print(f"ERROR: Level {self.level} has invalid value '{c}'")
                        sys.exit(1)

                matrix.append(row)  # Chỉ append sau khi kiểm tra hợp lệ
    
     if not level_found:
        print(f"ERROR: Level {self.level} not found in file")
        sys.exit(1)

     if not weights:
        print(f"ERROR: No weights found for Level {self.level}")
        sys.exit(1)

     self.weights = weights  # Lưu trọng số vào biến của class
     return matrix

    def find_worker(self, matrix):
     """Finds the worker's position in the matrix."""
     for i, row in enumerate(matrix):
        for j, cell in enumerate(row):
            if cell == '@':  # Assuming 'W' represents the worker
                return (i, j)
     return None  # If worker not found
    
    def get_boxes(self):
     """Trả về danh sách vị trí các hộp trong ma trận."""
     boxes = []
     for y, row in enumerate(self.matrix):
        for x, cell in enumerate(row):
            if cell in ('$','*'):  # '$' là hộp, '*' là hộp trên mục tiêu
                boxes.append((x, y))
     return boxes

    def load_level(self):
     """Tải lại level từ file."""
     self.matrix = self.load_matrix_from_file(self.level_path)  
     self.worker_position = self.find_worker(self.matrix)  # Find worker's position
     # Lưu ma trận gốc để reset sau này
     self.initial_matrix = [row[:] for row in self.matrix]

    def reset(self):
     global step_count, weight_count
     """Đặt lại trò chơi về trạng thái ban đầu"""
     step_count = 0
     weight_count = 0

     self.queue = queue.LifoQueue() 
     self.weights = []  
     self.history = []  
     self.matrix = []
     self.original_matrix = []  

     if level < 1:
            print(f"ERROR: Level {level} is out of range")
            sys.exit(1)

        # Kiểm tra file có tồn tại không
     if not os.path.exists(self.level_path):
            print(f"ERROR: File '{self.level_path}' not found!")
            sys.exit(1)

        # Đọc dữ liệu từ file
     with open(self.level_path, 'r', encoding='utf-8') as file:
            level_found = False
            reading_matrix = False  # Đánh dấu khi bắt đầu đọc ma trận
            
            for line in file:
                line = line.rstrip()

                if not level_found:
                    if line == f"Level {level}":
                        level_found = True
                elif not self.weights:
                    # Đọc trọng số, KHÔNG kiểm tra bằng is_valid_value
                    try:
                        self.weights = list(map(int, line.split()))
                    except ValueError:
                        print(f"ERROR: Invalid weight format in Level {level}")
                        sys.exit(1)
                else:
                    # Khi đến đây, bắt đầu đọc ma trận
                    reading_matrix = True  
                    
                    if line:  # Nếu không phải dòng trống
                        row = []
                        for c in line:
                            if self.is_valid_value(c):
                                row.append(c)
                            else:
                                print(f"ERROR: Level {level} has invalid value '{c}' in matrix!")
                                sys.exit(1)
                        self.matrix.append(row)
                    else:
                        break  # Gặp dòng trống thì dừng lại

        # Kiểm tra nếu thiếu dữ liệu
     if not level_found:
            print(f"ERROR: Level {level} not found in file")
            sys.exit(1)
     if not self.weights:
            print(f"ERROR: No weights found for Level {level}")
            sys.exit(1)
     if not self.matrix:
            print(f"ERROR: No matrix data found for Level {level}")
            sys.exit(1)

     self.original_matrix = [row[:] for row in self.matrix]  
     self.grid = self.matrix  # Lưu vào grid để sử dụng sau này

     # Tạo lại đối tượng game với level mới
     size = self.load_size()
     screen = pygame.display.set_mode(size)

     self.matrix = self.load_matrix_from_file(self.level_path)  
     self.worker_position = self.find_worker(self.matrix)  # Find worker's position
     # Lưu ma trận gốc để reset sau này
     self.initial_matrix = [row[:] for row in self.matrix]

    def load_size(self):
        x = 0
        y = len(self.matrix)
        for row in self.matrix:
            if len(row) > x:
                x = len(row)
        return (x * 32 + 175, y * 32 + 60)

    def get_matrix(self):
        return self.matrix

    def print_matrix(self):
        for row in self.matrix:
            for char in row:
                sys.stdout.write(char)
                sys.stdout.flush()
            sys.stdout.write('\n')

    def get_content(self,x,y):
        return self.matrix[y][x]

    def set_content(self,x,y,content):
        if self.is_valid_value(content):
            self.matrix[y][x] = content
        else:
            print("ERROR: Value '"+content+"' to be added is not valid")

    def worker(self):
        x = 0
        y = 0
        for row in self.matrix:
            for pos in row:
                if pos == '@' or pos == '+':
                    return (x, y, pos)
                else:
                    x = x + 1
            y = y + 1
            x = 0

    def can_move(self,x,y):
        return self.get_content(self.worker()[0]+x,self.worker()[1]+y) not in ['#','*','$']

    def next(self,x,y):
        return self.get_content(self.worker()[0]+x,self.worker()[1]+y)

    def can_push(self,x,y):
        return (self.next(x,y) in ['*','$'] and self.next(x+x,y+y) in [' ','.'])

    def is_completed(self):
        for row in self.matrix:
            for cell in row:
                if cell == '$':
                    return False
        return True

    def move_box(self, x, y, a, b):
     global weight_count

     current_box = self.get_content(x, y)
     future_box = self.get_content(x + a, y + b)

     # Lấy danh sách hộp hiện tại và đảm bảo đồng bộ với self.weights
     boxes = self.get_boxes()
     if len(self.weights) != len(boxes):
        print(f"⚠️ Số lượng hộp ({len(boxes)}) không khớp với trọng số ({len(self.weights)})!")
        return

     # Tìm chỉ mục của hòn đá cần di chuyển
     box_index = -1
     for i, (bx, by) in enumerate(boxes):
        if bx == x and by == y:
            box_index = i
            break

     if box_index == -1:
        print(f"⚠️ Không tìm thấy hòn đá tại ({x}, {y})!")
        return

     weight = self.weights[box_index]  # Trọng số của hòn đá cần di chuyển

     push_sound = pygame.mixer.Sound("music/stonePush.wav")
     if current_box in ('$','*') and future_box in (' ', '.'):
         push_sound.play()  # 🔊 Phát âm thanh khi đẩy đá

     if current_box == '$' and future_box == ' ':
        weight_count += weight
        self.set_content(x + a, y + b, '$')
        self.set_content(x, y, ' ')
     elif current_box == '$' and future_box == '.':
        weight_count += weight
        self.set_content(x + a, y + b, '*')
        self.set_content(x, y, ' ')
     elif current_box == '*' and future_box == ' ':
        weight_count += weight
        self.set_content(x + a, y + b, '$')
        self.set_content(x, y, '.')
     elif current_box == '*' and future_box == '.':
        weight_count += weight
        self.set_content(x + a, y + b, '*')
        self.set_content(x, y, '.')

     # Cập nhật lại danh sách vị trí hộp sau khi di chuyển
     new_boxes = self.get_boxes()
     new_weights = [0] * len(new_boxes)  # Tạo danh sách mới để lưu trọng số

     for i, (bx, by) in enumerate(new_boxes):
        # Nếu hộp này là hộp vừa di chuyển, gán trọng số từ hộp cũ
        if bx == x + a and by == y + b:
            new_weights[i] = weight
        else:
            # Lấy trọng số từ danh sách cũ dựa trên vị trí trước đó
            for j, (old_x, old_y) in enumerate(boxes):
                if bx == old_x and by == old_y:
                    new_weights[i] = self.weights[j]
                    break

     # Cập nhật lại danh sách trọng số sau khi di chuyển
     self.weights = new_weights

    def unmove(self):
        if not self.queue.empty():
            movement = self.queue.get()
            if movement[2]:
                current = self.worker()
                self.move(movement[0] * -1,movement[1] * -1, False)
                self.move_box(current[0]+movement[0],current[1]+movement[1],movement[0] * -1,movement[1] * -1)
            else:
                self.move(movement[0] * -1,movement[1] * -1, False)

    def move(self,x,y,save):
        global weight_count,step_count
        if self.can_move(x,y):
            current = self.worker()
            future = self.next(x,y)
            if current[2] == '@' and future == ' ':
                self.set_content(current[0]+x,current[1]+y,'@')
                self.set_content(current[0],current[1],' ')           
                step_count += 1
                if save: self.queue.put((x,y,False))
            elif current[2] == '@' and future == '.':
                self.set_content(current[0]+x,current[1]+y,'+')
                self.set_content(current[0],current[1],' ')            
                step_count += 1
                if save: self.queue.put((x,y,False))
            elif current[2] == '+' and future == ' ':
                self.set_content(current[0]+x,current[1]+y,'@')
                self.set_content(current[0],current[1],'.')             
                step_count += 1
                if save: self.queue.put((x,y,False))
            elif current[2] == '+' and future == '.':
                self.set_content(current[0]+x,current[1]+y,'+')
                self.set_content(current[0],current[1],'.')
                step_count += 1
                if save: self.queue.put((x,y,False))
        elif self.can_push(x,y):
            current = self.worker()
            future = self.next(x,y)
            future_box = self.next(x+x,y+y)
            if current[2] == '@' and future == '$' and future_box == ' ':
                self.move_box(current[0]+x,current[1]+y,x,y)
                self.set_content(current[0],current[1],' ')
                self.set_content(current[0]+x,current[1]+y,'@')
                step_count += 1
                if save: self.queue.put((x,y,True))
            elif current[2] == '@' and future == '$' and future_box == '.':
                self.move_box(current[0]+x,current[1]+y,x,y)
                self.set_content(current[0],current[1],' ')
                self.set_content(current[0]+x,current[1]+y,'@')
                step_count += 1
                if save: self.queue.put((x,y,True))
            elif current[2] == '@' and future == '*' and future_box == ' ':
                self.move_box(current[0]+x,current[1]+y,x,y)
                self.set_content(current[0],current[1],' ')
                self.set_content(current[0]+x,current[1]+y,'+')
                step_count += 1
                if save: self.queue.put((x,y,True))
            elif current[2] == '@' and future == '*' and future_box == '.':
                self.move_box(current[0]+x,current[1]+y,x,y)
                self.set_content(current[0],current[1],' ')
                self.set_content(current[0]+x,current[1]+y,'+')
                step_count += 1
                if save: self.queue.put((x,y,True))
            if current[2] == '+' and future == '$' and future_box == ' ':
                self.move_box(current[0]+x,current[1]+y,x,y)
                self.set_content(current[0],current[1],'.')
                self.set_content(current[0]+x,current[1]+y,'@')
                step_count += 1
                if save: self.queue.put((x,y,True))
            elif current[2] == '+' and future == '$' and future_box == '.':
                self.move_box(current[0]+x,current[1]+y,x,y)
                self.set_content(current[0],current[1],'.')
                self.set_content(current[0]+x,current[1]+y,'@')
                step_count += 1
                if save: self.queue.put((x,y,True))
            elif current[2] == '+' and future == '*' and future_box == ' ':
                self.move_box(current[0]+x,current[1]+y,x,y)
                self.set_content(current[0],current[1],'.')
                self.set_content(current[0]+x,current[1]+y,'+')
                step_count += 1
                if save: self.queue.put((x,y,True))
            elif current[2] == '+' and future == '*' and future_box == '.':
                self.move_box(current[0]+x,current[1]+y,x,y)
                self.set_content(current[0],current[1],'.')
                self.set_content(current[0]+x,current[1]+y,'+')
                step_count += 1
                if save: self.queue.put((x,y,True))

def get_max_dimensions(matrix):
    max_columns = max(len(row) for row in matrix)  # Số cột nhiều nhất
    max_rows = len(matrix)  # Số dòng nhiều nhất
    return max_rows, max_columns

step_count = 0  # Đặt số bước về 0 khi bắt đầu game
weight_count = 0

def print_game(matrix, screen):
    screen.fill(background)
    
    max_rows, max_cols = get_max_dimensions(matrix)  # Lấy dòng và cột lớn nhất
    game_width = max_cols * 32
    game_height = max_rows * 32
    
    for row_idx in range(max_rows):
        for col_idx in range(max_cols):
            x = col_idx * 32
            y = row_idx * 32
            
            if row_idx < len(matrix) and col_idx < len(matrix[row_idx]):
                char = matrix[row_idx][col_idx]
            else:
                char = ' '  # Mặc định là sàn nếu vượt kích thước ma trận
            
            if char == ' ':  # floor
                screen.blit(floor, (x, y))
            elif char == '#':  # wall
                screen.blit(wall, (x, y))
            elif char == '@':  # worker on floor
                screen.blit(worker, (x, y))
            elif char == '.':  # dock
                screen.blit(docker, (x, y))
            elif char == '*':  # box on dock
                screen.blit(box_docked, (x, y))
            elif char == '$':  # box
                screen.blit(box, (x, y))
            elif char == '+':  # worker on dock
                screen.blit(worker_docked, (x, y))
            x = x + 32
        x = 0
        y = y + 32

    # **Thêm nút bên ngoài ma trận**
    button_x = game_width + 25  # Đặt nút bên phải ma trận
    button_y = 50  # Khoảng cách từ đỉnh cửa sổ
    
    algo_button.rect.topleft = (button_x, button_y)  # Chỉnh vị trí nút thuật toán
    reset_button.rect.topleft = (button_x, button_y + 60)  # Chỉnh vị trí nút Reset
    play_button.rect.topleft = (button_x, button_y + 120)

    algo_button.draw(screen)
    reset_button.draw(screen)
    play_button.draw(screen)

    font = pygame.font.Font(None, 24)  
    step_text = font.render(f"Step: {step_count}   Weight: {weight_count}    Cost: {weight_count + step_count}", True, BLACK)  
    step_rect = step_text.get_rect(topleft=(10, game_height + 10))  

    screen.blit(step_text, step_rect)  # Vẽ số bước lên màn hình

def get_key():
  while 1:
    event = pygame.event.poll()
    if event.type == pygame.KEYDOWN:
      return event.key
    else:
      pass

def display_box(screen, message):
    """Hiển thị bảng nhập Level với viền trắng tự co theo chữ"""
    font_size = 60  # Điều chỉnh kích thước chữ
    fontobject = pygame.font.Font(None, font_size)  

    # Đổi màu chữ
    text_color = (255, 255, 220)  
    text_surface = fontobject.render(message, True, text_color)
    text_width, text_height = text_surface.get_size()

    padding_x = max(40, text_width // 5)  
    padding_y = max(30, text_height // 3)  

    box_width = text_width + 2 * padding_x
    box_height = text_height + 2 * padding_y
    box_x = (screen.get_width() - box_width) // 2
    box_y = (screen.get_height() - box_height) // 2

    # Xóa nền trước khi vẽ lại hộp (giữ màn hình đen)
    screen.fill((0, 0, 0))  

    # Tải ảnh nền cho hộp thoại
    box_background = pygame.image.load("images/background_level.png")
    box_background = pygame.transform.scale(box_background, (box_width, box_height))

    # Hiển thị ảnh nền
    screen.blit(box_background, (box_x, box_y))

    # Vẽ viền trắng bao quanh ảnh nền
    pygame.draw.rect(screen, (255, 255, 255), (box_x, box_y, box_width, box_height), 4, border_radius=0)

    # Căn chữ vào giữa hộp
    text_x = box_x + (box_width - text_width) // 2
    text_y = box_y + (box_height - text_height) // 2
    screen.blit(text_surface, (text_x, text_y))

    pygame.display.flip()

def display_end(screen):
    message = "Level Completed"
    fontobject = pygame.font.Font(None,18)
    pygame.draw.rect(screen, (0,0,0),
                   ((screen.get_width() / 2) - 100,
                    (screen.get_height() / 2) - 10,
                    200,20), 0)
    pygame.draw.rect(screen, (255,255,255),
                   ((screen.get_width() / 2) - 102,
                    (screen.get_height() / 2) - 12,
                    204,24), 1)
    screen.blit(fontobject.render(message, 1, (255,255,255)),
                ((screen.get_width() / 2) - 100, (screen.get_height() / 2) - 10))
    pygame.display.flip()


def ask(screen, question):
  "ask(screen, question) -> answer"
  pygame.font.init()
  current_string = []
  display_box(screen, question + ": " + "".join(current_string))
  while 1:
    inkey = get_key()
    if inkey == pygame.K_BACKSPACE:
      current_string = current_string[0:-1]
    elif inkey == pygame.K_RETURN:
      break
    elif inkey == pygame.K_MINUS:
      current_string.append("_")
    elif inkey <= 127:
      current_string.append(chr(inkey))
    display_box(screen, question + ": " + "".join(current_string))
  return "".join(current_string)

def start_game():
    start = pygame.display.set_mode((780, 520))
    level = ask(start, "Select Level")
    try:
        level = int(level)  # Chuyển chuỗi thành số nguyên
        if level > 0:
            return level
        else:
            print("ERROR: Invalid Level:", level)
            sys.exit(2)
    except ValueError:
        print("ERROR: Invalid input. Please enter a number.")
        sys.exit(2)

class SokobanSolver:
    def normalize_grid(self):
     """Chuẩn hóa lưới để đảm bảo tất cả các dòng có cùng số cột."""
     max_width = max(len(row) for row in self.grid)  # Tìm số cột lớn nhất
     for i in range(len(self.grid)):
        if len(self.grid[i]) < max_width:
            self.grid[i] += [" "] * (max_width - len(self.grid[i]))  # Thêm khoảng trắng

    def __init__(self, grid, algorithm):
        self.grid = [list(row) for row in grid]
        self.normalize_grid()  # Chuẩn hóa bàn cờ trước khi xử lý
        self.height = len(grid)
        self.width = len(grid[0])
        self.agent, self.boxes, self.targets = self.find_positions()
        self.algorithm = algorithm  # Lưu thuật toán được chọn

    def find_positions(self):
     if not self.grid or len(self.grid) == 0:
        return None, frozenset(), frozenset()

     agent = None
     boxes = set()
     targets = set()

     for r in range(self.height):
        if r >= len(self.grid):  # Kiểm tra giới hạn hàng
            print(f"LỖI: Hàng {r} không tồn tại trong grid!")
            continue

        for c in range(len(self.grid[r])):  # Chỉ duyệt trong giới hạn hợp lệ
            if c >= len(self.grid[r]):  # Kiểm tra giới hạn cột
                print(f"LỖI: Cột {c} không tồn tại trong hàng {r}!")
                continue

            if self.grid[r][c] == "@":
                agent = (r, c)
            elif self.grid[r][c] == "+":
                agent = (r, c)
                targets.add((r, c))
            elif self.grid[r][c] == "$":
                boxes.add((r, c))
            elif self.grid[r][c] == "*":
                boxes.add((r, c))
                targets.add((r, c))
            elif self.grid[r][c] == ".":
                targets.add((r, c))

     return agent, frozenset(boxes), frozenset(targets)

    def is_goal(self, boxes):
        return boxes == self.targets
    
    def heuristic(self, boxes):
        return sum(
            min(abs(bx - tx) + abs(by - ty) for tx, ty in self.targets)
            for bx, by in boxes
        )

    def get_neighbors(self, state):
        agent, boxes = state
        neighbors = []

        for action, (dr, dc) in DIRECTIONS.items():
            new_agent = (agent[0] + dr, agent[1] + dc)

            if self.grid[new_agent[0]][new_agent[1]] == "#":
                continue

            new_boxes = set(boxes)
            move_type = action

            if new_agent in boxes:
                new_box = (new_agent[0] + dr, new_agent[1] + dc)
                if new_box in boxes or self.grid[new_box[0]][new_box[1]] == "#":
                    continue
                new_boxes.remove(new_agent)
                new_boxes.add(new_box)
                move_type = action.upper()

            neighbors.append((move_type, (new_agent, frozenset(new_boxes))))

        return neighbors

    def ucs(self):
        start_time = time.time()
        tracemalloc.start()

        start_state = (self.agent, self.boxes)
        frontier = [(0, start_state, [])]  # Hàng đợi ưu tiên theo cost
        visited = set()
        nodes_explored = 0

        while frontier:
            cost, (agent, boxes), path = heapq.heappop(frontier)
            nodes_explored += 1

            if self.is_goal(boxes):
                end_time = time.time()
                current, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()

                steps = len(path)
                time_taken = (end_time - start_time) * 1000
                memory_used = peak / (1024 * 1024)

                output_filename = "output/outputUCS.txt"  # Tên file output

                with open(output_filename, "w", encoding="utf-8") as file:
                    file.write("Uniform Cost Search (UCS)\n")
                    file.write(
                    f"Steps: {steps}, Cost: {cost}, Nodes: {nodes_explored}, Time (ms): {time_taken:.2f}, Memory (MB): {memory_used:.2f}\n"
                    )
                    file.write(f"{''.join(path)}\n")

                return path

            if (agent, boxes) in visited:
                continue
            visited.add((agent, boxes))

            for action, next_state in self.get_neighbors((agent, boxes)):
                new_cost = cost + 1  # UCS chỉ dùng cost thực tế
                heapq.heappush(frontier, (new_cost, next_state, path + [action]))

        tracemalloc.stop()
        print("⛔ Không tìm thấy giải pháp!")
        return None

    def bfs(self):
        start_time = time.time()
        tracemalloc.start()

        start_state = (self.agent, self.boxes)
        frontier = deque([(start_state, [])])
        visited = set()
        nodes_explored = 0

        while frontier:
            (agent, boxes), path = frontier.popleft()
            nodes_explored += 1

            if self.is_goal(boxes):
                end_time = time.time()
                current, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()

                steps = len(path)
                time_taken = (end_time - start_time) * 1000
                memory_used = peak / (1024 * 1024)

                output_filename = "output/outputBFS.txt"  # Tên file output

                with open(output_filename, "w", encoding="utf-8") as file:
                    file.write("BFS search\n")
                    file.write(
                    f"Steps: {steps}, Node: {nodes_explored}, Time (ms): {time_taken:.2f}, Memory (MB): {memory_used:.2f}\n"
                    )
                    file.write(f"{''.join(path)}\n")

                return path

            if (agent, boxes) in visited:
                continue
            visited.add((agent, boxes))

            for action, next_state in self.get_neighbors((agent, boxes)):
                frontier.append((next_state, path + [action]))

        tracemalloc.stop()
        print("⛔ Không tìm thấy giải pháp!")
        return None

    def dfs(self):
        start_time = time.time()
        tracemalloc.start()

        start_state = (self.agent, self.boxes)
        stack = [(start_state, [])]  # Stack cho DFS
        visited = set()
        nodes_explored = 0

        while stack:
            (agent, boxes), path = stack.pop()
            nodes_explored += 1

            if self.is_goal(boxes):
                end_time = time.time()
                current, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()

                steps = len(path)
                time_taken = (end_time - start_time) * 1000
                memory_used = peak / (1024 * 1024)

                output_filename = "output/outputDFS.txt"  # Tên file output

                with open(output_filename, "w", encoding="utf-8") as file:
                    file.write("DFS search\n")
                    file.write(
                    f"Steps: {steps}, Node: {nodes_explored}, Time (ms): {time_taken:.2f}, Memory (MB): {memory_used:.2f}\n"
                    )
                    file.write(f"{''.join(path)}\n")

                return path

            if (agent, boxes) in visited:
                continue
            visited.add((agent, boxes))

            for action, next_state in self.get_neighbors((agent, boxes)):
                stack.append((next_state, path + [action]))  # Đẩy vào stack

        tracemalloc.stop()
        print("⛔ Không tìm thấy giải pháp!")
        return None
    
    def a_star(self):
        start_time = time.time()
        tracemalloc.start()

        start_state = (self.agent, self.boxes)
        frontier = [(self.heuristic(self.boxes), 0, start_state, [])]
        visited = set()
        nodes_explored = 0

        while frontier:
            _, cost, (agent, boxes), path = heapq.heappop(frontier)
            nodes_explored += 1

            if self.is_goal(boxes):
                end_time = time.time()
                current, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()

                steps = len(path)
                weight = cost
                time_taken = (end_time - start_time) * 1000
                memory_used = peak / (1024 * 1024)

                output_filename = "output/outputA_star.txt"  # Tên file output

                with open(output_filename, "w", encoding="utf-8") as file:
                    file.write("A* search\n")
                    file.write(
                    f"Steps: {steps}, Node: {nodes_explored}, Time (ms): {time_taken:.2f}, Memory (MB): {memory_used:.2f}\n"
                    )
                    file.write(f"{''.join(path)}\n")

                return path

            if (agent, boxes) in visited:
                continue
            visited.add((agent, boxes))

            for action, next_state in self.get_neighbors((agent, boxes)):
                new_cost = cost + 1
                heapq.heappush(
                    frontier,
                    (
                        new_cost + self.heuristic(next_state[1]),
                        new_cost,
                        next_state,
                        path + [action],
                    ),
                )

        tracemalloc.stop()
        print("⛔ Không tìm thấy giải pháp!")
        return None
    
    def gbfs(self):
        start_time = time.time()
        tracemalloc.start()

        start_state = (self.agent, self.boxes)
        frontier = [(self.heuristic(self.boxes), start_state, [])]  # Chỉ dùng h(n)
        visited = set()
        nodes_explored = 0

        while frontier:
            _, (agent, boxes), path = heapq.heappop(frontier)
            nodes_explored += 1

            if self.is_goal(boxes):
                end_time = time.time()
                current, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()

                steps = len(path)
                time_taken = (end_time - start_time) * 1000
                memory_used = peak / (1024 * 1024)

                output_filename = "output/outputGBFS.txt"  # Tên file output

                with open(output_filename, "w", encoding="utf-8") as file:
                    file.write("Greedy Best-First Search (GBFS)\n")
                    file.write(
                    f"Steps: {steps}, Node: {nodes_explored}, Time (ms): {time_taken:.2f}, Memory (MB): {memory_used:.2f}\n"
                    )
                    file.write(f"{''.join(path)}\n")

                return path

            if (agent, boxes) in visited:
                continue
            visited.add((agent, boxes))

            for action, next_state in self.get_neighbors((agent, boxes)):
                heapq.heappush(
                    frontier,
                    (
                        self.heuristic(next_state[1]),
                        next_state,
                        path + [action],
                    ),  # Chỉ xét h(n)
                )

        tracemalloc.stop()
        print("⛔ Không tìm thấy giải pháp!")
        return None
    
    def solve(self):
        """Triển khai thuật toán giải Sokoban"""
        if self.algorithm == "BFS":
            return self.bfs()
        elif self.algorithm == "DFS":
            return self.dfs()
        elif self.algorithm == "UCS":
            return self.ucs()
        elif self.algorithm == "A*":
            return self.a_star()
        elif self.algorithm == "GBFS":
            return self.gbfs()
        else:
            print("Thuật toán không hợp lệ:", self.algorithm)
            return None

pygame.init()
pygame.mixer.init()

# Cấu hình màn hình
WIDTH, HEIGHT = 800, 600  # Kích thước tổng
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Game Sokoban")

# Tải hình nền menu
background_image = pygame.image.load("images/background.png")
background_image = pygame.transform.scale(background_image, (WIDTH, HEIGHT))  # Đảm bảo ảnh vừa khung hình

# Màu sắc
GRAY = (150, 150, 150)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
YELLOW = (255, 215, 0)
TITLE_COLOR = (255, 140, 0)
SHADOW_COLOR = (139, 69, 19)
PURPLE = (160, 90, 190)
LIGHT_BLUE = (173, 216, 230)

# Font chữ
menu_font = "arial"
title_font = pygame.font.SysFont("arial", 80, bold=True)  # Font lớn cho tiêu đề
font_size = 50

# Danh sách menu
menu_items = ["Play", "Guide", "Exit"]
selected_item = 0

# Load ảnh nền (cần có file ảnh trong thư mục)
background_image = pygame.image.load("images/background.png")  # Đảm bảo file ảnh tồn tại

def show_guide():
    guide_running = True
    guide_font = pygame.font.Font(None, 40)
    guide_text = [
        "How to play:",
        "- Move with arrow keys.",
        "- Push the stone into the target position.",
        "- Press ESC to go back."
    ]

    while guide_running:
        screen.blit(background_image, (0, 0))  # Vẽ lại nền

        # Tạo khung nền bảng hướng dẫn
        pygame.draw.rect(screen, (50, 50, 50), (150, 170, 570, 200), border_radius=10)
        pygame.draw.rect(screen, (255, 215, 0), (150, 170, 570, 200), 3, border_radius=10)  # Viền vàng

        # Hiển thị văn bản hướng dẫn
        for i, line in enumerate(guide_text):
            text_surface = guide_font.render(line, True, (255, 255, 255))
            screen.blit(text_surface, (170, 180 + i * 50))

        pygame.display.flip()

        # Xử lý sự kiện
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                guide_running = False  # Thoát bảng hướng dẫn

# Load video nền 
video_path = "images/video.mp4"  # Đường dẫn tới video
cap = cv2.VideoCapture(video_path)

# Phát nhạc nền
pygame.mixer.music.load("music/backgroundMusic.mp3")  # Thay bằng đường dẫn file nhạc
pygame.mixer.music.play(-1)  # -1 để nhạc lặp vô hạn

clock = pygame.time.Clock()
def show_menu():
    global selected_item
    while True:
        # Đọc frame từ video
        ret, frame = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # Reset video nếu chạy hết
            continue

        # Chuyển đổi frame từ OpenCV (BGR) sang Pygame (RGB)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = np.rot90(frame)  # Xoay ảnh nếu bị sai hướng
        frame = pygame.surfarray.make_surface(frame)

        # Hiển thị video nền
        screen.blit(pygame.transform.scale(frame, (WIDTH, HEIGHT)), (0, 0))

        # Hiển thị tiêu đề "SOKOBAN"
        title_text = title_font.render("SOKOBAN", True, TITLE_COLOR)
        shadow_text = title_font.render("SOKOBAN", True, SHADOW_COLOR)
        screen.blit(shadow_text, (WIDTH // 2 - title_text.get_width() // 2 + 3, 53))
        screen.blit(title_text, (WIDTH // 2 - title_text.get_width() // 2, 50))

        # Danh sách menu
        menu_rects = []
        for i, item in enumerate(menu_items):
            size = 60 if i == selected_item else 50  # Tăng kích thước khi chọn
            temp_font = pygame.font.SysFont(menu_font, size)
            color = YELLOW if i == selected_item else GRAY
            text = temp_font.render(item, True, color)

            text_x = WIDTH // 2 - text.get_width() // 2
            text_y = 200 + i * 80
            menu_rect = pygame.Rect(text_x, text_y, text.get_width(), text.get_height())
            menu_rects.append(menu_rect)

            shadow = temp_font.render(item, True, BLACK)
            screen.blit(shadow, (text_x + 2, text_y + 2))
            screen.blit(text, (text_x, text_y))

        # Xử lý sự kiện
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    selected_item = (selected_item - 1) % len(menu_items)
                elif event.key == pygame.K_DOWN:
                    selected_item = (selected_item + 1) % len(menu_items)
                elif event.key == pygame.K_RETURN:
                    if selected_item == 0:
                        return  # Bắt đầu game
                    elif selected_item == 1:
                        show_guide()  # Hiển thị hướng dẫn
                    elif selected_item == 2:
                        pygame.quit()
                        sys.exit()
            elif event.type == pygame.MOUSEMOTION:
                for i, menu_rect in enumerate(menu_rects):
                    if menu_rect.collidepoint(event.pos):
                        selected_item = i
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    for i, menu_rect in enumerate(menu_rects):
                        if menu_rect.collidepoint(event.pos):
                            selected_item = i
                            if selected_item == 0:
                                return  # Bắt đầu game
                            elif selected_item == 1:
                                show_guide()
                            elif selected_item == 2:
                                pygame.quit()
                                sys.exit()

        pygame.display.flip()
        clock.tick(30)  # Giữ FPS ổn định

# Gọi menu trước khi vào game
show_menu()

# --- GAME CHÍNH ---

# Tải hình ảnh nhân vật theo hướng
worker_up = pygame.image.load('images/charater_up.png')
worker_down = pygame.image.load('images/charater_down.png')
worker_left = pygame.image.load('images/charater_left.png')
worker_right = pygame.image.load('images/charater_right.png')

# Tải hình ảnh nhân vật khi đứng trên dock
worker_docked_up = pygame.image.load('images/charater_dock_up.png')
worker_docked_down = pygame.image.load('images/charater_dock_down.png')
worker_docked_left = pygame.image.load('images/charater_dock_left.png')
worker_docked_right = pygame.image.load('images/charater_dock_right.png')

wall = pygame.image.load('images/wall.png')
floor = pygame.image.load('images/floor.png')
box = pygame.image.load('images/stone.png')
box_docked = pygame.image.load('images/stone_dock.png')
worker = worker_down
worker_docked = worker_docked_down
docker = pygame.image.load('images/dock.png')
background = 255, 226, 191

# Kích thước nút
BUTTON_WIDTH = 100
BUTTON_HEIGHT = 30

# Định nghĩa lớp Button
class Button:
    def __init__(self, x, y, width, height, color, text, text_color):
        self.rect = pygame.Rect(x, y, width, height)
        self.color = color
        self.text = text
        self.text_color = text_color
        self.font = pygame.font.Font(None, 30)
    
    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.rect)
        text_surface = self.font.render(self.text, True, self.text_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)
    
    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)

# Tạo nút
algo_button = Button(50, 500, BUTTON_WIDTH + 10, BUTTON_HEIGHT + 10, PURPLE, "Algorithm", WHITE)
reset_button = Button(600, 500, BUTTON_WIDTH + 10, BUTTON_HEIGHT + 10, LIGHT_BLUE, "Reset", WHITE)
play_button = Button(600, 500, BUTTON_WIDTH + 10, BUTTON_HEIGHT + 10, LIGHT_BLUE, "Weight", WHITE)

# Biến trạng thái để theo dõi menu
menu_open = False
selected_algorithm = None

def select_algorithm():
    global menu_open, selected_algorithm  # Ensure these variables are global
    
    running = True
    screen_width, screen_height = screen.get_size()
    board_width, board_height = 240, 230
    board_x = (screen_width - board_width) // 2
    board_y = (screen_height - board_height) // 2

    while running:
        if menu_open:
            pygame.draw.rect(screen, WHITE, pygame.Rect(board_x, board_y, board_width, board_height))
            pygame.draw.rect(screen, BLACK, pygame.Rect(board_x, board_y, board_width, board_height), 2)

            button_x = board_x + (board_width - BUTTON_WIDTH) // 2  # Căn giữa theo chiều ngang

            bfs_button = Button(button_x, board_y + 20, BUTTON_WIDTH, BUTTON_HEIGHT, PURPLE, "BFS", BLACK)
            dfs_button = Button(button_x, board_y + 60, BUTTON_WIDTH, BUTTON_HEIGHT, PURPLE, "DFS", BLACK)
            ucs_button = Button(button_x, board_y + 100, BUTTON_WIDTH, BUTTON_HEIGHT, PURPLE, "UCS", BLACK)
            a_button = Button(button_x, board_y + 140, BUTTON_WIDTH, BUTTON_HEIGHT, PURPLE, "A*", BLACK)
            gbfs_button = Button(button_x, board_y + 180, BUTTON_WIDTH, BUTTON_HEIGHT, PURPLE, "GBFS", BLACK)

            # Vẽ từng nút riêng lẻ
            bfs_button.draw(screen)
            dfs_button.draw(screen)
            ucs_button.draw(screen)
            a_button.draw(screen)
            gbfs_button.draw(screen)

            pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                menu_open = False
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN:
                x, y = event.pos
                if menu_open:
                    if bfs_button.rect.collidepoint(x, y):
                        selected_algorithm = "BFS"
                    elif dfs_button.rect.collidepoint(x, y):
                        selected_algorithm = "DFS"
                    elif ucs_button.rect.collidepoint(x, y):
                        selected_algorithm = "UCS"
                    elif a_button.rect.collidepoint(x, y):
                        selected_algorithm = "A*"
                    elif gbfs_button.rect.collidepoint(x, y):
                        selected_algorithm = "GBFS"
                    else:
                        continue  # Nếu không bấm vào nút nào thì bỏ qua vòng lặp này
                    
                    menu_open = False  # Đóng menu
                    running = False  # Thoát vòng lặp sau khi chọn

                    # Chạy thuật toán đã chọn
                    solver = SokobanSolver(game.grid, selected_algorithm)
                    solution = solver.solve()
                    
    return selected_algorithm
    
def read_output_file(filename):
    try:
        with open(filename, 'r') as file:
            # Đọc toàn bộ các dòng
            algorithm = file.readline().strip()  # Dòng đầu tiên: Tên thuật toán
            info_line = file.readline().strip()  # Dòng thứ hai: Thông số
            path = file.readline().strip()  # Dòng thứ ba: Mảng bước đi

            return algorithm, info_line, path

    except FileNotFoundError:
        print(f"File not found: {filename}")
    except Exception as e:
        print(f"An error occurred: {e}")

def game_start():
    global current_scr
    global worker
    global worker_docked
    global running
    global selected_algorithm, timeout, start_time, step_count

    current_scr = "Game"
    
    game.load_level()  # Nạp level
    pygame.display.update()
    
    # Đọc dữ liệu từ file output
    if (selected_algorithm == "BFS"):
     algorithm, info_line, path = read_output_file('output/outputBFS.txt')
    if (selected_algorithm == "DFS"):
     algorithm, info_line, path = read_output_file('output/outputDFS.txt')
    if (selected_algorithm == "UCS"):
     algorithm, info_line, path = read_output_file('output/outputUCS.txt')
    if (selected_algorithm == "A*"):
     algorithm, info_line, path = read_output_file('output/outputA_star.txt')
    if (selected_algorithm == "GBFS"):
     algorithm, info_line, path = read_output_file('output/outputGBFS.txt')

    info_font = pygame.font.Font(None, 20)
    info_text = info_font.render(info_line, True, (255, 255, 255))
    info_rect = info_text.get_rect(center=(400, 550))
    screen.blit(info_text, info_rect)

    # Duyệt qua từng bước trong đường đi
    for i in path:
        # Thực hiện kiểm tra sự kiện thoát trong mỗi lần lặp
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                return  # Thoát hoàn toàn khỏi game nếu người dùng muốn thoát
            
        screen.fill((0, 0, 0))  
        screen.blit(info_text, info_rect) 

        # Thực hiện bước di chuyển
        if i == 'U' or i == 'u':
            game.move(0, -1, True)
            worker = worker_up
            worker_docked = worker_docked_up
        elif i == 'D' or i == 'd':
            game.move(0, 1, True)
            worker = worker_down
            worker_docked = worker_docked_down
        elif i == 'L' or i == 'l':
            game.move(-1, 0, True)
            worker = worker_left
            worker_docked = worker_docked_left
        elif i == 'R' or i == 'r':
            game.move(1, 0, True)
            worker = worker_right
            worker_docked = worker_docked_right

        print_game(game.get_matrix(),screen)
        pygame.display.update()

        time.sleep(0.5)
    
    # Hiển thị thông báo khi hoàn thành

    pygame.display.update()

# Tải level
level = start_game()
game = game('level.txt', level)

size = game.load_size()
screen = pygame.display.set_mode(size)

while 1:
    if game.is_completed(): 
        display_end(screen)  # Hiển thị bảng thông báo kết thúc game
        pygame.time.delay(2000)  # Dừng 2 giây để người chơi thấy thông báo
        
        screen = pygame.display.set_mode((WIDTH, HEIGHT))
        #show_menu()  # Quay lại menu chính hoặc khởi động lại game       

        # Chọn level mới
        level = start_game()  # Chọn lại level từ menu
        game.level = level
        game.reset()  # Reset dữ liệu game để chơi lại

        game.load_size()
        print_game(game.get_matrix(),screen)
        pygame.display.update()

    print_game(game.get_matrix(),screen)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit(0)

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP: 
                game.move(0, -1, True)
                worker = worker_up
                worker_docked = worker_docked_up
            elif event.key == pygame.K_DOWN: 
                game.move(0, 1, True)
                worker = worker_down
                worker_docked = worker_docked_down
            elif event.key == pygame.K_LEFT: 
                game.move(-1, 0, True)
                worker = worker_left
                worker_docked = worker_docked_left
            elif event.key == pygame.K_RIGHT: 
                game.move(1, 0, True)
                worker = worker_right
                worker_docked = worker_docked_right
            elif event.key == pygame.K_q: 
                pygame.quit()
                sys.exit(0)
            elif event.key == pygame.K_d: 
                game.unmove()
            elif event.key == pygame.K_r:  # Thêm phím tắt R để reset
                game.reset()

        elif event.type == pygame.MOUSEBUTTONDOWN:
         if reset_button.rect.collidepoint(event.pos):  # Nhấn vào nút "Reset"
          game.reset()  # Quay lại trạng thái ban đầu của trò chơi

         if algo_button.rect.collidepoint(event.pos):   # Nhấn vào nút "Algorithm"
          menu_open = not menu_open  # Mở/đóng menu khi nhấn vào nút "Algorithm"
          select_algorithm()
          game_start()

         if play_button.rect.collidepoint(event.pos):
          game.on_play_button_click()

    pygame.display.update()
