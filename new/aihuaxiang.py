import pandas as pd
import json
import time
import os
import re
from dotenv import load_dotenv
import dashscope
from dashscope import Generation
import sys

# ---------------------- 1. 配置项 ----------------------
INPUT_FILE = r"E:\pycharm\PythonProject1\new\岗位分级结果_加权评分制_最终版.xlsx"
OUTPUT_PORTFOLIO = r"E:\pycharm\PythonProject1\new\岗位画像单独文件（新）.xlsx"
OUTPUT_MERGED = r"E:\pycharm\PythonProject1\new\原数据+画像整合文件（新）.xlsx"

JOB_NAME_COL = "岗位名称"
JOB_DETAIL_COL = "岗位详情"
SALARY_COL = "最终薪资"
JOB_LEVEL_COL = "岗位级别"

# 调试开关：True=模拟数据，False=真实调用
DEBUG_MODE = False

# Qwen3.5Plus Token配置（核心优化：最大化利用Token）
# qwen3.5plus 单轮最大Token≈8192（上下文），预留200Token给指令，实际可用≈7992
MAX_TOKEN = 7992  # 模型单轮最大可用Token
TOKEN_PER_CHINESE = 1.3  # 1个中文字≈1.3 Token（经验值，qwen的中文Token换算）
TOKEN_PER_ENGLISH = 1  # 1个英文字符≈1 Token
RESERVE_TOKEN = 200  # 预留Token（指令部分占用）

# 动态计算最大中文字符数（最大化利用Token，减少空余）
MAX_PROMPT_CHARS = int((MAX_TOKEN - RESERVE_TOKEN) / TOKEN_PER_CHINESE)  # ≈6000字
MAX_DETAIL_CHARS = int(MAX_PROMPT_CHARS * 0.8)  # 详情占80%，指令占20% ≈4800字

# 加载环境变量（官方方式）
load_dotenv("mima.env")
API_KEY = os.getenv("DASHSCOPE_API_KEY")
if not API_KEY and not DEBUG_MODE:
    raise ValueError("❌ 未获取到DASHSCOPE_API_KEY，请检查mima.env文件")


# ---------------------- 2. 核心工具函数 ----------------------
def calculate_token(text):
    """
    计算文本的Token数（适配Qwen3.5Plus的Token换算规则）
    :param text: 输入文本
    :return: 估算的Token数
    """
    if not isinstance(text, str):
        return 0

    # 分离中文和英文/数字
    chinese_chars = re.findall(r'[\u4e00-\u9fa5]', text)
    english_chars = re.findall(r'[a-zA-Z0-9\s]', text)
    other_chars = len(text) - len(chinese_chars) - len(english_chars)

    # 计算总Token
    token_count = (len(chinese_chars) * TOKEN_PER_CHINESE) + len(english_chars) + other_chars
    return int(token_count)


