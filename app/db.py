# app/db.py
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import async_sessionmaker  # 确保导入
import os
from dotenv import load_dotenv

# 加载环境变量（如果你有的话）
load_dotenv()

# 1. 配置数据库连接
# 从你的截图中读取 URL
DATABASE_URL = "postgresql+asyncpg://postgres:postgres123@localhost:5432/career_platform"
# 注意：如果是异步引擎，需要指定驱动为 postgresql+asyncpg，或者确保 create_engine 支持异步

# 2. 创建异步引擎（关键：使用 async_engine）
from sqlalchemy.ext.asyncio import create_async_engine

engine = create_async_engine(DATABASE_URL, echo=True)

# 3. 定义异步会话
async_session = async_sessionmaker(engine, expire_on_commit=False)


# 4. 测试连接（可选）
async def test_connection():
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            print("✅ PostgreSQL 异步连接成功！")
    except Exception as e:
        print(f"❌ 连接失败: {e}")


# 5. 你需要的核心函数：获取最新学生画像
async def get_latest_student_profile():
    try:
        async with async_session() as session:
            result = await session.execute(text("""
                SELECT * FROM student_ability_profile 
                ORDER BY id DESC LIMIT 1;
            """))
            row = result.first()

            if not row:
                return None

            student_data = {key: value for key, value in row._asdict().items()}

            # 🔥 🔥 🔥 关键：删除时间字段！避免序列化失败！
            if "create_time" in student_data:
                del student_data["create_time"]

            print("✅ 成功获取学生数据（已清理时间字段）")
            return student_data

    except Exception as e:
        print(f"❌ 查询失败: {str(e)}")
        return None