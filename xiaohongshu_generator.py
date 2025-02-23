from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import os
from datetime import datetime
import pyautogui
import time
from pathlib import Path
import jinja2
import json
import asyncio
import logging
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import emoji
import random
import math

app = FastAPI()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 修改保存目录配置
SAVE_DIR = Path("generated_content")
IMAGE_DIR = SAVE_DIR / "image"  # 添加图片目录
HTML_DIR = SAVE_DIR  # HTML文件仍保存在根目录

# Ollama配置
OLLAMA_URL = "http://localhost:11434"
MODEL_NAME = "deepseek-r1:1.5b"

# 修改标题页模板
title_template_str = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        @font-face {
            font-family: 'YouSheTitleBlack';
            src: url('优设标题黑.ttf') format('truetype');
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            margin: 0;
            padding: 20px;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            background: #f5f5f5;
        }
        
        .content-box {
            width: 975px;
            height: 1300px;
            position: relative;
            overflow: hidden;
            background-image: url('bg1.jpg');
            background-size: cover;
            background-position: center;
            display: flex;
            align-items: center;
        }
        
        .title-wrapper {
            width: 100%;
            padding: 60px;
        }
        
        .title {
            font-family: 'YouSheTitleBlack', sans-serif;
            font-size: 150px;
            color: #000;
            line-height: 1;
            text-align: center;
            padding: 40px;
            white-space: pre-line;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
            font-weight: normal;
        }
    </style>
</head>
<body>
    <div class="content-box">
        <div class="title-wrapper">
            <div class="title">{{ title }}</div>
        </div>
    </div>
</body>
</html>
"""

# 修改内容页模板
content_template_str = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        @font-face {
            font-family: 'ShangShouYuYuan';
            src: url('No.14-上首水滴体.ttf') format('truetype');
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            margin: 0;
            padding: 20px;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }
        
        .content-box {
            width: 975px;
            height: 1300px;
            position: relative;
            overflow: hidden;
            background-image: url('bg1.jpg');
            background-size: cover;
            background-position: center;
        }
        
        .content-wrapper {
            width: 100%;
            height: 100%;
            padding: 40px;
            background: rgba(255, 255, 255, 0);  /* 降低白色背景的不透明度 */
            backdrop-filter: blur(1px);  /* 减小模糊程度 */
            display: flex;
            flex-direction: column;
        }
        
        .title {
            font-family: 'ShangShouYuYuan', sans-serif;
            font-size: 32px;
            font-weight: 700;
            color: #333;
            text-align: center;
            margin-top: 30px;  /* 增加顶部边距 */
            margin-bottom: 30px;
        }
        
        .content {
            flex: 1;
            font-family: 'ShangShouYuYuan', sans-serif;
            font-size: 24px;
            line-height: 1.8;
            color: #333;
            display: flex;
            flex-direction: column;
            gap: 25px;
            padding: 30px 0;  /* 将顶部内边距从20px增加到30px */
        }
        
        .paragraph {
            margin: 0;
            padding: 25px 30px;
            text-align: justify;
            background: rgba(255, 255, 255, 0.9);  /* 白色半透明背景 */
            border-radius: 20px;  /* 增大圆角 */
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);  /* 轻微阴影 */
            backdrop-filter: blur(5px);  /* 背景模糊效果 */
            border: 2px solid rgba(0, 0, 0, 0.8);  /* 黑色描边 */
            position: relative;  /* 为伪元素定位 */
        }
        
        /* 添加双层效果 */
        .paragraph::before {
            content: '';
            position: absolute;
            top: -2px;
            left: -2px;
            right: -2px;
            bottom: -2px;
            border-radius: 20px;  /* 与段落相同的圆角 */
            border: 1px solid rgba(0, 0, 0, 0.3);  /* 外层淡黑色边框 */
            pointer-events: none;  /* 确保不影响交互 */
        }
        
        .hashtags {
            font-family: 'ShangShouYuYuan', sans-serif;
            margin-top: auto;
            padding: 15px;
            font-size: 20px;
            color: #666;
            text-align: center;
            background: rgba(255, 255, 255, 0.9);
            border-radius: 15px;
            backdrop-filter: blur(5px);
            border: 2px solid rgba(0, 0, 0, 0.8);  /* 与段落相同的边框样式 */
        }
        
        .macaron-text {
            font-weight: 500;
            text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.8);
        }
    </style>
</head>
<body>
    <div class="content-box">
        <div class="content-wrapper">
            <div class="title">{{ title }}</div>
            <div class="content">
            {% for para in content.split('\n\n') %}
                {% if para.strip() %}
                <div class="paragraph">{{ para }}</div>
                {% endif %}
            {% endfor %}
            </div>
            {% if hashtags %}
            <div class="hashtags">{{ hashtags }}</div>
            {% endif %}
        </div>
    </div>
</body>
</html>
"""

