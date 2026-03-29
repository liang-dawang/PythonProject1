import os
# 禁用 OneDNN 加速，解决 Windows 兼容性问题
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["PADDLE_DISABLE_ONEDNN"] = "1"
import json
import psycopg2
import re
import logging
from typing import Dict, Any
from http import HTTPStatus

import requests
import base64
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor
from dashscope import Generation
# 新增：导入Celery配置
from .tool.celery_config import app
from paddleocr import PaddleOCR

# -------------------------- 配置与初始化 --------------------------
# 加载环境变量
load_dotenv(r"E:\pycharm\PythonProject1\new\mima.env")
SOFT_SKILL_STANDARDS_DIR = r"E:\pycharm\PythonProject1\app\resume\soft_skill_standards"

# PostgreSQL 配置
PG_CONFIG = {
    "host": os.getenv("PG_HOST", "localhost"),
    "port": os.getenv("PG_PORT", "5432"),
    "user": os.getenv("PG_USER", "postgres"),
    "password": os.getenv("PG_PASSWORD", "postgres123"),
    "database": os.getenv("PG_DB", "career_platform")
}

# 通义千问配置
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")

# 配置校验
if not DASHSCOPE_API_KEY:
    raise ValueError("❌ 未获取到 DASHSCOPE_API_KEY，请检查 mima.env 文件")

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("resume_parser.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 初始化本地 PaddleOCR
ocr = PaddleOCR(
    use_angle_cls=True,
    lang='ch',
    use_gpu=False,
    show_log=False,
    use_space_char=True,
    det_db_unclip_ratio=1.5
)

# -------------------------- 核心工具函数（保留原有逻辑） --------------------------
def extract_text_from_image_paddle_local(image_path: str) -> str:
    """本地调用 PaddleOCR"""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"图片文件不存在: {image_path}")

    valid_ext = ['.jpg', '.jpeg', '.png', '.bmp', '.pdf']
    file_ext = os.path.splitext(image_path)[-1].lower()
    if file_ext not in valid_ext:
        raise ValueError(f"不支持的文件类型: {file_ext}，仅支持 {valid_ext}")

    try:
        logger.info(f"本地 PaddleOCR 识别图片: {image_path}")
        result = ocr.ocr(image_path, cls=True)

        text_lines = []
        for page in result:
            if page is not None:
                for line in page:
                    text = line[1][0].strip()
                    if text:
                        text_lines.append(text)

        resume_text = "\n".join(text_lines)
        resume_text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9，。：；！？（）【】《》、·\s]', '', resume_text)

        if not resume_text:
            raise ValueError("本地 OCR 未识别到任何文本（图片可能模糊/无有效文字）")

        logger.info(f"✅ OCR识别成功，提取文本行数: {len(text_lines)}，结果预览: {resume_text[:50]}...")
        return resume_text

    except Exception as e:
        raise Exception(f"❌ 图片识别失败: {str(e)}")


def build_soft_skill_prompt_section(skill_name: str, standard_file: str) -> str:
    """根据标准文件生成单个软技能的 Prompt 片段"""
    try:
        with open(standard_file, 'r', encoding='utf-8') as f:
            standard = json.load(f)
    except Exception as e:
        logger.warning(f"加载标准文件失败 {standard_file}: {e}")
        return f"{skill_name}：未提供标准定义"

    keywords = []
    examples = []
    for anchor in standard.get("behavioral_anchors", []):
        keywords.extend(anchor.get("evidence_keywords", []))
        if "example_resume_snippet" in anchor:
            examples.append(anchor["example_resume_snippet"])

    prompt = f"{skill_name}：\n"
    prompt += "- 关键行为线索（满足任一即视为体现该能力）：\n"
    for kw in keywords[:10]:
        prompt += f"  • {kw}\n"
    if examples:
        prompt += "- 典型简历语句示例：\n"
        for ex in examples[:3]:
            prompt += f"  • {ex}\n"
    return prompt.strip()


