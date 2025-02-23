import requests
import json
import time
from pathlib import Path
import logging
import sys
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import asyncio
import aiohttp
from datetime import datetime
import re
import tkinter as tk
from tkinter import ttk, scrolledtext
from queue import Queue
import threading

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def clean_folder_name(title: str) -> str:
    """清理文件夹名称，移除非法字符和emoji
    Args:
        title: 原始标题
    Returns:
        清理后的文件夹名称
    """
    # 移除emoji
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        "]+", flags=re.UNICODE)
    title = emoji_pattern.sub('', title)
    
    # 移除Windows文件系统非法字符
    title = re.sub(r'[<>:"/\\|?*]', '', title)
    
    # 移除其他可能导致问题的字符
    title = re.sub(r'[^\w\s\-_\u4e00-\u9fff]', '', title)
    
    # 移除首尾空白字符
    title = title.strip()
    
    # 如果标题为空，返回默认名称
    if not title:
        return "未命名文章"
    
    return title

def get_next_folder_number(base_dir: Path) -> int:
    """获取下一个可用的文件夹编号"""
    existing_folders = [d for d in base_dir.iterdir() if d.is_dir() and d.name.isdigit()]
    if not existing_folders:
        return 1
    return max(int(d.name) for d in existing_folders) + 1

async def generate_content(topic: str, style: str = "干货分享") -> dict:
    """生成单个话题的内容"""
    url = "http://localhost:8000/generate"
    
    async with aiohttp.ClientSession() as session:
        try:
            # 第一次请求 - 生成标题页
            logger.info(f"正在生成话题 '{topic}' 的标题页...")
            async with session.post(url, json={
                "topic": topic,
                "style": style,
                "page_index": "0"
            }, timeout=120) as response:
                if response.status != 200:
                    logger.error(f"生成标题页失败: HTTP {response.status}")
                    return None
                
                result = await response.json()
                request_id = result["request_id"]
                total_pages = result["total_pages"]
                
                # 获取标题内容
                title_content = result.get("title", "")
                if not title_content:
                    title_content = result.get("content", topic)
                
                # 确保 image 目录存在
                base_dir = Path("image")
                base_dir.mkdir(parents=True, exist_ok=True)
                
                # 获取下一个可用的文件夹编号
                folder_number = get_next_folder_number(base_dir)
                topic_dir = base_dir / str(folder_number)
                topic_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"创建目录: {topic_dir}")
                
                try:
                    # 移动生成的图片到话题目录
                    src_image = Path(result["image_path"])
                    if src_image.exists():
                        dst_image = topic_dir / src_image.name
                        src_image.rename(dst_image)
                        logger.info(f"移动图片到: {dst_image}")
                    else:
                        logger.error(f"源图片不存在: {src_image}")
                except Exception as e:
                    logger.error(f"移动图片时出错: {str(e)}")
                
                # 收集内容数据（包含原始标题）
                content_data = {
                    "folder_number": folder_number,
                    "title": title_content,
                    "topic": topic,
                    "content": [],
                    "hashtags": []
                }
                
                logger.info(f"标题页生成完成")
                await asyncio.sleep(2)
            
            # 生成所有内容页（从第1页开始）
            for page_index in range(1, total_pages + 1):
                logger.info(f"正在生成第 {page_index}/{total_pages} 页...")
                
                async with session.post(url, json={
                    "topic": topic,
                    "style": style,
                    "request_id": request_id,
                    "page_index": str(page_index)
                }, timeout=120) as response:
                    if response.status != 200:
                        logger.error(f"生成内容页失败: HTTP {response.status}")
                        continue
                    
                    result = await response.json()
                    
                    # 移动生成的图片到话题目录
                    src_image = Path(result["image_path"])
                    dst_image = topic_dir / src_image.name
                    src_image.rename(dst_image)
                    
                    # 获取内容数据
                    content_data["content"].append(result.get("content", ""))
                    if page_index == total_pages:
                        content_data["hashtags"] = result.get("hashtags", [])
                    
                    logger.info(f"第 {page_index} 页生成完成")
                    await asyncio.sleep(2)
            
            # 保存内容数据到JSON文件
            json_path = topic_dir / "content.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(content_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"话题 '{title_content}' 的所有内容生成完成")
            logger.info("-----------------------------------")
            return content_data
            
        except Exception as e:
            logger.error(f"生成过程发生错误: {str(e)}", exc_info=True)
            return None

