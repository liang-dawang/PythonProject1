import pandas as pd
from neo4j import GraphDatabase
import re

# ---------------------- 1. 配置项（已更新为你的新Excel路径） ----------------------
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678"  # 你的密码
INPUT_FILE = r"E:\pycharm\PythonProject1\new\岗位画像单独文件（新）.xlsx"  # 已更新

# 岗位级别配置
JOB_LEVELS = ["初级", "中级", "高级", "顶级"]

# 所有岗位列表（含级别）
ALL_JOBS = [
    ("C/C++", "初级"), ("C/C++", "中级"), ("C/C++", "高级"),
    ("Java", "初级"), ("Java", "中级"), ("Java", "高级"),
    ("前端开发", "初级"), ("前端开发", "中级"), ("前端开发", "高级"),
    ("实施工程师", "初级"), ("实施工程师", "中级"), ("实施工程师", "高级"),
    ("技术支持工程师", "初级"), ("技术支持工程师", "中级"), ("技术支持工程师", "高级"),
    ("测试工程师", "初级"), ("测试工程师", "中级"), ("测试工程师", "高级"),
    ("硬件测试", "初级"), ("硬件测试", "中级"), ("硬件测试", "高级"),
    ("软件测试", "初级"), ("软件测试", "中级"), ("软件测试", "高级"),
    ("科研人员", "顶级"),
    ("项目经理/主管", "顶级")
]

# 同岗位垂直晋升
INTERNAL_PROMOTION_MAP = {
    "C/C++初级": "C/C++中级",
    "C/C++中级": "C/C++高级",
    "Java初级": "Java中级",
    "Java中级": "Java高级",
    "前端开发初级": "前端开发中级",
    "前端开发中级": "前端开发高级",
    "实施工程师初级": "实施工程师中级",
    "实施工程师中级": "实施工程师高级",
    "技术支持工程师初级": "技术支持工程师中级",
    "技术支持工程师中级": "技术支持工程师高级",
    "测试工程师初级": "测试工程师中级",
    "测试工程师中级": "测试工程师高级",
    "硬件测试初级": "硬件测试中级",
    "硬件测试中级": "硬件测试高级",
    "软件测试初级": "软件测试中级",
    "软件测试中级": "软件测试高级"
}

# 跨岗位晋升
CROSS_PROMOTION_MAP = [
    ("C/C++高级", "项目经理/主管顶级"),
    ("Java高级", "项目经理/主管顶级"),
    ("前端开发高级", "项目经理/主管顶级"),
    ("实施工程师高级", "项目经理/主管顶级"),
    ("技术支持工程师高级", "项目经理/主管顶级"),
    ("测试工程师高级", "项目经理/主管顶级"),
    ("硬件测试高级", "项目经理/主管顶级"),
    ("软件测试高级", "项目经理/主管顶级"),
    ("科研人员顶级", "项目经理/主管顶级")
]

