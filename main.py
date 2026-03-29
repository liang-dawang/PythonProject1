from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.resume.router import resume_router
from app.resumedata.router import data_router

app = FastAPI()

# 🔥 跨域配置【修复版】
# 不能用 * + allow_credentials=True，浏览器直接封杀！
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(resume_router)

app.include_router(data_router)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)