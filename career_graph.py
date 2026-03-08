from neo4j import GraphDatabase

# 连接 Neo4j（密码改成你实际设置的8位及以上密码）
driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "12345678"))


# 1. 创建岗位节点（单独执行，避免语法冲突）
def create_job_nodes():
    with driver.session() as session:
        # 分步创建节点，避免多语句语法错误
        session.run("""
            CREATE (junior:Job {name: 'Java开发工程师', level: '初级', salary: '8-15K', desc: '负责业务模块开发'})
            CREATE (senior:Job {name: '高级Java开发', level: '中级', salary: '15-25K', desc: '负责核心系统设计'})
            CREATE (tech_lead:Job {name: '技术主管', level: '高级', salary: '25-40K', desc: '负责团队管理和技术规划'})
            CREATE (architect:Job {name: '架构师', level: '专家', salary: '40-80K', desc: '负责技术架构设计'})
        """)
    print("✅ 岗位节点创建成功！")


# 2. 创建晋升关系（节点创建完成后再建关系）
def create_promote_relations():
    with driver.session() as session:
        # 分步创建关系，避免多语句语法错误
        session.run("""
            MATCH (junior:Job {name: 'Java开发工程师'}), (senior:Job {name: '高级Java开发'})
            CREATE (junior)-[:PROMOTE_TO {requirement: '3年经验+微服务技术栈'}]->(senior)
        """)

        session.run("""
            MATCH (senior:Job {name: '高级Java开发'}), (tech_lead:Job {name: '技术主管'})
            CREATE (senior)-[:PROMOTE_TO {requirement: '5年经验+团队管理经验'}]->(tech_lead)
        """)

        session.run("""
            MATCH (tech_lead:Job {name: '技术主管'}), (architect:Job {name: '架构师'})
            CREATE (tech_lead)-[:PROMOTE_TO {requirement: '8年经验+架构设计能力'}]->(architect)
        """)
    print("✅ 晋升关系创建成功！")


# 3. 查询最短晋升路径（兼容所有Neo4j版本的写法）
def query_career_path():
    with driver.session() as session:
        # 改用UNWIND拆解路径节点，兼容低版本Neo4j
        result = session.run("""
            MATCH path = shortestPath((start:Job {name: 'Java开发工程师'})-[:PROMOTE_TO*]->(end:Job {name: '架构师'}))
            UNWIND nodes(path) AS node
            RETURN collect(node.name) AS career_path
        """)
        record = result.single()
        if record and record["career_path"]:
            print("📈 最短晋升路径：", record["career_path"])
        else:
            print("❌ 未找到晋升路径")


# 4. 清空重复数据（可选，避免重复创建）
def clear_duplicate_data():
    with driver.session() as session:
        session.run("MATCH (n:Job) DELETE n")
    print("🗑️ 已清空原有岗位数据！")


if __name__ == "__main__":
    # 先清空旧数据（如果之前重复创建过，取消注释执行）
    # clear_duplicate_data()

    # 分步执行，避免语法错误
    create_job_nodes()
    create_promote_relations()
    query_career_path()

    # 关闭连接
    driver.close()