# 横向换岗路径
TRANSFER_BASE = {
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


# ---------------------- 2. Neo4j 操作类（完全保留） ----------------------
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

    def create_job_node(self, job_full_name, skills="", cert="", exp=""):
        job_name = None
        job_level = None
        for level in JOB_LEVELS:
            if job_full_name.endswith(level):
                job_name = job_full_name[:-len(level)]
                job_level = level
                break

        if isinstance(skills, str):
            skills_list = [s.strip() for s in re.split(r'[,，;；]', skills) if s.strip()]
        else:
            skills_list = []

        cert = cert.strip() if isinstance(cert, str) else "无"
        exp = exp.strip() if isinstance(exp, str) else "无"

        query = """
        MERGE (j:Job {name: $job_full_name})
        SET j.job_name = $job_name,
            j.level = $job_level,
            j.skills = $skills,
            j.skills_str = $skills_str,
            j.cert = $cert,
            j.exp = $exp
        """
        with self.driver.session() as session:
            session.run(
                query,
                job_full_name=job_full_name,
                job_name=job_name,
                job_level=job_level,
                skills=skills_list,
                skills_str=skills,
                cert=cert,
                exp=exp
            )

    def create_internal_promotion(self):
        for from_node, to_node in INTERNAL_PROMOTION_MAP.items():
            query = """
            MATCH (a:Job {name: $from_node})
            MATCH (b:Job {name: $to_node})
            MERGE (a)-[r:PROMOTE_TO {type: '垂直晋升', desc: '同岗位技术晋升'}]->(b)
            """
            with self.driver.session() as session:
                session.run(query, from_node=from_node, to_node=to_node)

    def create_cross_promotion(self):
        for from_node, to_node in CROSS_PROMOTION_MAP:
            query = """
            MATCH (a:Job {name: $from_node})
            MATCH (b:Job {name: $to_node})
            MERGE (a)-[r:PROMOTE_TO {type: '跨岗晋升', desc: '技术转管理/专家岗'}]->(b)
            """
            with self.driver.session() as session:
                session.run(query, from_node=from_node, to_node=to_node)

    def create_transfer_paths(self):
        transfer_mapping = {}
        for from_base, to_bases in TRANSFER_BASE.items():
            for level in ["初级", "中级", "高级"]:
                from_full = f"{from_base}{level}"
                if from_full not in [job[0] + job[1] for job in ALL_JOBS]:
                    continue
                transfer_mapping[from_full] = []
                for to_base in to_bases:
                    to_level = level if (to_base, level) in ALL_JOBS else "顶级"
                    to_full = f"{to_base}{to_level}"
                    transfer_mapping[from_full].append(to_full)
            if (from_base, "顶级") in ALL_JOBS:
                from_full = f"{from_base}顶级"
                transfer_mapping[from_full] = []
                for to_base in to_bases:
                    to_level = "顶级" if (to_base, "顶级") in ALL_JOBS else "高级"
                    to_full = f"{to_base}{to_level}"
                    transfer_mapping[from_full].append(to_full)

        for from_node, to_nodes in transfer_mapping.items():
            for to_node in to_nodes:
                query = """
                MATCH (a:Job {name: $from_node})
                MATCH (b:Job {name: $to_node})
                MERGE (a)-[r:CAN_TRANSFER_TO {type: '横向换岗', desc: '岗位能力迁移'}]->(b)
                """
                with self.driver.session() as session:
                    session.run(query, from_node=from_node, to_node=to_node)

    def get_promotion_skills(self, job_full_name):
        query = """
        MATCH (current:Job {name: $job_full_name})-[r:PROMOTE_TO]->(target:Job)
        WITH current, target, r
        UNWIND target.skills AS target_skill
        WITH current, target, r, collect(DISTINCT target_skill) AS target_skills
        UNWIND current.skills AS current_skill
        WITH current, target, r, target_skills, collect(DISTINCT current_skill) AS current_skills
        WITH current, target, r, 
             [skill IN target_skills WHERE NOT skill IN current_skills] AS missing_skills
        RETURN 
            current.name AS 当前岗位,
            target.name AS 晋升目标,
            r.type AS 晋升类型,
            missing_skills AS 需要学习的技能,
            size(missing_skills) AS 技能缺口数,
            target.exp AS 目标岗位经验要求
        ORDER BY 技能缺口数 DESC
        """
        with self.driver.session() as session:
            result = session.run(query, job_full_name=job_full_name)
            return pd.DataFrame([record.data() for record in result])

    def get_transfer_skills(self, job_full_name):
        query = """
        MATCH (current:Job {name: $job_full_name})-[r:CAN_TRANSFER_TO]->(target:Job)
        WITH current, target, r
        UNWIND target.skills AS target_skill
        WITH current, target, r, collect(DISTINCT target_skill) AS target_skills
        UNWIND current.skills AS current_skill
        WITH current, target, r, target_skills, collect(DISTINCT current_skill) AS current_skills
        WITH current, target, r, 
             [skill IN target_skills WHERE NOT skill IN current_skills] AS missing_skills
        RETURN 
            current.name AS 当前岗位,
            target.name AS 换岗目标,
            r.type AS 换岗类型,
            missing_skills AS 需要学习的技能,
            size(missing_skills) AS 技能缺口数,
            target.exp AS 目标岗位经验要求
        ORDER BY 技能缺口数 DESC
        """
        with self.driver.session() as session:
            result = session.run(query, job_full_name=job_full_name)
            return pd.DataFrame([record.data() for record in result])


# ---------------------- 3. 主流程（已完善，路径正确） ----------------------
def build_real_career_graph():
    # 读取新Excel
    try:
        df = pd.read_excel(INPUT_FILE, engine='openpyxl')
        print(f"✅ 成功加载新Excel：{len(df)} 条数据")
    except Exception as e:
        print(f"❌ 加载失败：{e}")
        return

    graph = RealJobGraph(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    graph.clear_db()

    print("\n===== 开始创建岗位节点 =====")
    for job_base, level in ALL_JOBS:
        job_full_name = f"{job_base}{level}"
        row = df[(df["岗位名称"] == job_base) & (df["岗位级别"] == level)]

        # 安全读取数据
        skills = row["专业技能"].values[0] if len(row) > 0 and not pd.isna(row["专业技能"].values[0]) else "无"
        cert = row["证书要求"].values[0] if len(row) > 0 and not pd.isna(row["证书要求"].values[0]) else "无"
        exp = row["经验要求"].values[0] if len(row) > 0 and not pd.isna(row["经验要求"].values[0]) else "无"

        graph.create_job_node(job_full_name, skills, cert, exp)
        print(f"✅ {job_full_name}")

    # 构建关系
    graph.create_internal_promotion()
    graph.create_cross_promotion()
    graph.create_transfer_paths()

    # 示例查询
    print("\n===== Java 初级 晋升技能 =====")
    print(graph.get_promotion_skills("Java初级").to_string(index=False))

    print("\n===== Java 中级 换岗技能 =====")
    print(graph.get_transfer_skills("Java中级").to_string(index=False))

    graph.close()
    print("\n🎉 职业图谱构建完成！")


# ---------------------- 运行 ----------------------
if __name__ == "__main__":
    build_real_career_graph()