def clean_and_deduplicate_detail(text):
    """
    清洗岗位详情：去重、保留核心技能关键词、控制长度
    """
    if not isinstance(text, str) or text.strip() == "":
        return "无岗位详情"

    # 1. 基础清洗：去空格、换行、特殊符号
    text = re.sub(r"\s+", " ", text)  # 多个空格/换行替换为单个空格
    text = re.sub(r"[^\u4e00-\u9fa5a-zA-Z0-9,，.。；;：:（）()、/]", "", text)
    separators = r"[。；;，,]"
    sentences = re.split(separators, text)
    seen_sentences = set()
    unique_sentences = []

    # 优先保留的核心关键词（可根据你的岗位类型扩展）
    # 优先保留的核心关键词（整合所有岗位技能+证书，分类清晰）
    core_keywords = [
        # -------------------------- 编程语言 & 基础编程 --------------------------
        "C", "C++", "C/C++", "C++11", "STL", "多线程编程", "数据结构与算法",
        "Java", "Python", "JavaScript", "TypeScript", "HTML", "HTML5", "CSS", "CSS3", "ES6",
        "SQL", "Qt框架", "Windows编程", "ARM R52+", "RH850", "单片机", "Arduino",

        # -------------------------- 框架 & 中间件 --------------------------
        "Spring", "Spring MVC", "MyBatis", "SpringBoot", "Vue", "Vue2", "Vue3",
        "React", "Redis", "MQ", "Dubbo", "Spring Cloud", "jQuery", "ElementUI", "AntDesignUI",
        "Vue Router", "Vuex", "Webpack", "Ajax", "DOM",

        # -------------------------- 数据库 --------------------------
        "MySQL", "Oracle", "SQLServer", "DB2", "数据库优化",

        # -------------------------- 嵌入式 & 汽车电子 --------------------------
        "AUTOSAR规范", "嵌入式调试工具", "PLS UDE", "Lauterbach", "iSystem",
        "CAN总线工具", "CANOE", "BusMaster", "CAN", "TCP/IP协议", "RS232", "RS422",
        "LVDS", "PCI", "PCIE", "FPGA MGT", "FPGA", "CPLD", "AD", "DA", "FLASH",

        # -------------------------- 前端开发 --------------------------
        "CesiumJS", "Mapbox", "OpenLayers", "小程序开发", "跨浏览器兼容",
        "前端性能优化", "模块化开发", "响应式设计",

        # -------------------------- 大数据 & AI & 机器学习 --------------------------
        "机器学习基础", "深度学习模型", "DNN", "CNN", "RNN", "LSTM", "GAN",
        "强化学习", "人工智能芯片设计", "AI算法研发", "大数据处理与分析",
        "微波成像系统设计", "AI驱动的成像算法",

        # -------------------------- 测试相关 --------------------------
        # 测试类型
        "硬件测试", "功能测试", "性能测试", "兼容性测试", "集成测试", "系统测试",
        "可靠性测试", "环境测试", "安全测试", "单元测试", "确认测试", "接口测试",
        "数据测试", "APP测试", "自动化测试",
        # 测试工具/方法
        "DOE试验设计", "测试用例设计", "测试计划编制", "测试报告编写", "缺陷跟踪与管理",
        "LabVIEW", "数据采集", "仪器控制", "Selenium", "Robot Framework",
        # 测试仪器
        "万用表", "示波器", "频谱仪", "信号源", "信号发生器", "电子负载",

        # -------------------------- 行业软件 & 系统 --------------------------
        "PLM系统实施", "MES系统实施", "CAD软件", "CAXA", "SOLIDWORKS", "UG",
        "云平台软件部署", "系统调试", "ArcGIS", "CASS", "FineReport", "FineBI",
        "Visual Studio", "OpenCV", "图像处理",

        # -------------------------- 工控 & 物联网 & 弱电 --------------------------
        "Modbus", "OPC UA", "IEC 104", "DL/T 645", "弱电技术", "自动化系统集成",
        "安防系统部署", "工业互联网", "危化安全生产", "物联网硬件集成", "机器视觉系统调试",

        # -------------------------- 操作系统 & 网络 --------------------------
        "Linux", "CentOS", "麒麟信安操作系统", "网络配置", "VLAN", "静态路由", "防火墙",

        # -------------------------- 项目管理 & 流程 --------------------------
        "项目管理全流程管控", "APQP流程", "工程施工管理", "客户沟通", "需求管理",
        "跨部门资源协调",

        # -------------------------- 证书 & 资质 --------------------------
        "注册电气工程师（供配电）", "安防工程企业技术人员证书", "PMP项目管理专业人士认证",
        "信息系统项目管理师（中级）", "驾驶证", "医疗器械相关从业资格证",
        "英语六级", "CET-4", "ISO/IEC 17025", "电子工程师资格证", "ISO/IEC 17025内审员证书",
        "ISTQB基础级认证", "软件测试工程师（中级）", "一级建造师", "二级建造师",
        "日本语能力测试N2",

        # -------------------------- 通用技能 --------------------------
        "系统设计", "技术攻关", "代码编写与测试", "软件配置与故障排除", "系统集成支持",
        "产品技术培训", "医疗影像识图", "OCT", "IVUS", "超声", "手术跟台支持",
        "售前售后技术支持", "项目运维与实施", "设备安装与调试", "售后故障诊断与维修",
        "技术方案编写", "产品演示与培训", "电子元器件替代验证", "电源/电路测试与分析",
        "焊接技能", "硬件可靠性测试", "BOM变更流程支持", "芯片基础软件开发",
        "Python自动化测试", "天线设计与阵列优化", "测试环境搭建", "板卡测试",
        "环境试验", "振动", "高低温", "热真空", "电路板设计基础", "Office办公软件",
        "缺陷跟踪与分析"
    ]

    for sent in sentences:
        sent_trim = sent.strip()
        # 过滤空短句 + 去重（忽略大小写）
        if sent_trim and sent_trim.lower() not in seen_sentences:
            # 优先保留包含核心关键词的短句
            if any(key in sent_trim for key in core_keywords) or len(unique_sentences) < 20:
                seen_sentences.add(sent_trim.lower())
                unique_sentences.append(sent_trim)

    # 3. 合并并控制长度（适配Token最大化利用）
    cleaned_text = "。".join(unique_sentences)
    if len(cleaned_text) > MAX_DETAIL_CHARS:
        # 截取到最大长度，最大化利用Token
        cleaned_text = cleaned_text[:MAX_DETAIL_CHARS]

    return cleaned_text