def call_qwen35(resume_text: str) -> Dict[str, Any]:
    """调用通义千问，基于软技能标准文件提取证据"""
    skill_mapping = {
        "创新能力": "innovation_ability.json",
        "学习能力": "learning_ability.json",
        "抗压能力": "resilience_ability.json",
        "沟通能力": "communication_ability.json",
        "实习能力": "execution_ability.json"
    }

    skill_definitions = "### 软技能定义与提取标准（必须严格遵循）\n"
    for field_name, filename in skill_mapping.items():
        file_path = os.path.join(SOFT_SKILL_STANDARDS_DIR, filename)
        if os.path.exists(file_path):
            skill_definitions += build_soft_skill_prompt_section(field_name, file_path) + "\n\n"
        else:
            skill_definitions += f"{field_name}：请根据常识判断，若简历中体现相关行为则提取原句。\n\n"

    prompt = f"""
你是一个专业的简历解析引擎，请严格按照以下规则处理：

{skill_definitions}

### 提取规则
1. 对每个软技能，从简历原文中**逐字提取所有匹配的完整句子**；
2. 必须是简历中的原话，不可改写、总结、编造；
3. 若找到多条，用中文分号“；”连接；
4. 若完全未体现，返回“无”；
5. **特别注意**：即使未出现关键词，只要语义匹配（如“协调多方”≈“跨团队对齐”），也应提取。

### 输出格式（仅返回JSON，无其他内容）
{{
  "专业技能": ["Java", "Redis"],
  "证书": ["英语六级"],
  "创新能力": "采用逻辑过期方案解决缓存击穿",
  "学习能力": "无",
  "抗压能力": "无",
  "沟通能力": "主导订单系统与风控团队对接，协调5方达成技术方案；撰写微服务接口文档，供前端团队使用",
  "实习能力": "6个月Java开发实习生，独立完成接口开发"
}}

### 简历文本
{resume_text}
"""

    try:
        response = Generation.call(
            model='qwen-plus',
            api_key=DASHSCOPE_API_KEY,
            messages=[{"role": "user", "content": prompt}],
            result_format='json',
            temperature=0.1,
            max_tokens=1536,
            top_p=0.9
        )

        if response.status_code != HTTPStatus.OK:
            raise Exception(f"通义千问调用失败: {response.code} - {response.message}")

        content = response.output.choices[0].message.content
        if not content:
            raise ValueError("通义千问返回空内容")

        if isinstance(content, list):
            content = "".join(str(item) for item in content)
        content = content.strip()

        json_match = re.search(r'\{[\s\S]*\}', content)
        if not json_match:
            raise ValueError(f"非标准JSON: {content[:200]}...")

        profile_data = json.loads(json_match.group())

        default_fields = {
            "专业技能": [], "证书": [],
            "创新能力": "无", "学习能力": "无", "抗压能力": "无",
            "沟通能力": "无", "实习能力": "无"
        }
        for field, default_val in default_fields.items():
            profile_data.setdefault(field, default_val)
            if field in ["专业技能", "证书"] and not isinstance(profile_data[field], list):
                profile_data[field] = []

        logger.info("✅ 通义千问结构化解析成功")
        return profile_data

    except Exception as e:
        logger.error(f"❌ 通义千问处理失败: {e}")
        raise


