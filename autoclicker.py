import pyautogui
import time
import keyboard
import sys
from pynput import mouse, keyboard as kb
import json

# 设置防故障安全措施
pyautogui.FAILSAFE = True

class ClickRecorder:
    def __init__(self):
        self.recorded_actions = []
        self.is_recording = False
        self.mouse_listener = None
        self.keyboard_listener = None
        self.start_time = None
        self.drag_start = None

    def on_click(self, x, y, button, pressed):
        if not self.is_recording:
            return
        
        current_time = time.time()
        if self.start_time is None:
            self.start_time = current_time
            interval = 0
        else:
            interval = current_time - self.start_time

        button_name = 'left' if button == mouse.Button.left else 'right'
        if pressed:
            if not self.drag_start:
                self.drag_start = (x, y, button_name)
            else:
                # 如果已经有拖动起点，这是一个新的点击，清除拖动状态
                self.drag_start = None
                self.recorded_actions.append({
                    'type': 'click',
                    'x': x,
                    'y': y,
                    'button': button_name,
                    'interval': interval
                })
                print(f"记录{button_name}点击: ({x}, {y})")
        else:  # 释放点击
            if self.drag_start:
                start_x, start_y, start_button = self.drag_start
                if (start_x, start_y) != (x, y):  # 如果起点和终点不同，记录为拖动
                    self.recorded_actions.append({
                        'type': 'drag',
                        'start_x': start_x,
                        'start_y': start_y,
                        'end_x': x,
                        'end_y': y,
                        'button': start_button,
                        'interval': interval
                    })
                    print(f"记录拖动: 从({start_x}, {start_y})到({x}, {y})")
                else:  # 如果起点和终点相同，记录为点击
                    self.recorded_actions.append({
                        'type': 'click',
                        'x': x,
                        'y': y,
                        'button': button_name,
                        'interval': interval
                    })
                    print(f"记录{button_name}点击: ({x}, {y})")
                self.drag_start = None

    def on_key(self, key):
        if not self.is_recording:
            return

        try:
            current_time = time.time()
            if self.start_time is None:
                self.start_time = current_time
                interval = 0
            else:
                interval = current_time - self.start_time

            if hasattr(key, 'char'):
                key_char = key.char
            else:
                key_char = str(key)

            self.recorded_actions.append({
                'type': 'key',
                'key': key_char,
                'interval': interval
            })
            print(f"记录按键: {key_char}")
        except AttributeError:
            pass

    def start_recording(self):
        if not self.is_recording:
            self.is_recording = True
            self.recorded_actions = []
            self.start_time = None
            self.drag_start = None
            self.mouse_listener = mouse.Listener(on_click=self.on_click)
            self.keyboard_listener = kb.Listener(on_press=self.on_key)
            self.mouse_listener.start()
            self.keyboard_listener.start()
            print("开始录制...")

    def stop_recording(self):
        if self.is_recording:
            self.is_recording = False
            if self.mouse_listener:
                self.mouse_listener.stop()
            if self.keyboard_listener:
                self.keyboard_listener.stop()
            print("停止录制")

    def save_recording(self, filename="clicks.json"):
        if self.recorded_actions:
            with open(filename, 'w') as f:
                json.dump(self.recorded_actions, f)
            print(f"录制已保存到 {filename}")
            return True
        else:
            print("没有记录到动作")
            return False

def play_recorded_actions(filename="clicks.json"):
    try:
        with open(filename, 'r') as f:
            actions = json.load(f)
        
        print("开始播放录制的动作...")
        
        last_time = 0
        for action in actions:
            # 等待到指定的时间间隔
            wait_time = action['interval'] - last_time
            if wait_time > 0:
                time.sleep(wait_time)
            
            if action['type'] == 'click':
                if action['button'] == 'left':
                    pyautogui.click(x=action['x'], y=action['y'])
                else:
                    pyautogui.rightClick(x=action['x'], y=action['y'])
            elif action['type'] == 'drag':
                pyautogui.mouseDown(x=action['start_x'], y=action['start_y'], button=action['button'])
                pyautogui.moveTo(action['end_x'], action['end_y'], duration=0.2)
                pyautogui.mouseUp()
            elif action['type'] == 'key':
                pyautogui.press(action['key'])
            
            last_time = action['interval']
            
        print("播放完成")
        return True
    except FileNotFoundError:
        print("未找到录制文件")
    except json.JSONDecodeError:
        print("录制文件格式错误")
    except Exception as e:
        print(f"播放时发生错误: {str(e)}")
    return False

def main():
    print("自动点击录制/播放程序")
    print("按 'F2' 开始录制")
    print("按 'F3' 停止录制并保存")
    print("按 'F4' 播放录制")
    print("按 'Esc' 退出程序")
    print("支持左键、右键点击、拖动和键盘按键")
    
    recorder = ClickRecorder()
    
    try:
        while True:
            # 开始录制
            if keyboard.is_pressed('F2'):
                recorder.start_recording()
                time.sleep(0.5)
            
            # 停止录制并保存
            elif keyboard.is_pressed('F3'):
                recorder.stop_recording()
                recorder.save_recording()
                time.sleep(0.5)
            
            # 播放录制
            elif keyboard.is_pressed('F4'):
                if recorder.is_recording:
                    print("请先停止录制（按'F3'）")
                else:
                    play_recorded_actions()
                time.sleep(0.5)
                
            # 检查 Esc 键来退出程序
            elif keyboard.is_pressed('Esc'):
                print("程序已退出!")
                if recorder.is_recording:
                    recorder.stop_recording()
                sys.exit()
                
    except KeyboardInterrupt:
        print("程序已终止!")
        if recorder.is_recording:
            recorder.stop_recording()
        sys.exit()
    except Exception as e:
        print(f"发生错误: {str(e)}")
        if recorder.is_recording:
            recorder.stop_recording()
        sys.exit(1)

if __name__ == "__main__":
    main() 