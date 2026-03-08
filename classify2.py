import pandas as pd
import re

# ===================== 配置 =====================
INPUT_FILE = "分类完数据.xlsx"  # 你的9大类数据文件
OUTPUT_FILE = "9大类+后端运维细分_通用兜底版.xlsx"
# =================================================

# 读取数据
df = pd.read_excel(INPUT_FILE)
print(f"📥 读取数据完成，总数据量：{len(df)}")

# --------------------- 核心配置（精准匹配+通用兜底） ---------------------
# 后端细分关键词（优先匹配「明确指定」的场景）
JAVA_KEYWORDS = {"java", "spring", "springboot", "springcloud", "mybatis", "jpa"}
PYTHON_KEYWORDS = {"python", "django", "flask", "fastapi", "scrapy"}
CPP_KEYWORDS = {"c++", "cpp", "c/c++", "stl", "qt", "boost"}
# 通用后端标记（匹配"熟悉XX/XX/XX中的一种"这类兜底描述）
GENERAL_BACKEND_PATTERN = re.compile(
    r"熟悉掌握但不限于.*(java|python|c\+\+|go|c#).*中的一种|精通.*(java|python|c\+\+).*或.*")

# 运维细分关键词
OPS_KEYWORDS = {"linux", "服务器", "docker", "k8s", "云运维", "监控"}
SUPPORT_KEYWORDS = {"技术支持", "售后", "客户支持", "实施", "故障处理"}


def classify_backend_ops(row):
    """
    核心逻辑：
    1. 优先按「岗位名称」判断（名称明确则直接归类）
    2. 再按「岗位详情」判断（有单一技术栈偏向则归类）
    3. 多语言兜底 → 标注为「通用后端开发」
    4. 无任何线索 → 标注为「后端开发类（未细分）」
    """
    cate = str(row["岗位大类"]).strip()
    job_name = str(row["岗位名称"]).lower() if pd.notna(row["岗位名称"]) else ""
    job_detail = str(row["岗位详情"]).lower() if pd.notna(row["岗位详情"]) else ""

    # ========== 后端开发类细分 ==========
    if cate == "后端开发类":
        # Step1：优先看岗位名称（名称明确则直接归类）
        if any(kw in job_name for kw in JAVA_KEYWORDS):
            return "Java后端开发"
        elif any(kw in job_name for kw in PYTHON_KEYWORDS):
            return "Python后端开发"
        elif any(kw in job_name for kw in CPP_KEYWORDS):
            return "C++后端开发"

        # Step2：看岗位详情，统计单一技术栈频次（排除"多种选一种"的场景）
        java_cnt = sum(1 for k in JAVA_KEYWORDS if k in job_detail)
        python_cnt = sum(1 for k in PYTHON_KEYWORDS if k in job_detail)
        cpp_cnt = sum(1 for k in CPP_KEYWORDS if k in job_detail)
        max_cnt = max(java_cnt, python_cnt, cpp_cnt)

        # Step3：判断是否是"多语言兜底"场景
        is_general = GENERAL_BACKEND_PATTERN.search(row["岗位详情"]) is not None

        if is_general:
            # 多语言兜底 → 通用后端开发
            return "通用后端开发"
        elif max_cnt > 0:
            # 有单一技术栈偏向 → 按最高频次归类
            if max_cnt == java_cnt:
                return "Java后端开发"
            elif max_cnt == python_cnt:
                return "Python后端开发"
            else:
                return "C++后端开发"
        else:
            # 无任何线索 → 未细分
            return "后端开发类（未细分）"

    # ========== 技术支持与运维类细分 ==========
    elif cate == "技术支持与运维类":
        ops_cnt = sum(1 for k in OPS_KEYWORDS if k in job_detail + job_name)
        sup_cnt = sum(1 for k in SUPPORT_KEYWORDS if k in job_detail + job_name)

        if ops_cnt > sup_cnt:
            return "系统运维/云运维"
        elif sup_cnt > ops_cnt:
            return "技术支持/售后实施"
        else:
            return "技术支持与运维类（未细分）"

    # ========== 其他7类不变 ==========
    else:
        return cate


# --------------------- 执行分类 ---------------------
print("🚀 开始细分（适配多语言通用后端）...")
df["细分岗位大类"] = df.apply(classify_backend_ops, axis=1)

# --------------------- 保存+统计 ---------------------
df.to_excel(OUTPUT_FILE, index=False)
print(f"\n✅ 细分完成！文件已保存至：{OUTPUT_FILE}")

# 精准统计
print("\n📊 最终分类统计（核心类别）：")
core_cates = [
    "Java后端开发", "Python后端开发", "C++后端开发", "通用后端开发", "后端开发类（未细分）",
    "系统运维/云运维", "技术支持/售后实施", "技术支持与运维类（未细分）"
]
stats = df["细分岗位大类"].value_counts()
for c in core_cates:
    print(f"   {c}：{stats.get(c, 0)}条")
print(f"   其他7大类汇总：{sum(stats.values) - sum(stats.get(c, 0) for c in core_cates)}条")