async def generate_multiple_topics(topics: list[str], style: str = "干货分享"):
    """按顺序生成多个话题的内容"""
    # 检查服务器状态
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8000/docs") as response:
                if response.status != 200:
                    logger.error("无法连接到服务器，请确保服务器正在运行")
                    logger.info("请先运行 python xiaohongshu_generator.py 启动服务器")
                    return
    except Exception:
        logger.error("无法连接到服务器，请确保服务器正在运行")
        return
    
    successful = 0
    total = len(topics)
    
    # 顺序生成每个话题
    for index, topic in enumerate(topics, 1):
        logger.info("===================================")
        logger.info(f"开始生成第 {index}/{total} 个话题: {topic}")
        logger.info("===================================")
        
        result = await generate_content(topic, style)
        
        if result is not None:
            successful += 1
            logger.info(f"话题 '{topic}' 生成成功")
        else:
            logger.error(f"话题 '{topic}' 生成失败")
        
        # 在话题之间添加短暂延迟
        if index < total:
            logger.info("等待2秒后开始生成下一个话题...")
            await asyncio.sleep(2)
    
    # 统计结果
    logger.info("===================================")
    logger.info(f"全部生成完成: {successful}/{total} 个话题成功")
    logger.info("===================================")

def get_user_input():
    """获取用户输入的话题和执行次数"""
    print("\n=== 小红书文章生成器 ===")
    topics = []
    
    while True:
        topic = input("\n请输入话题（直接回车结束输入）: ").strip()
        if not topic:
            if not topics:
                print("至少需要输入一个话题！")
                continue
            break
        
        times = input(f"请输入该话题需要生成的次数（默认1次）: ").strip()
        try:
            times = int(times) if times else 1
            if times < 1:
                print("次数必须大于0，已设置为1次")
                times = 1
        except ValueError:
            print("输入的次数无效，已设置为1次")
            times = 1
        
        # 将话题添加指定次数
        topics.extend([topic] * times)
        print(f"已添加话题: {topic} ({times}次)")
    
    print("\n=== 话题列表 ===")
    for i, topic in enumerate(topics, 1):
        print(f"{i}. {topic}")
    print(f"共 {len(topics)} 个任务")
    
    return topics