# 创建Jinja2模板
title_template = jinja2.Template(title_template_str)
content_template = jinja2.Template(content_template_str)

class ContentRequest(BaseModel):
    topic: str
    style: str = "轻松活泼"
    system_prompt: str = ""
    request_id: str = ""
    page_index: str = "0"  # 添加页面索引字段

# 使用字典来跟踪每个用户的生成状态
user_generation_states = {}

async def check_ollama_status():
    """检查Ollama服务是否可用"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{OLLAMA_URL}/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                if not any(model["name"] == MODEL_NAME for model in models):
                    print(f"警告: 模型 {MODEL_NAME} 未找到，请先下载")
                return True
    except Exception as e:
        print(f"Ollama服务未启动: {str(e)}")
        return False

async def generate_with_ollama(prompt: str) -> str:
    """使用Ollama生成内容"""
    if not await check_ollama_status():
        logger.error("Ollama服务未启动")
        raise HTTPException(status_code=503, detail="Ollama服务未启动")

    async with httpx.AsyncClient(timeout=60.0) as client:  # 增加超时时间
        try:
            logger.info("开始请求Ollama API")
            response = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": MODEL_NAME,
                    "prompt": prompt,
                    "stream": True,
                    "temperature": 0.7,  # 添加温度参数
                    "max_tokens": 500    # 限制生成长度
                }
            )
            response.raise_for_status()
            
            logger.info("开始接收流式响应")
            full_response = ""
            async for line in response.aiter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        if "response" in data:
                            full_response += data["response"]
                            print(".", end="", flush=True)
                        if "error" in data:  # 检查错误信息
                            logger.error(f"Ollama返回错误: {data['error']}")
                            raise HTTPException(status_code=500, detail=data['error'])
                    except json.JSONDecodeError as e:
                        logger.warning(f"JSON解析错误: {str(e)}, line: {line}")
                        continue

            if not full_response.strip():
                logger.error("生成的内容为空")
                raise HTTPException(status_code=500, detail="生成的内容为空")

            logger.info("生成完成")
            return full_response

        except httpx.TimeoutException as e:
            logger.error(f"请求超时: {str(e)}")
            raise HTTPException(status_code=504, detail="生成超时，请重试")
        except Exception as e:
            logger.error(f"生成过程发生错误: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Ollama API错误: {str(e)}")

def get_element_position(html_path):
    """获取内容盒子的位置"""
    import pyautogui
    import time
    
    os.system(f"start {html_path}")
    time.sleep(4)  # 等待页面加载
    
    screen_width, screen_height = pyautogui.size()
    
    # 计算975x1300的div在屏幕上的位置
    # 假设div在页面中居中显示
    x = (screen_width - 975) // 2
    y = (screen_height - 1300) // 2
    if y < 0:  # 如果高度超出屏幕，从顶部开始
        y = 20  # 给定一个小的上边距
    
    return x, y, 975, 1300

def add_emojis_and_styling(text: str) -> str:
    """添加emoji装饰和马卡龙色系文字样式"""
    # 马卡龙色系列表
    macaron_colors = [
        '#FFB6C1',  # 浅粉红
        '#FFD700',  # 金色
        '#87CEEB',  # 天蓝色
        '#DDA0DD',  # 梅红色
        '#98FB98',  # 浅绿色
        '#FFA07A',  # 浅鲑鱼色
        '#F0E68C',  # 卡其色
        '#E6E6FA',  # 淡紫色
        '#FFC3A0',  # 浅橙色
        '#A6E7FF',  # 浅蓝色
        '#FFB7B2',  # 浅珊瑚色
        '#B5EAD7',  # 薄荷绿
        '#FFDAC1',  # 浅桃色
        '#C7CEEA',  # 淡蓝紫色
        '#E2F0CB'   # 浅黄绿色
    ]
    
    # 装饰性emoji
    decorative_emojis = [
        '🍭', '🍬', '🎀', '🌸', '🌺', '🌷', '🌹', '🌈', '✨', 
        '🦄', '🎠', '🎪', '🎨', '🍡', '🧁', '🍰', '🎂', '🍪'
    ]
    
    # 在每个段落中随机给词语添加颜色
    lines = text.split('\n')
    decorated_lines = []
    
    for line in lines:
        if line.strip():
            # 添加段落装饰emoji
            start_emoji = random.choice(decorative_emojis)
            end_emoji = random.choice(decorative_emojis)
            
            # 将句子分成词语
            words = line.split()
            decorated_words = []
            
            for word in words:
                # 35%的概率给词语添加随机马卡龙色
                if random.random() < 0.35:
                    color = random.choice(macaron_colors)
                    decorated_words.append(
                        f'<span class="macaron-text" style="color: {color};">{word}</span>'
                    )
                else:
                    decorated_words.append(word)
            
            # 重新组合句子
            decorated_line = ' '.join(decorated_words)
            line = f"{start_emoji} {decorated_line} {end_emoji}"
            
        decorated_lines.append(line)
    
    # 使用emoji库转换emoji短代码
    text = '\n'.join(decorated_lines)
    text = emoji.emojize(text, language='alias')
    
    return text

def save_html_and_capture_div(content: str, hashtags: str, is_first: bool = False, title: str = "", page_index: int = 0) -> tuple[str, str]:
    """保存HTML并捕获指定div为图片"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 确保字体文件和背景图片存在并复制
    font_files = {
        Path("优设标题黑.ttf"): "标题字体",
        Path("No.42-上首芋圆体.ttf"): "内容字体",
        Path("bg1.jpg"): "背景图片"
    }
    
    # 检查所有必需文件
    for file_path, desc in font_files.items():
        if not file_path.exists():
            raise FileNotFoundError(f"找不到{desc}文件: {file_path}")
    
    # 复制资源文件到HTML目录
    for resource in font_files.keys():
        dest = HTML_DIR / resource.name
        if not dest.exists():
            import shutil
            shutil.copy2(resource, dest)
    
    # 修改文件命名逻辑
    file_prefix = "title" if is_first else "content"
    html_path = HTML_DIR / f"{file_prefix}_{timestamp}.html"
    # 图片按页码命名：标题页为1.png，内容页从2.png开始
    image_name = f"{page_index + 1}.png"
    image_path = IMAGE_DIR / image_name
    
    logger.info(f"正在生成{'标题' if is_first else '内容'}页面")
    logger.info(f"HTML路径: {html_path}")
    logger.info(f"图片路径: {image_path}")
    
    # 渲染模板
    template = title_template if is_first else content_template
    if is_first:
        # 标题页渲染
        html_content = template.render(
            title=content  # 对于标题页，content就是标题内容
        )
    else:
        # 内容页渲染
        html_content = template.render(
            title=title,
            content=content,
            hashtags=hashtags
        )
    
    # 保存HTML
    try:
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
            logger.info("HTML已生成")
    except Exception as e:
        logger.error(f"HTML生成错误: {str(e)}")
        raise
    
    # 设置Chrome选项
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--hide-scrollbars')
    chrome_options.add_argument(f'--window-size=1200,1600')
    chrome_options.add_argument('--disable-web-security')  # 添加此选项以允许跨域
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        file_url = html_path.absolute().as_uri()
        driver.get(file_url)
        
        # 等待内容盒子加载完成
        content_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "content-box"))
        )
        
        # 注入html2canvas库
        driver.execute_script("""
            return new Promise((resolve, reject) => {
                var script = document.createElement('script');
                script.src = 'https://html2canvas.hertzen.com/dist/html2canvas.min.js';
                script.onload = resolve;
                script.onerror = reject;
                document.body.appendChild(script);
            });
        """)
        
        # 等待html2canvas加载完成
        time.sleep(2)
        
        # 执行截图并等待结果
        result = driver.execute_script("""
            return new Promise((resolve, reject) => {
                const element = document.querySelector('.content-box');
                if (!element) {
                    reject('Content box not found');
                    return;
                }
                
                html2canvas(element, {
                    width: 975,
                    height: 1300,
                    scale: 2,
                    useCORS: true,
                    allowTaint: true,
                    backgroundColor: null,
                    logging: true,
                    onclone: function(clonedDoc) {
                        // 确保背景图片已加载
                        const images = clonedDoc.getElementsByTagName('img');
                        return Promise.all(Array.from(images).map(img => {
                            if (img.complete) return Promise.resolve();
                            return new Promise(resolve => {
                                img.onload = resolve;
                                img.onerror = resolve;
                            });
                        }));
                    }
                }).then(canvas => {
                    resolve(canvas.toDataURL('image/png'));
                }).catch(error => {
                    reject(error);
                });
            });
        """)
        
        if not result:
            raise ValueError("Failed to generate image")
        
        # 移除base64头部描述
        img_data = result.replace('data:image/png;base64,', '')
        
        # 保存图片到image子目录
        import base64
        with open(image_path, 'wb') as f:
            f.write(base64.b64decode(img_data))
        
        logger.info(f"图片已保存到: {image_path}")
        
    except Exception as e:
        logger.error(f"图片生成错误: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"图片生成错误: {str(e)}")
    
    finally:
        driver.quit()
    
    return str(html_path), str(image_path)

# 修改分页函数
def calculate_content_pages(content: str, max_height: int = 1100) -> list[str]:
    """根据内容长度动态分页，确保内容不会被裁剪"""
    paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
    pages = []
    current_page = []
    estimated_height = 0
    
    # 调整参数使排版更紧凑
    font_size = 24
    line_height = 1.4  # 进一步减小行高
    padding = 25  # 减小段落内边距
    chars_per_line = 40  # 增加每行字符数
    margin_between_paragraphs = 15  # 减小段落间距
    title_height = 80  # 标题占用高度
    hashtags_height = 50  # 标签占用高度
    
    # 计算可用内容区域高度
    available_height = max_height - title_height - hashtags_height
    
    for para in paragraphs:
        # 估算当前段落高度（考虑emoji和样式标签的影响）
        effective_length = len(para) + (para.count('🌸') + para.count('✨') + para.count('🍭')) * 2
        lines = math.ceil(effective_length / chars_per_line)
        para_height = (lines * font_size * line_height) + padding
        
        # 如果不是第一段，添加段落间距
        if current_page:
            para_height += margin_between_paragraphs
        
        # 尝试添加到当前页
        if estimated_height + para_height <= available_height or not current_page:
            current_page.append(para)
            estimated_height += para_height
        else:
            # 如果当前段落太长，尝试拆分
            if len(para) > chars_per_line * 2:  # 只拆分较长的段落
                words = para.split()
                first_part = []
                second_part = []
                current_length = 0
                
                for word in words:
                    if current_length + len(word) <= chars_per_line * 2:
                        first_part.append(word)
                        current_length += len(word) + 1
                    else:
                        second_part.append(word)
                
                if first_part:
                    current_page.append(' '.join(first_part))
                    pages.append('\n\n'.join(current_page))
                    current_page = [' '.join(second_part)] if second_part else []
                    estimated_height = para_height
                else:
                    pages.append('\n\n'.join(current_page))
                    current_page = [para]
                    estimated_height = para_height
            else:
                pages.append('\n\n'.join(current_page))
                current_page = [para]
                estimated_height = para_height
    
    # 添加最后一页
    if current_page:
        pages.append('\n\n'.join(current_page))
    
    return pages

# 修改生成内容的处理逻辑
@app.post("/generate")
async def generate_content(request: ContentRequest):
    """生成小红书风格的内容"""
    request_id = request.request_id or datetime.now().strftime("%Y%m%d_%H%M%S")
    page_index = int(request.page_index) if request.page_index else 0
    is_first = (page_index == 0)
    
    # 从用户状态中获取或创建HTML文件列表
    if request_id not in user_generation_states:
        user_generation_states[request_id] = {
            "html_files": []  # 用于跟踪该请求生成的所有HTML文件
        }
    
    try:
        logger.info(f"收到生成请求 - 主题: {request.topic}, 风格: {request.style}")
        logger.info(f"请求ID: {request_id}, 页面索引: {page_index}")
        
        if page_index == 0:  # 标题页
            # 生成内容
            prompt = request.system_prompt + f"\n\n主题：{request.topic}\n风格：{request.style}" if request.system_prompt else f"""
            请你扮演一个90后小红书博主，围绕主题"{request.topic}"创作一篇{request.style}风格的文案。
            要求：
            1. 文案总字数控制在5000字之间
            2. 标题要简短吸引人，带有emoji，最多10字，需要能自然分成三行，标题严格限制在10字以内！
            3. 正文分段阐述，每段都要带emoji
            4. 使用网络流行语，要有年轻人的语气
            5. 内容要接地气，像朋友在聊天
            6. 每段都要简短有力，突出重点
            7. 使用中文标点符号
            """
            
            generated_text = await generate_with_ollama(prompt)
            generated_text = clean_content(generated_text)
            
            # 分离标题和内容
            lines = generated_text.splitlines()
            title = lines[0].strip() if lines else ""
            content = '\n\n'.join(lines[1:]) if len(lines) > 1 else ""
            
            logger.info(f"生成的标题: {title}")  # 添加日志
            
            # 处理内容，添加emoji和样式
            decorated_content = add_emojis_and_styling(content)
            
            # 分页处理
            content_pages = calculate_content_pages(decorated_content)
            total_pages = len(content_pages)
            
            logger.info(f"内容已分为 {total_pages} 页")
            
            # 生成标题页
            html_path, image_path = save_html_and_capture_div(
                content=title,
                hashtags="",
                is_first=True,
                title=title,
                page_index=0
            )
            # 记录HTML文件路径
            user_generation_states[request_id]["html_files"].append(html_path)
            
            # 更新状态
            user_generation_states[request_id].update({
                "title": title,
                "content_pages": content_pages,
                "total_pages": total_pages,
                "current_page": 0,
                "timestamp": datetime.now()
            })
            
            return {
                "status": "success",
                "html_path": html_path,
                "image_path": image_path,
                "is_first": is_first,
                "request_id": request_id,
                "page_index": page_index,
                "total_pages": total_pages,
                "title": title,  # 确保返回标题
                "content": title,  # 对于标题页，content就是标题内容
                "hashtags": []
            }
        
        else:  # 内容页
            if request_id not in user_generation_states:
                raise HTTPException(status_code=400, detail=f"无效的请求ID: {request_id}")
            
            state = user_generation_states[request_id]
            title = state["title"]
            content_pages = state["content_pages"]
            total_pages = state["total_pages"]
            
            if page_index > total_pages:
                raise HTTPException(status_code=400, detail=f"页面索引超出范围: {page_index}/{total_pages}")
            
            # 获取当前页内容
            current_page_content = content_pages[page_index - 1]
            
            # 移除话题标签，只在最后一页显示生活分享标签
            hashtags = ["#生活分享"] if page_index == total_pages else []
            hashtags_text = ' '.join(hashtags)
            
            # 生成内容页
            html_path, image_path = save_html_and_capture_div(
                current_page_content,
                hashtags_text,
                is_first=False,
                title=title,
                page_index=page_index
            )
            # 记录HTML文件路径
            user_generation_states[request_id]["html_files"].append(html_path)
            
            # 如果是最后一页，清理所有HTML文件
            if page_index == total_pages:
                # 清理该请求生成的所有HTML文件
                html_files = user_generation_states[request_id]["html_files"]
                for html_file in html_files:
                    try:
                        Path(html_file).unlink()
                        logger.info(f"已清理HTML文件: {html_file}")
                    except Exception as e:
                        logger.warning(f"清理HTML文件失败: {str(e)}")
                
                # 清理状态
                del user_generation_states[request_id]
                logger.info("所有页面生成完成，已清理HTML文件和状态")
        
        return {
            "status": "success",
            "html_path": html_path,
            "image_path": image_path,
            "is_first": is_first,
            "request_id": request_id,
            "page_index": page_index,
            "total_pages": total_pages,
            "title": title if page_index == 1 else None,  # 只在第一页返回标题
            "content": current_page_content if not is_first else None,
            "hashtags": hashtags if page_index == total_pages else []
        }
        
    except Exception as e:
        # 发生错误时也清理HTML文件
        if request_id in user_generation_states:
            html_files = user_generation_states[request_id]["html_files"]
            for html_file in html_files:
                try:
                    Path(html_file).unlink()
                    logger.info(f"错误处理时清理HTML文件: {html_file}")
                except Exception as clean_error:
                    logger.warning(f"清理HTML文件失败: {str(clean_error)}")
            del user_generation_states[request_id]
        
        logger.error(f"生成过程发生错误: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# 添加定期清理函数
async def cleanup_files():
    """定期清理HTML文件"""
    while True:
        try:
            # 清理HTML目录中的所有html文件
            for html_file in HTML_DIR.glob("*.html"):
                try:
                    html_file.unlink()
                    logger.info(f"清理过期HTML文件: {html_file}")
                except Exception as e:
                    logger.warning(f"清理文件失败: {str(e)}")
            
            await asyncio.sleep(3600)  # 每小时检查一次
            
        except Exception as e:
            logger.error(f"清理过程发生错误: {str(e)}")
            await asyncio.sleep(3600)  # 发生错误时等待一小时后重试

# 修改启动事件
@app.on_event("startup")
async def startup_event():
    if not await check_ollama_status():
        print("警告: Ollama服务未启动，请确保服务可用")
    
    # 启动定期清理任务
    asyncio.create_task(cleanup_files())
    
    async def cleanup_states():
        while True:
            await asyncio.sleep(3600)  # 每小时清理一次
            user_generation_states.clear()
            logger.info("已清理用户生成状态")
    
    asyncio.create_task(cleanup_states())

# 添加clean_content函数定义
def clean_content(text: str) -> str:
    """清理生成的内容
    - 移除<think>标签及其内容
    - 移除其他思考标记
    - 清理多余的空行
    """
    # 移除<think>标签及其内容
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    
    # 移除其他可能的思考标记
    text = re.sub(r'\[思考\].*?\[/思考\]', '', text, flags=re.DOTALL)
    text = re.sub(r'【思考】.*?【/思考】', '', text, flags=re.DOTALL)
    text = re.sub(r'（思考）.*?（/思考）', '', text, flags=re.DOTALL)
    
    # 移除markdown格式的注释
    text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
    
    # 清理多余的空行
    text = re.sub(r'\n\s*\n', '\n\n', text)
    
    # 清理行首行尾的空白字符
    text = '\n'.join(line.strip() for line in text.split('\n'))
    
    # 最后整体去除首尾空白
    return text.strip()

if __name__ == "__main__":
    import uvicorn
    logger.info(f"正在启动服务...")
    logger.info(f"使用模型: {MODEL_NAME}")
    logger.info(f"保存目录: {SAVE_DIR}")
    logger.info(f"图片目录: {IMAGE_DIR}")
    
    # 确保所有必要的目录存在
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    
    uvicorn.run(
        app, 
        host="localhost",
        port=8000,
        log_level="info"
    ) 