def calculate_completeness_score(ocr_text: str) -> float:
    """
    计算简历完整度评分（0~100），适用于嵌入式/工业/前端/后端/测试等技术岗。
    特点：
      - 不依赖联系方式
      - 姓名仅占 5 分（因识别率低）
      - 强化专业技能（35分）和项目经历（30分）
    """
    text = ocr_text.strip()
    if not text:
        return 0.0

    score = 0.0
    text_lower = text.lower()

    # ==================== 1. 姓名（5%）====================
    # 弱化判断：只要开头是中文名 或 含“姓名”字段即给分
    if re.search(r'姓名[:：]?[\u4e00-\u9fa5]{2,4}', text) or (
        len(text.split()) > 0 and re.match(r'^[\u4e00-\u9fa5]{2,4}$', text.split()[0])
    ):
        score += 5

    # ==================== 2. 学历（15%）====================
    degree_patterns = [r'本科', r'硕士', r'博士', r'大专', r'bachelor', r'master', r'phd']
    if any(re.search(pattern, text_lower) for pattern in degree_patterns):
        score += 15

    # ==================== 3. 专业（10%）====================
    comp_majors = [
        r'计算机', r'软件工程', r'信息工程', r'人工智能', r'大数据', r'物联网', r'网络工程',
        r'信息安全', r'数据科学', r'智能科学', r'自动化', r'电子信息', r'通信工程', r'嵌入式',
        r'测控', r'机械电子', r'车辆工程', r'工业工程', r'前端', r'testing', r'quality assurance'
    ]
    if any(re.search(major, text, re.IGNORECASE) for major in comp_majors):
        score += 10
    elif re.search(r'(专业[:：]|主修[:：]|Major[:：])', text):
        score += 3  # 有字段但未填具体专业

    # ==================== 4. 专业技能（35%）====================
    # 按领域组织关键词，覆盖你提供的所有技术栈
    tech_domains = {
        "嵌入式/汽车电子": [
            "C/C++", "AUTOSAR", "PLS UDE", "Lauterbach", "iSystem", "CAN", "LIN", "ETH", "TCP/IP",
            "RTOS", "ISO 26262", "功能安全", "RH850", "AURIX", "CPU虚拟化", "国产芯片", "OpenCV"
        ],
        "工业自动化/工控": [
            "Modbus", "OPC UA", "IEC104", "PLC", "HMI", "DCS", "组态", "CAD", "SolidWorks", "CAXA",
            "ArcGIS", "VLAN", "交换机", "路由器", "弱电", "安防", "工业互联网", "边缘计算"
        ],
        "后端开发（Java）": [
            "Java", "SpringBoot", "SpringCloud", "MyBatis", "Dubbo", "RocketMQ", "Kafka", "Redis",
            "MySQL", "Oracle", "Tomcat", "Maven", "Linux", "Docker", "Git"
        ],
        "前端开发": [
            "HTML5", "CSS3", "JavaScript", "TypeScript", "Vue", "React", "Webpack", "Vite", "Element Plus",
            "Ant Design", "ECharts", "Cesium", "Mapbox", "WebSocket", "MQTT", "性能优化", "跨浏览器"
        ],
        "测试/质量保障": [
            "Selenium", "Appium", "JMeter", "LoadRunner", "Pytest", "Postman", "JIRA", "禅道",
            "接口测试", "性能测试", "安全测试", "自动化测试", "CANoe", "示波器", "万用表", "EMC"
        ],
        "通用开发基础": [
            "Linux", "Windows", "Git", "Shell", "Python", "多线程", "多进程", "TCP/IP", "HTTP",
            "串口", "SPI", "I2C", "UART", "STL", "Qt", "GCC", "GDB", "Make", "单元测试"
        ]
    }

    # 扁平化所有关键词（转为小写）
    all_tech_keywords = set()
    for keywords in tech_domains.values():
        for kw in keywords:
            all_tech_keywords.add(kw.lower())

    # 判断是否包含技能描述 + 具体技术词
    has_skill_section = any(
        phrase in text for phrase in ["技能", "掌握", "熟悉", "精通", "技术栈", "开发工具", "编程语言"]
    )
    has_tech_word = any(
        re.search(rf'\b{re.escape(kw)}\b', text_lower) for kw in all_tech_keywords
    )

    if has_skill_section and has_tech_word:
        score += 35
    elif has_tech_word:
        score += 25  # 有技术词但无明确标题
    elif has_skill_section:
        score += 10  # 有“技能”但无具体内容

    # ==================== 5. 实习/项目经历（30%）====================
    # 高级复合判断：时间 + 组织/项目 + 动作
    time_match = bool(re.search(r'(20\d{2}[-–—\.年]\d{1,2}|至今|实习|项目|experience|internship)', text, re.IGNORECASE))
    org_match = bool(re.search(r'(公司|科技|有限|实验室|团队|project|项目)', text, re.IGNORECASE))
    action_match = bool(re.search(r'(负责|参与|开发|实现|设计|优化|完成|主导|协作|部署|测试|调试)', text, re.IGNORECASE))

    if time_match and org_match and action_match:
        score += 30
    elif (time_match and action_match) or (org_match and action_match):
        score += 20
    elif time_match or org_match or action_match:
        score += 10
    elif re.search(r'(实习|项目|经历|工作)', text, re.IGNORECASE):
        score += 5

    # ==================== 6. 软技能/证书（5%）【可选加分】====================
    soft_or_cert = any(
        re.search(pattern, text, re.IGNORECASE)
        for pattern in [r'创新能力', r'学习能力', r'沟通能力', r'抗压能力', r'英语六级', r'CET-6', r'软考', r'证书']
    )
    if soft_or_cert:
        score += 5

    # ==================== 最终处理 ====================
    final_score = round(min(score, 100.0), 1)
    logger.info(f"✅ 简历完整度评分（技术岗·无联系方式·姓名弱化）: {final_score}")
    return final_score


