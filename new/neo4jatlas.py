import pandas as pd
from neo4j import GraphDatabase

# ---------------------- 1. 配置项 ----------------------
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678"  # 替换为你的密码
INPUT_FILE = r"E:\pycharm\PythonProject1\岗位画像单独文件.xlsx"

# 现实晋升规则
LEVEL_HIERARCHY = ["初级", "中级", "高级"]  # 技术岗基础晋升
TOP_LEVELS = ["顶级"]  # 管理/专家岗

# 同岗位垂直晋升（现实路径）
INTERNAL_PROMOTION = {
    "C/C++": ["初级", "中级", "高级"],
    "Java": ["初级", "中级", "高级"],
    "前端开发": ["初级", "中级", "高级"],
    "实施工程师": ["初级", "中级", "高级"],
    "技术支持工程师": ["初级", "中级", "高级"],
    "测试工程师": ["初级", "中级", "高级"],
    "硬件测试": ["初级", "中级", "高级"],
    "软件测试": ["初级", "中级", "高级"],
    "科研人员": ["顶级"],  # 专家岗，无内部晋升
    "项目经理/主管": ["顶级"]  # 管理岗，无内部晋升
}

# 跨岗位晋升（现实技术→管理路径）
CROSS_PROMOTION = [
    # 所有高级技术岗 → 项目经理/主管
    ("C/C++", "高级", "项目经理/主管", "顶级"),
    ("Java", "高级", "项目经理/主管", "顶级"),
    ("前端开发", "高级", "项目经理/主管", "顶级"),
    ("实施工程师", "高级", "项目经理/主管", "顶级"),
    ("技术支持工程师", "高级", "项目经理/主管", "顶级"),
    ("测试工程师", "高级", "项目经理/主管", "顶级"),
    ("硬件测试", "高级", "项目经理/主管", "顶级"),
    ("软件测试", "高级", "项目经理/主管", "顶级"),
    ("科研人员", "顶级", "项目经理/主管", "顶级")  # 专家转管理
]

# 横向换岗（现实可行路径，每个岗位≥2条）
TRANSFER_PATHS = {
    "C/C++": ["Java", "硬件测试", "实施工程师"],
    "Java": ["C/C++", "软件测试", "技术支持工程师"],
    "前端开发": ["测试工程师", "实施工程师", "项目经理/主管"],
    "实施工程师": ["技术支持工程师", "前端开发", "项目经理/主管"],
    "技术支持工程师": ["实施工程师", "测试工程师", "项目经理/主管"],
    "测试工程师": ["软件测试", "硬件测试", "Java"],
    "硬件测试": ["测试工程师", "C/C++", "科研人员"],
    "软件测试": ["测试工程师", "Java", "前端开发"],
    "科研人员": ["硬件测试", "C/C++", "项目经理/主管"],
    "项目经理/主管": ["技术支持工程师", "实施工程师", "前端开发"]
}