# ---------------------- 3. 核心类实现 ----------------------
class JobProfileGenerator:
    """优化版：保留完整技能信息的岗位画像生成器（新增Token统计）"""

    def __init__(self):
        self.level_exp_mapping = {
            "初级": "1年以内相关工作经验",
            "中级": "1-3年相关工作经验",
            "高级": "3年以上相关工作经验",
        }
        # 新增：画像字段模板（对齐你提供的Java画像格式）
        self.profile_fields = [
            "专业技能", "证书要求", "创新能力", "学习能力",
            "抗压能力", "沟通能力", "实习能力", "经验要求"
        ]
        # 新增：统计数据存储
        self.statistics = []

    def load_and_clean_data(self):
        """加载并清洗数据（新增：岗位详情去重精简）"""
        try:
            df = pd.read_excel(INPUT_FILE)
            print(f"✅ 成功加载数据，共{len(df)}条记录")

            # 检查必要列
            required_cols = [JOB_NAME_COL, JOB_DETAIL_COL]
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                raise ValueError(f"❌ 数据缺少必要列：{', '.join(missing_cols)}")

            # 数据清洗
            fill_values = {
                JOB_NAME_COL: "未知岗位",
                JOB_DETAIL_COL: "无岗位详情",
                SALARY_COL: "0",
                JOB_LEVEL_COL: "未指定"
            }
            df = df.fillna(fill_values)

            # 去重：按岗位+级别+核心详情去重（更精准）
            df = df.drop_duplicates(subset=[JOB_NAME_COL, JOB_LEVEL_COL, JOB_DETAIL_COL], keep="first")

            # 清理空格并精简岗位详情（核心优化）
            for col in [JOB_NAME_COL, JOB_DETAIL_COL, JOB_LEVEL_COL]:
                df[col] = df[col].astype(str).str.strip()

            # 关键优化：对岗位详情进行去重+精简，保留核心技能
            df[JOB_DETAIL_COL] = df[JOB_DETAIL_COL].apply(clean_and_deduplicate_detail)

            # 过滤空详情
            df = df[df[JOB_DETAIL_COL] != "无岗位详情"]
            print(f"✅ 数据清洗完成，有效记录数：{len(df)}")

            return df

        except Exception as e:
            print(f"❌ 加载数据失败：{str(e)}")
            raise

    def group_job_details(self, df):
        """按岗位+级别分组（优化：合并详情时去重）"""
        df["分组键"] = df[JOB_NAME_COL] + "_" + df[JOB_LEVEL_COL]

        # 优化聚合逻辑：合并详情时再次去重，避免重复内容
        def merge_details(details):
            """合并多个详情，去重并保留核心"""
            all_details = "。".join(details.unique())
            return clean_and_deduplicate_detail(all_details)

        grouped = df.groupby("分组键").agg({
            JOB_NAME_COL: "first",
            JOB_LEVEL_COL: "first",
            JOB_DETAIL_COL: merge_details,  # 使用优化的合并函数
            SALARY_COL: "first"
        }).reset_index(drop=True)

        print(f"✅ 数据分组完成，共{len(grouped)}个岗位级别组合")
        return grouped

    def generate_prompt(self, job_name, job_level, merged_detail):
        """优化提示词：对齐Java画像示例，最大化利用Token"""
        exp_desc = self.level_exp_mapping.get(job_level, "无明确经验要求")

        # 优化提示词模板：精简指令部分，预留更多Token给详情
        prompt_content = f"""
你是专业的IT岗位画像生成专家，严格按要求输出JSON格式（无多余文字）：
1. 专业技能为数组格式，包含核心技术栈；
2. 能力字段为具体描述，非简单"无"；
3. 初级岗位实习能力体现应届生要求，中高级填"无"；
4. 证书要求明确列出，无则填"无"；
5. 经验要求：{exp_desc}。

生成{job_name}({job_level})岗位画像（基于以下详情）：
{merged_detail}

JSON模板：
{{
  "专业技能": ["核心技术1", "核心技术2"],
  "证书要求": "无"或"具体证书",
  "创新能力": "具体要求",
  "学习能力": "具体要求",
  "抗压能力": "具体要求",
  "沟通能力": "具体要求",
  "实习能力": "具体要求",
  "经验要求": "{exp_desc}"
}}
        """
        # 精简提示词格式（去多余换行/空格），减少Token占用
        prompt_content = re.sub(r"\n+", "\n", prompt_content).strip()

        # 最终控制提示词总长度（最大化利用Token，仅留少量冗余）
        prompt_token = calculate_token(prompt_content)
        if prompt_token > MAX_TOKEN:
            # 计算需要截取的详情长度
            excess_token = prompt_token - MAX_TOKEN
            excess_chars = int(excess_token / TOKEN_PER_CHINESE) + 1
            merged_detail_trimmed = merged_detail[:len(merged_detail) - excess_chars]
            # 替换详情并重新生成提示词
            prompt_content = prompt_content.replace(merged_detail, merged_detail_trimmed)

        return prompt_content

    def call_dashscope_model(self, prompt):
        """保持原调用逻辑，增加异常重试"""
        # 调试模式返回模拟数据（参考你提供的Java画像）
        if DEBUG_MODE:
            if "Java" in prompt and "初级" in prompt:
                return '''{
                  "专业技能": ["Java", "SQL", "SpringBoot", "MyBatis", "Oracle/SQLServer/DB2", "Linux基础命令"],
                  "证书要求": "无",
                  "创新能力": "能主动研究新技术，提升开发效率和程序性能",
                  "学习能力": "有较强的源码阅读、研究和理解能力；能快速掌握新框架与技术",
                  "抗压能力": "能适应加班、出差，具备较强抗压能力，心态积极，能主动融入团队",
                  "沟通能力": "思路清晰，善于思考，能独立分析和解决问题；擅长沟通交流，主动沟通、有担当",
                  "实习能力": "能辅助进行文档资料整理、收集资料，具备良好的文档编制习惯",
                  "经验要求": "1年以内相关工作经验"
                }'''
            elif "Java" in prompt and "中级" in prompt:
                return '''{
                  "专业技能": ["Java", "Spring", "Spring MVC", "MyBatis", "SpringBoot", "Vue", "Redis", "MQ", "MySQL", "Dubbo", "Spring Cloud", "HTML/CSS/JavaScript", "jQuery", "Linux", "Tomcat"],
                  "证书要求": "无",
                  "创新能力": "具备AI工具辅助开发意识，能结合AI技术提升代码质量与开发效率，参与智能代码审查等AI赋能项目",
                  "学习能力": "具备快速学习AI编程工具（如GitHub Copilot、CodeWhisperer等）及新技术栈的能力，适应AI+Java融合开发范式",
                  "抗压能力": "能适应项目出差及多任务并行开发节奏，具备在时限压力下高质量交付模块的能力",
                  "沟通能力": "具备良好的跨团队协作与表达能力，能清晰阐述技术方案并与前后端、测试、AI工程团队高效协同",
                  "实习能力": "面向2026届应届生，需具备扎实的Java基础和工程实践潜力，能通过2个月暑期实习完成结项答辩并展现AI+开发融合潜力",
                  "经验要求": "1-3年相关工作经验"
                }'''
            elif "Java" in prompt and "高级" in prompt:
                return '''{
                  "专业技能": ["Java", "MySQL", "数据库优化", "系统设计", "技术攻关", "代码编写与测试"],
                  "证书要求": "无",
                  "创新能力": "具备技术方案设计能力，能解决疑难问题并进行技术攻关",
                  "学习能力": "热爱编程，基础扎实，乐衷新技术，善于总结分享，喜欢动手实践",
                  "抗压能力": "能够承受一定工作压力，具备良好的心理素质",
                  "沟通能力": "具有良好的沟通和协调能力，能与客户保持紧密沟通并理解需求，日语N2或以上、口语流利",
                  "实习能力": "无",
                  "经验要求": "3年以上相关工作经验"
                }'''
            else:
                return '''{
                  "专业技能": ["Python", "SQL", "数据分析"],
                  "证书要求": "无",
                  "创新能力": "具备数据分析场景下的创新思维，能提出数据驱动的优化方案",
                  "学习能力": "能快速掌握新的数据分析工具和算法模型",
                  "抗压能力": "能承受多项目并行和紧急分析需求的压力",
                  "沟通能力": "能清晰向业务方解读分析结果，具备良好的跨部门沟通能力",
                  "实习能力": "无",
                  "经验要求": "无明确经验要求"
                }'''

        # 官方标准调用方式（增加重试机制）
        max_retries = 3
        retry_count = 0
        while retry_count < max_retries:
            try:
                messages = [
                    {'role': 'system',
                     'content': '你是一个专业的IT岗位画像生成助手，仅输出JSON格式内容，无多余文字，严格按照用户要求的字段和格式生成。'},
                    {'role': 'user', 'content': prompt}
                ]

                response = Generation.call(
                    api_key=API_KEY,
                    model="qwen-plus",
                    messages=messages,
                    result_format='message',
                    temperature=0.1,  # 降低随机性，保证输出稳定
                    max_tokens=1000,
                    timeout=60
                )

                if response.status_code == 200:
                    return response.output.choices[0].message.content.strip()
                else:
                    print(f"❌ 模型调用失败，状态码：{response.status_code}，信息：{response.message}")
                    retry_count += 1
                    time.sleep(2)  # 重试前等待
            except Exception as e:
                print(f"❌ 模型调用异常（第{retry_count + 1}次）：{str(e)}")
                retry_count += 1
                time.sleep(2)

        print("❌ 多次调用失败，返回默认画像")
        return ""

    def parse_profile_json(self, json_str):
        """优化JSON解析：兼容更多格式，保证字段完整"""
        if not json_str:
            return self.get_default_profile()

        try:
            # 更强的清理逻辑：移除JSON外的所有字符
            json_str = re.sub(r'^[\s\S]*?\{', '{', json_str)
            json_str = re.sub(r'\}[\s\S]*$', '}', json_str)
            # 处理单引号转双引号
            json_str = json_str.replace("'", "\"")
            profile = json.loads(json_str)

            # 补全缺失字段并格式化
            default = self.get_default_profile()
            for key in default:
                profile.setdefault(key, default[key])

            # 确保专业技能是列表格式
            if isinstance(profile["专业技能"], str):
                if profile["专业技能"] == "无":
                    profile["专业技能"] = []
                else:
                    # 分割字符串为列表（处理逗号分隔的技能）
                    profile["专业技能"] = [s.strip() for s in profile["专业技能"].split(",") if s.strip()]

            # 确保证书要求是字符串
            if isinstance(profile["证书要求"], list):
                profile["证书要求"] = ", ".join(profile["证书要求"]) if profile["证书要求"] else "无"

            return profile
        except Exception as e:
            print(f"⚠️ JSON解析失败：{str(e)}，使用默认画像")
            return self.get_default_profile()

    def get_default_profile(self):
        """默认画像模板（更贴合IT岗位）"""
        return {
            "专业技能": [],
            "证书要求": "无",
            "创新能力": "具备基础的技术创新意识，能在工作中尝试新方法",
            "学习能力": "具备良好的自主学习能力，能快速掌握岗位所需技术",
            "抗压能力": "能适应常规工作压力，具备良好的工作心态",
            "沟通能力": "具备基础的团队沟通能力，能清晰表达工作想法",
            "实习能力": "无",
            "经验要求": "无"
        }

    def generate_all_profiles(self):
        """主流程（新增Token/字数统计）"""
        # 1. 加载数据
        raw_df = self.load_and_clean_data()
        grouped_df = self.group_job_details(raw_df)

        # 2. 生成画像
        profiles = []
        for idx, row in grouped_df.iterrows():
            job_name = row[JOB_NAME_COL]
            job_level = row[JOB_LEVEL_COL]
            merged_detail = row[JOB_DETAIL_COL]

            print(f"\n📌 正在处理：{job_name} - {job_level}（{idx + 1}/{len(grouped_df)}）")

            # 新增：统计去重后详情的字数和Token
            detail_char_count = len(merged_detail)
            detail_token_count = calculate_token(merged_detail)

            # 生成提示词
            prompt = self.generate_prompt(job_name, job_level, merged_detail)

            # 新增：统计实际传入模型的字数和Token
            prompt_char_count = len(prompt)
            prompt_token_count = calculate_token(prompt)
            token_utilization = (prompt_token_count / MAX_TOKEN) * 100  # Token利用率

            print(f"📝 去重后详情字数：{detail_char_count} | Token数：{detail_token_count}")
            print(
                f"📤 传入模型总字数：{prompt_char_count} | Token数：{prompt_token_count}（利用率：{token_utilization:.1f}%）")

            # 调用模型
            llm_resp = self.call_dashscope_model(prompt)
            if llm_resp:
                print(f"✅ 模型返回结果：{llm_resp[:100]}...")

            # 解析结果
            profile = self.parse_profile_json(llm_resp)

            # 构建结果行（优化格式：技能列表转字符串）
            result_row = {
                "岗位名称": job_name,
                "岗位级别": job_level,
                "专业技能": ", ".join(profile["专业技能"]) if isinstance(profile["专业技能"], list) else str(
                    profile["专业技能"]),
                "证书要求": profile["证书要求"],
                "创新能力": profile["创新能力"],
                "学习能力": profile["学习能力"],
                "抗压能力": profile["抗压能力"],
                "沟通能力": profile["沟通能力"],
                "实习能力": profile["实习能力"],
                "经验要求": profile["经验要求"],
                # 新增：统计字段写入结果
                "去重后详情字数": detail_char_count,
                "传入模型总字数": prompt_char_count,
                "传入模型Token数": prompt_token_count,
                "Token利用率(%)": round(token_utilization, 1)
            }
            profiles.append(result_row)

            # 新增：保存统计数据
            self.statistics.append({
                "岗位名称": job_name,
                "岗位级别": job_level,
                "去重后详情字数": detail_char_count,
                "去重后详情Token数": detail_token_count,
                "传入模型总字数": prompt_char_count,
                "传入模型Token数": prompt_token_count,
                "Token利用率(%)": round(token_utilization, 1),
                "最大可用Token数": MAX_TOKEN
            })

            # 控制请求频率（避免触发限流）
            time.sleep(1.5)

        # 3. 保存单独的画像文件（包含统计字段）
        profile_df = pd.DataFrame(profiles)
        profile_df.to_excel(OUTPUT_PORTFOLIO, index=False, engine="openpyxl")
        print(f"\n✅ 岗位画像单独文件已保存：{OUTPUT_PORTFOLIO}")

        # 4. 整合原数据和画像
        profile_map = {}
        for _, row in profile_df.iterrows():
            profile_map[f"{row['岗位名称']}_{row['岗位级别']}"] = row

        merged_data = raw_df.copy()
        # 初始化画像列 + 统计列
        for col in self.profile_fields + ["去重后详情字数", "传入模型总字数", "传入模型Token数", "Token利用率(%)"]:
            merged_data[col] = ""

        # 填充画像数据
        for idx, row in merged_data.iterrows():
            key = f"{row[JOB_NAME_COL]}_{row[JOB_LEVEL_COL]}"
            if key in profile_map:
                profile = profile_map[key]
                for col in self.profile_fields + ["去重后详情字数", "传入模型总字数", "传入模型Token数",
                                                  "Token利用率(%)"]:
                    merged_data.loc[idx, col] = profile[col]

        # 保存整合文件
        merged_data.to_excel(OUTPUT_MERGED, index=False, engine="openpyxl")
        print(f"✅ 原数据+画像整合文件已保存：{OUTPUT_MERGED}")

        # 5. 输出统计汇总
        self.print_statistics_summary()

        return profile_df, merged_data

    def print_statistics_summary(self):
        """打印Token/字数统计汇总"""
        if not self.statistics:
            print("\n⚠️ 无统计数据")
            return

        stat_df = pd.DataFrame(self.statistics)
        print("\n" + "=" * 80)
        print("📊 岗位画像Token/字数统计汇总")
        print("=" * 80)
        print(f"总处理岗位数：{len(stat_df)}")
        print(f"平均去重后详情字数：{stat_df['去重后详情字数'].mean():.0f}")
        print(f"平均传入模型Token数：{stat_df['传入模型Token数'].mean():.0f}")
        print(f"平均Token利用率：{stat_df['Token利用率(%)'].mean():.1f}%")
        print(
            f"最高Token利用率：{stat_df['Token利用率(%)'].max():.1f}%（{stat_df.loc[stat_df['Token利用率(%)'].idxmax(), '岗位名称']}-{stat_df.loc[stat_df['Token利用率(%)'].idxmax(), '岗位级别']}）")
        print(
            f"最低Token利用率：{stat_df['Token利用率(%)'].min():.1f}%（{stat_df.loc[stat_df['Token利用率(%)'].idxmin(), '岗位名称']}-{stat_df.loc[stat_df['Token利用率(%)'].idxmin(), '岗位级别']}）")
        print("=" * 80)