def init_postgresql() -> None:
    """初始化 PostgreSQL 数据表（首次运行调用）"""
    conn = None
    try:
        conn = psycopg2.connect(**PG_CONFIG)
        cur = conn.cursor()

        create_table_sql = """
        CREATE TABLE IF NOT EXISTS student_ability_profile (
            id SERIAL PRIMARY KEY,
            student_name VARCHAR(100) NOT NULL COMMENT '学生姓名',
            resume_text TEXT NOT NULL COMMENT '原始简历文本',
            professional_skills JSONB DEFAULT '[]'::JSONB COMMENT '专业技能',
            certificates JSONB DEFAULT '[]'::JSONB COMMENT '证书',
            innovation_ability TEXT DEFAULT '无' COMMENT '创新能力',
            learning_ability TEXT DEFAULT '无' COMMENT '学习能力',
            pressure_ability TEXT DEFAULT '无' COMMENT '抗压能力',
            communication_ability TEXT DEFAULT '无' COMMENT '沟通能力',
            internship_ability TEXT DEFAULT '无' COMMENT '实习能力',
            completeness_score FLOAT DEFAULT 0.0 COMMENT '简历完整度评分(0-100)',
            competitiveness_score FLOAT DEFAULT 0.0 COMMENT '竞争力评分(预留)',
            create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '更新时间'
        );

        CREATE INDEX IF NOT EXISTS idx_student_name ON student_ability_profile(student_name);
        CREATE INDEX IF NOT EXISTS idx_create_time ON student_ability_profile(create_time);
        """

        cur.execute(create_table_sql)
        conn.commit()
        cur.close()
        logger.info("✅ PostgreSQL 表初始化/检查成功")
    except Exception as e:
        logger.error(f"❌ 初始化数据库失败: {e}")
        raise
    finally:
        if conn:
            conn.close()


def save_to_postgresql(
        student_name: str,
        resume_text: str,
        profile_data: Dict[str, Any],
        completeness_score: float,
        retry_times: int = 3
) -> None:
    """保存结构化简历数据到 PostgreSQL（带重试）"""
    conn = None
    attempt = 0
    while attempt < retry_times:
        try:
            attempt += 1
            conn = psycopg2.connect(**PG_CONFIG)
            cur = conn.cursor()

            insert_sql = """
            INSERT INTO student_ability_profile (
                student_name, resume_text, professional_skills, certificates,
                innovation_ability, learning_ability, pressure_ability,
                communication_ability, internship_ability, completeness_score
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING;
            """

            params = (
                student_name,
                resume_text,
                json.dumps(profile_data.get("专业技能", [])),
                json.dumps(profile_data.get("证书", [])),
                profile_data.get("创新能力", "无"),
                profile_data.get("学习能力", "无"),
                profile_data.get("抗压能力", "无"),
                profile_data.get("沟通能力", "无"),
                profile_data.get("实习能力", "无"),
                completeness_score
            )

            cur.execute(insert_sql, params)
            conn.commit()
            cur.close()
            logger.info(f"✅ {student_name} 简历数据已保存，完整度评分: {completeness_score}")
            return
        except psycopg2.OperationalError as e:
            logger.warning(f"❌ 数据库连接失败（第{attempt}次）: {e}")
            if attempt >= retry_times:
                raise Exception(f"数据库连接失败（重试{retry_times}次）: {e}")
            import time
            time.sleep(1)
        except Exception as e:
            logger.error(f"❌ 保存数据失败: {e}")
            raise
        finally:
            if conn:
                conn.close()