class RedBookGeneratorUI:
    def __init__(self, root):
        self.root = root
        self.root.title("小红书文章生成器")
        self.root.geometry("800x600")
        
        # 创建消息队列用于日志显示
        self.log_queue = Queue()
        
        # 加载字体目录中的字体
        self.fonts_dir = Path("fonts")
        self.title_fonts = self.load_fonts("title")  # 标题字体目录
        self.content_title_fonts = self.load_fonts("content_title")  # 内容页标题字体
        self.content_body_fonts = self.load_fonts("content_body")  # 内容页正文字体
        
        self.setup_ui()
        self.setup_logging()
        self.check_log_queue()
    
    def load_fonts(self, font_type: str) -> dict:
        """从fonts目录加载字体"""
        fonts = {}
        font_dir = self.fonts_dir / font_type
        
        # 尝试从子目录加载
        if font_dir.exists():
            for font_file in font_dir.glob("*.ttf"):
                display_name = font_file.stem
                fonts[display_name] = str(font_file.relative_to(self.fonts_dir))
        
        # 如果子目录为空，尝试从根目录加载
        if not fonts:
            for font_file in self.fonts_dir.glob("*.ttf"):
                display_name = font_file.stem
                fonts[display_name] = font_file.name
        
        # 如果还是没有找到字体，使用默认值
        if not fonts:
            logger.warning(f"未找到{font_type}字体，使用默认值")
            if font_type == "title":
                fonts = {"默认标题字体": "title/优设标题黑.ttf"}
            elif font_type == "content_title":
                fonts = {"默认内容标题字体": "content_title/优设标题黑.ttf"}
            else:
                fonts = {"默认正文字体": "content_body/No.14-上首水滴体.ttf"}
        
        return fonts
    
    def setup_ui(self):
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 字体选择区域
        font_frame = ttk.LabelFrame(main_frame, text="字体设置", padding="5")
        font_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E))
        
        # 标题页字体选择
        ttk.Label(font_frame, text="标题页字体:").grid(row=0, column=0, padx=5)
        self.title_font_var = tk.StringVar(value=list(self.title_fonts.keys())[0])
        title_font_combo = ttk.Combobox(font_frame, textvariable=self.title_font_var, values=list(self.title_fonts.keys()), state='readonly', width=20)
        title_font_combo.grid(row=0, column=1, padx=5)
        
        # 内容页标题字体选择
        ttk.Label(font_frame, text="内容页标题字体:").grid(row=0, column=2, padx=5)
        self.content_title_font_var = tk.StringVar(value=list(self.content_title_fonts.keys())[0])
        content_title_font_combo = ttk.Combobox(font_frame, textvariable=self.content_title_font_var, values=list(self.content_title_fonts.keys()), state='readonly', width=20)
        content_title_font_combo.grid(row=0, column=3, padx=5)
        
        # 内容页正文字体选择
        ttk.Label(font_frame, text="内容页正文字体:").grid(row=1, column=0, padx=5)
        self.content_body_font_var = tk.StringVar(value=list(self.content_body_fonts.keys())[0])
        content_body_font_combo = ttk.Combobox(font_frame, textvariable=self.content_body_font_var, values=list(self.content_body_fonts.keys()), state='readonly', width=20)
        content_body_font_combo.grid(row=1, column=1, padx=5)
        
        # 话题输入区域
        topic_frame = ttk.LabelFrame(main_frame, text="话题输入", padding="5")
        topic_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E))
        
        ttk.Label(topic_frame, text="话题:").grid(row=0, column=0, padx=5)
        self.topic_entry = ttk.Entry(topic_frame, width=40)
        self.topic_entry.grid(row=0, column=1, padx=5)
        
        ttk.Label(topic_frame, text="生成次数:").grid(row=0, column=2, padx=5)
        self.times_entry = ttk.Entry(topic_frame, width=10)
        self.times_entry.insert(0, "1")
        self.times_entry.grid(row=0, column=3, padx=5)
        
        ttk.Button(topic_frame, text="添加话题", command=self.add_topic).grid(row=0, column=4, padx=5)
        
        # 话题列表
        list_frame = ttk.LabelFrame(main_frame, text="待生成话题列表", padding="5")
        list_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.topic_list = tk.Listbox(list_frame, height=10)
        self.topic_list.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        list_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.topic_list.yview)
        list_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.topic_list.configure(yscrollcommand=list_scroll.set)
        
        # 控制按钮
        button_frame = ttk.Frame(main_frame, padding="5")
        button_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E))
        
        ttk.Button(button_frame, text="清空列表", command=self.clear_topics).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="开始生成", command=self.start_generation).grid(row=0, column=1, padx=5)
        ttk.Button(button_frame, text="打开文件夹", command=self.open_image_folder).grid(row=0, column=2, padx=5)
        
        # 日志显示区域
        log_frame = ttk.LabelFrame(main_frame, text="生成日志", padding="5")
        log_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置grid权重
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1)
        list_frame.columnconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
    
    # ... 其他方法保持不变 ...

if __name__ == "__main__":
    try:
        # 获取用户输入的话题和次数
        topics = get_user_input()
        
        # 确认是否开始生成
        confirm = input("\n确认开始生成？(y/n): ").strip().lower()
        if confirm != 'y':
            print("已取消生成")
            sys.exit(0)
        
        print("\n开始生成...")
        # 运行生成任务
        asyncio.run(generate_multiple_topics(topics))
        
    except KeyboardInterrupt:
        print("\n已中断生成过程")
        sys.exit(1)
    except Exception as e:
        print(f"\n发生错误: {str(e)}")
        sys.exit(1) 