# ---------------------- 4. 测试官方调用（单独验证） ----------------------
def test_official_call():
    """单独测试官方API调用是否正常"""
    print("🔍 开始测试官方API调用...")
    try:
        messages = [
            {'role': 'system', 'content': 'You are a helpful assistant.'},
            {'role': 'user', 'content': '你是谁？'}
        ]
        response = dashscope.Generation.call(
            api_key=API_KEY,
            model="qwen-plus",
            messages=messages,
            result_format='message'
        )
        print(f"✅ 测试调用成功，响应状态码：{response.status_code}")
        print(f"✅ 模型返回：{response.output.choices[0].message.content}")
        return True
    except Exception as e:
        print(f"❌ 测试调用失败：{str(e)}")
        return False


# ---------------------- 5. 执行入口 ----------------------
if __name__ == "__main__":
    # 打印Token配置信息
    print(f"📌 Qwen3.5Plus配置：")
    print(f"   最大可用Token：{MAX_TOKEN}")
    print(f"   最大详情字符数：{MAX_DETAIL_CHARS}")
    print(f"   中文字符/Token：{TOKEN_PER_CHINESE}")
    print("-" * 50)

    # 先测试官方调用是否正常
    if not DEBUG_MODE:
        if not test_official_call():
            print("\n⚠️ API调用测试失败，请先解决密钥/网络问题！")
            sys.exit(1)
        print("✅ API调用测试通过，开始生成岗位画像...\n")

    try:
        generator = JobProfileGenerator()
        profile_df, merged_df = generator.generate_all_profiles()
        # 输出生成结果统计
        print(f"\n🎉 所有任务执行完成！")
        print(f"📊 生成画像数量：{len(profile_df)}")
        # 打印前3条生成结果示例
        print("\n📋 生成结果示例：")
        for idx, row in profile_df.head(3).iterrows():
            print(f"\n{row['岗位名称']}（{row['岗位级别']}）：")
            print(f"专业技能：{row['专业技能']}")
            print(f"Token利用率：{row['Token利用率(%)']}%")
            print(f"经验要求：{row['经验要求']}")
    except Exception as e:
        print(f"\n❌ 执行失败：{str(e)}")
        import traceback

        traceback.print_exc()
    finally:
        # 兼容Windows编码的退出逻辑
        try:
            if sys.platform == "win32":
                import msvcrt

                print("\n按任意键退出...")
                msvcrt.getch()
            else:
                input("按Enter键退出...")
        except:
            pass