# -------------------------- Celery异步任务 --------------------------
@app.task(bind=True, name="resume_parser_task")
def resume_parser_async(self, student_name: str, resume_input: str, input_type: str = "text") -> Dict[str, Any]:
    """
    Celery异步简历解析任务
    :param self: Celery任务上下文（用于重试）
    :param student_name: 学生姓名
    :param resume_input: 简历文本/图片路径
    :param input_type: 输入类型（text/image）
    :return: 解析结果字典
    """
    try:
        if input_type not in ["text", "image"]:
            raise ValueError("input_type 必须为 'text' 或 'image'")

        logger.info(f"[异步任务] 开始解析 {student_name} 的简历，输入类型: {input_type}")

        # 提取简历文本
        if input_type == "image":
            resume_text = extract_text_from_image_paddle_local(resume_input)
        else:
            resume_text = str(resume_input).strip()

        if not resume_text:
            raise ValueError("简历文本提取结果为空")

        # 结构化解析 + 评分 + 保存
        profile_data = call_qwen35(resume_text)
        completeness_score = calculate_completeness_score(resume_text)
        save_to_postgresql(student_name, resume_text, profile_data, completeness_score)

        return {
            "code": 200,
            "msg": "解析成功",
            "data": {
                "student_name": student_name,
                "resume_profile": profile_data,
                "completeness_score": completeness_score,
                "competitiveness_score": 0.0,
                "raw_text": resume_text[:500] + "..." if len(resume_text) > 500 else resume_text
            }
        }

    except Exception as e:
        logger.exception(f"[异步任务] ❌ {student_name} 简历解析异常")
        # 任务失败自动重试（最多3次）
        self.retry(exc=e, countdown=2 ** self.request.retries)
        return {
            "code": 500,
            "msg": f"处理失败: {str(e)}",
            "data": None
        }

# -------------------------- 前端调用接口示例（FastAPI） --------------------------
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI(title="简历解析异步接口")

# 初始化数据库（启动时执行一次）
@app.on_event("startup")
def startup_event():
    init_postgresql()

@app.post("/parse_resume")
async def parse_resume(student_name: str, resume_input: str, input_type: str = "text"):
    """
    前端调用的接口：提交简历解析请求，返回任务ID
    """
    try:
        # 提交异步任务
        task = resume_parser_async.delay(student_name, resume_input, input_type)
        return JSONResponse({
            "code": 200,
            "msg": "任务已提交",
            "data": {
                "task_id": task.id,
                "student_name": student_name
            }
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提交任务失败: {str(e)}")

@app.get("/get_task_result/{task_id}")
async def get_task_result(task_id: str):
    """
    查询异步任务结果
    """
    task = resume_parser_async.AsyncResult(task_id)
    if task.state == 'PENDING':
        return JSONResponse({
            "code": 202,
            "msg": "任务处理中",
            "data": {"task_id": task_id, "state": task.state}
        })
    elif task.state == 'SUCCESS':
        return JSONResponse({
            "code": 200,
            "msg": "任务完成",
            "data": task.result
        })
    else:
        return JSONResponse({
            "code": 500,
            "msg": "任务失败",
            "data": {"task_id": task_id, "state": task.state, "error": str(task.result)}
        })

# -------------------------- 测试入口 --------------------------
if __name__ == "__main__":
    # 启动FastAPI服务
    uvicorn.run(app, host="0.0.0.0", port=8000)