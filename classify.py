import pandas as pd
import re

# 1. 加载5000条岗位数据（假设是Excel格式，你替换成自己的文件路径）
df = pd.read_excel("5000条岗位数据_最终分类.xlsx")
# 确保关键字段非空
df["岗位名称"] = df["岗位名称"].fillna("")
df["岗位详情"] = df["岗位详情"].fillna("")

category_keywords = {
    # 前端类优先
    "前端开发类": ["前端", "Vue", "React", "HTML", "CSS", "JS", "小程序", "H5",
                   "Web开发", "前端开发", "移动端开发", "uniapp", "小程序开发", "前端工程师"],
    "后端开发类": ["后端", "Java", "Python", "Go", "C\\+\\+", "Spring", "微服务", "分布式"],
    "软件测试类": ["测试", "自动化测试", "功能测试", "性能测试", "Selenium", "Jmeter"],
    "硬件开发与测试类": ["硬件", "电路", "PCB", "示波器", "硬件测试", "嵌入式", "单片机"],
    "技术支持与运维类": ["运维", "Linux", "Docker", "K8s", "技术支持", "故障排查"],
    "实施交付类": ["实施", "交付", "现场部署", "项目上线", "用户培训"],
    "项目管理类": ["项目管理", "PM", "项目经理", "需求分析", "进度管控"],
    "产品相关类": ["产品", "PM", "产品经理", "原型设计", "PRD", "需求调研"],
    # 修复科研与算法类：仅匹配计算机相关科研/算法岗
    "科研与算法类": ["算法", "机器学习", "深度学习", "数据挖掘", "计算机科研", "AI科研", "算法研发"],
    "全栈开发类": ["全栈", "前后端", "全栈开发", "全栈工程师"]
}

# 新增：非计算机类科研岗排除关键词（生物/化学/医学等）
exclude_keywords = ["分子生物学", "生物技术", "生物化学", "测序", "实验", "实验室",
                    "医学", "化学", "化工", "药学", "生物实验", "NGS", "长读长测序"]


# 优化分类函数（加入排除逻辑）
def classify_job(row):
    # 合并字段并转小写
    text = (row["岗位名称"] + " " + row["岗位详情"]).lower()

    # 第一步：先检查是否包含非计算机类关键词，若包含直接归为其他类
    for exclude_word in exclude_keywords:
        if re.search(re.escape(exclude_word.lower()), text, re.IGNORECASE):
            return "其他类"

    # 第二步：按分类规则匹配核心岗位
    for category, keywords in category_keywords.items():
        for keyword in keywords:
            if re.search(re.escape(keyword.lower()), text, re.IGNORECASE):
                return category

    # 未匹配到归为其他类
    return "其他类"

# 4. 执行分类
df["岗位大类"] = df.apply(classify_job, axis=1)

# 5. 保存分类结果（方便后续处理）
df.to_excel("5000条岗位数据_最终分类2.xlsx", index=False)

# 6. 打印分类统计（看分布是否合理）
print("分类结果统计：")
print(df["岗位大类"].value_counts())