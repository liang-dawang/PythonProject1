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
OUTPUT_PORTFOLIO = r"E:\pycharm\PythonProject1\new\岗位画像单独文件.xlsx"
OUTPUT_MERGED = r"E:\pycharm\PythonProject1\new\原数据+画像整合文件.xlsx"

JOB_NAME_COL = "岗位名称"
JOB_DETAIL_COL = "岗位详情"
SALARY_COL = "最终薪资"
JOB_LEVEL_COL = "岗位级别"

# 调试开关：True=模拟数据，False=真实调用
DEBUG_MODE = False

# 加载环境变量（官方方式）
load_dotenv("mima.env")
API_KEY = os.getenv("DASHSCOPE_API_KEY")
if not API_KEY and not DEBUG_MODE:
    raise ValueError("❌ 未获取到DASHSCOPE_API_KEY，请检查mima.env文件")


# ---------------------- 2. 核心类实现 ----------------------
class JobProfileGenerator:
    """完全适配官方示例的岗位画像生成器"""

    def __init__(self):
        self.level_exp_mapping = {
            "初级": "1年以内相关工作经验",
            "中级": "1-3年相关工作经验",
            "高级": "3年以上相关工作经验",

        }

    def load_and_clean_data(self):
        """加载并清洗数据"""
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

            # 去重+清理空格
            df = df.drop_duplicates(subset=[JOB_NAME_COL, JOB_DETAIL_COL], keep="first")
            for col in [JOB_NAME_COL, JOB_DETAIL_COL, JOB_LEVEL_COL]:
                df[col] = df[col].astype(str).str.strip()

            # 过滤空详情
            df = df[df[JOB_DETAIL_COL] != "无岗位详情"]
            print(f"✅ 数据清洗完成，有效记录数：{len(df)}")

            return df

        except Exception as e:
            print(f"❌ 加载数据失败：{str(e)}")
            raise

    def group_job_details(self, df):
        """按岗位+级别分组"""
        df["分组键"] = df[JOB_NAME_COL] + "_" + df[JOB_LEVEL_COL]

        grouped = df.groupby("分组键").agg({
            JOB_NAME_COL: "first",
            JOB_LEVEL_COL: "first",
            JOB_DETAIL_COL: lambda x: "\n".join(x.unique()),
            SALARY_COL: "first"
        }).reset_index(drop=True)

        print(f"✅ 数据分组完成，共{len(grouped)}个岗位级别组合")
        return grouped

    def generate_prompt(self, job_name, job_level, merged_detail):
        """生成符合官方调用规范的提示词"""
        exp_desc = self.level_exp_mapping.get(job_level, "无明确经验要求")

        # 极简提示词，强制JSON输出（官方模型对简洁提示词响应更稳定）
        prompt_content = f"""
仅输出JSON格式，不要任何多余文字：
{{
  "专业技能": ["核心技术1", "核心技术2"],
  "证书要求": "无" 或 ["证书名称"],
  "创新能力": "具体要求" 或 "无",
  "学习能力": "具体要求" 或 "无",
  "抗压能力": "具体要求" 或 "无",
  "沟通能力": "具体要求" 或 "无",
  "实习能力": "具体要求" 或 "无",
  "经验要求": "{exp_desc}"
}}

基于以下信息生成{job_name}({job_level})的岗位画像：
{merged_detail[:1000]}
        """
        return prompt_content.strip()

    def call_dashscope_model(self, prompt):
        """完全按照官方示例调用模型"""
        # 调试模式返回模拟数据
        if DEBUG_MODE:
            return '''{
              "专业技能": ["C/C++", "Linux", "数据结构", "STL"],
              "证书要求": "无",
              "创新能力": "无",
              "学习能力": "具备快速学习新技术的能力",
              "抗压能力": "能承受项目进度压力",
              "沟通能力": "良好的团队沟通能力",
              "实习能力": "无",
              "经验要求": "1-3年相关工作经验"
            }'''

        # 官方标准调用方式
        try:
            messages = [
                {'role': 'system', 'content': '你是一个专业的IT岗位画像生成助手，仅输出JSON格式内容，无多余文字。'},
                {'role': 'user', 'content': prompt}
            ]

            # 完全复刻官方示例的参数
            response = Generation.call(
                api_key=API_KEY,  # 显式传入API Key（官方推荐）
                model="qwen-plus",  # 用官方示例的qwen-plus模型
                messages=messages,
                result_format='message',  # 官方必选参数
                temperature=0.0,  # 0值保证输出稳定
                max_tokens=1000,
                timeout=60
            )

            # 官方标准的响应解析
            if response.status_code == 200:
                return response.output.choices[0].message.content.strip()
            else:
                print(f"❌ 模型调用失败，状态码：{response.status_code}，信息：{response.message}")
                return ""

        except Exception as e:
            print(f"❌ 模型调用异常：{str(e)}")
            return ""

    def parse_profile_json(self, json_str):
        """安全解析JSON"""
        if not json_str:
            return self.get_default_profile()

        try:
            # 清理非JSON字符
            json_str = re.sub(r'^[^{]*', '', json_str)
            json_str = re.sub(r'[^}]*$', '', json_str)
            profile = json.loads(json_str)

            # 补全缺失字段
            default = self.get_default_profile()
            for key in default:
                profile.setdefault(key, default[key])

            return profile
        except:
            return self.get_default_profile()

    def get_default_profile(self):
        """默认画像模板"""
        return {
            "专业技能": [],
            "证书要求": "无",
            "创新能力": "无",
            "学习能力": "无",
            "抗压能力": "无",
            "沟通能力": "无",
            "实习能力": "无",
            "经验要求": "无"
        }

    def generate_all_profiles(self):
        """主流程"""
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

            # 生成提示词
            prompt = self.generate_prompt(job_name, job_level, merged_detail)

            # 调用模型（官方方式）
            llm_resp = self.call_dashscope_model(prompt)

            # 解析结果
            profile = self.parse_profile_json(llm_resp)

            # 构建结果行
            result_row = {
                "岗位名称": job_name,
                "岗位级别": job_level,
                "专业技能": ", ".join(profile["专业技能"]) if isinstance(profile["专业技能"], list) else profile[
                    "专业技能"],
                "证书要求": profile["证书要求"] if not isinstance(profile["证书要求"], list) else ", ".join(
                    profile["证书要求"]),
                "创新能力": profile["创新能力"],
                "学习能力": profile["学习能力"],
                "抗压能力": profile["抗压能力"],
                "沟通能力": profile["沟通能力"],
                "实习能力": profile["实习能力"],
                "经验要求": profile["经验要求"]
            }
            profiles.append(result_row)

            # 控制请求频率
            time.sleep(1)

        # 3. 保存单独的画像文件
        profile_df = pd.DataFrame(profiles)
        profile_df.to_excel(OUTPUT_PORTFOLIO, index=False)
        print(f"\n✅ 岗位画像单独文件已保存：{OUTPUT_PORTFOLIO}")

        # 4. 整合原数据和画像
        profile_map = {}
        for _, row in profile_df.iterrows():
            profile_map[f"{row['岗位名称']}_{row['岗位级别']}"] = row

        merged_data = raw_df.copy()
        # 初始化画像列
        for col in ["专业技能", "证书要求", "创新能力", "学习能力", "抗压能力", "沟通能力", "实习能力", "经验要求"]:
            merged_data[col] = ""

        # 填充画像数据
        for idx, row in merged_data.iterrows():
            key = f"{row[JOB_NAME_COL]}_{row[JOB_LEVEL_COL]}"
            if key in profile_map:
                profile = profile_map[key]
                for col in ["专业技能", "证书要求", "创新能力", "学习能力", "抗压能力", "沟通能力", "实习能力",
                            "经验要求"]:
                    merged_data.loc[idx, col] = profile[col]

        # 保存整合文件
        merged_data.to_excel(OUTPUT_MERGED, index=False)
        print(f"✅ 原数据+画像整合文件已保存：{OUTPUT_MERGED}")

        return profile_df, merged_data


# ---------------------- 3. 测试官方调用（单独验证） ----------------------
def test_official_call():
    """单独测试官方示例调用是否正常"""
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


# ---------------------- 4. 执行入口 ----------------------
if __name__ == "__main__":
    # 先测试官方调用是否正常
    if not DEBUG_MODE:
        if not test_official_call():
            print("\n⚠️ API调用测试失败，请先解决密钥/网络问题！")
            sys.exit(1)
        print("✅ API调用测试通过，开始生成岗位画像...\n")

    try:
        generator = JobProfileGenerator()
        generator.generate_all_profiles()
        print("\n🎉 所有任务执行完成！")
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