# ---------------------- 2. Neo4j操作类 ----------------------
class RealJobGraph:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def clear_db(self):
        confirm = input("⚠️ 确定清空所有数据？输入 'YES' 确认：")
        if confirm != "YES":
            print("🚫 操作取消")
            return
        with self.driver.session() as session:
            session.run("MATCH ()-[r]->() DELETE r")
            session.run("MATCH (n) DELETE n")
            print("✅ 数据库已清空")

    def create_job_node(self, job_name, job_level, skills="", cert="", exp=""):
        query = """
        MERGE (j:Job {name: $job_name, level: $job_level})
        SET j.skills = $skills, j.cert = $cert, j.exp = $exp
        """
        with self.driver.session() as session:
            session.run(query, job_name=job_name, job_level=job_level, skills=skills, cert=cert, exp=exp)
            print(f"✅ 节点：{job_name}-{job_level}")

    def create_internal_promotion(self):
        """创建同岗位垂直晋升"""
        for job, levels in INTERNAL_PROMOTION.items():
            for i in range(len(levels) - 1):
                from_lvl = levels[i]
                to_lvl = levels[i + 1]
                query = """
                MATCH (a:Job {name: $job, level: $from_lvl})
                MATCH (b:Job {name: $job, level: $to_lvl})
                MERGE (a)-[r:PROMOTE_TO {type: '垂直晋升', desc: '同岗位技术晋升'}]->(b)
                """
                with self.driver.session() as session:
                    session.run(query, job=job, from_lvl=from_lvl, to_lvl=to_lvl)
                    print(f"✅ 晋升：{job}-{from_lvl} → {job}-{to_lvl}")

    def create_cross_promotion(self):
        """创建跨岗位晋升（技术→管理）"""
        for from_job, from_lvl, to_job, to_lvl in CROSS_PROMOTION:
            query = """
            MATCH (a:Job {name: $from_job, level: $from_lvl})
            MATCH (b:Job {name: $to_job, level: $to_lvl})
            MERGE (a)-[r:PROMOTE_TO {type: '跨岗晋升', desc: '技术转管理/专家岗'}]->(b)
            """
            with self.driver.session() as session:
                session.run(query, from_job=from_job, from_lvl=from_lvl, to_job=to_job, to_lvl=to_lvl)
                print(f"✅ 跨岗晋升：{from_job}-{from_lvl} → {to_job}-{to_lvl}")

    def create_transfer_paths(self):
        """创建横向换岗路径"""
        for from_job, to_jobs in TRANSFER_PATHS.items():
            with self.driver.session() as session:
                res = session.run("MATCH (a:Job {name: $job}) RETURN a.level", job=from_job)
                from_lvls = [r["a.level"] for r in res]

            for from_lvl in from_lvls:
                for to_job in to_jobs:
                    with self.driver.session() as session:
                        res = session.run("MATCH (b:Job {name: $job}) RETURN b.level", job=to_job)
                        to_lvls = [r["b.level"] for r in res]
                    to_lvl = from_lvl if from_lvl in to_lvls else ("顶级" if "顶级" in to_lvls else to_lvls[0])

                    query = """
                    MATCH (a:Job {name: $from_job, level: $from_lvl})
                    MATCH (b:Job {name: $to_job, level: $to_lvl})
                    MERGE (a)-[r:CAN_TRANSFER_TO {type: '横向换岗', desc: '岗位能力迁移'}]->(b)
                    """
                    with self.driver.session() as session:
                        session.run(query, from_job=from_job, from_lvl=from_lvl, to_job=to_job, to_lvl=to_lvl)
                        print(f"✅ 换岗：{from_job}-{from_lvl} → {to_job}-{to_lvl}")


# ---------------------- 3. 主流程 ----------------------
def build_real_career_graph():
    # 1. 加载岗位数据
    try:
        df = pd.read_excel(INPUT_FILE)
    except:
        df = pd.DataFrame(columns=["岗位名称", "岗位级别", "专业技能", "证书要求", "经验要求"])

    # 2. 初始化Neo4j
    graph = RealJobGraph(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    graph.clear_db()

    # 3. 创建所有岗位节点
    job_levels = [
        ("C/C++", "中级"), ("C/C++", "初级"), ("C/C++", "高级"),
        ("Java", "中级"), ("Java", "初级"), ("Java", "高级"),
        ("前端开发", "中级"), ("前端开发", "初级"), ("前端开发", "高级"),
        ("实施工程师", "中级"), ("实施工程师", "初级"), ("实施工程师", "高级"),
        ("技术支持工程师", "中级"), ("技术支持工程师", "初级"), ("技术支持工程师", "高级"),
        ("测试工程师", "中级"), ("测试工程师", "初级"), ("测试工程师", "高级"),
        ("硬件测试", "中级"), ("硬件测试", "初级"), ("硬件测试", "高级"),
        ("科研人员", "顶级"),
        ("软件测试", "中级"), ("软件测试", "初级"), ("软件测试", "高级"),
        ("项目经理/主管", "顶级")
    ]
    for job, lvl in job_levels:
        row = df[(df["岗位名称"] == job) & (df["岗位级别"] == lvl)]
        skills = row["专业技能"].values[0] if len(row) else "无"
        cert = row["证书要求"].values[0] if len(row) else "无"
        exp = row["经验要求"].values[0] if len(row) else "无"
        graph.create_job_node(job, lvl, skills, cert, exp)

    # 4. 构建晋升与换岗
    graph.create_internal_promotion()
    graph.create_cross_promotion()
    graph.create_transfer_paths()

    graph.close()
    print("\n🎉 现实职业路径图谱构建完成！")


# ---------------------- 4. 验证查询 ----------------------
if __name__ == "__main__":
    build_real_career_graph()
    print("""
📌 查看现实路径的Cypher语句：
1. 查看Java完整职业路径：
MATCH p=(a:Job {name:"Java", level:"初级"})-[*]->(b:Job {name:"项目经理/主管"})
RETURN p

2. 查看所有技术→管理的晋升路径：
MATCH (a)-[r:PROMOTE_TO {type:"跨岗晋升"}]->(b:Job {name:"项目经理/主管"})
RETURN a.name, a.level, r.desc, b.name

3. 查看前端开发的换岗路径：
MATCH (a:Job {name:"前端开发"})-[r:CAN_TRANSFER_TO]->(b)
RETURN a.name, a.level, r.type, b.name, b.level
""")