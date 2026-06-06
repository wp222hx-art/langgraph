# Paydaes ClaimGPT · AI Native 报销智能平台 V3.0

> "不再是一个让你填表的系统,而是一群替你思考的智能体。"

## 项目概述
- **名称**:Paydaes ClaimGPT —— AI Native 报销智能平台
- **目标**:用 AI Agent 架构重构传统报销 SaaS,把 18 个填表模块进化为 5 个会对话的智能体
- **核心理念**:表单 → 对话,人类只做最终审批
- **技术底座**:LangGraph 编排引擎(Orchestrator-Worker 双层架构)

## ✅ 已完成功能(阶段一:架构验证 MVP)
- **5 主 Agent + 8 子 Agent** 双层编排,基于 LangGraph StateGraph 实现
- **18 个业务模块全部跑通**(模块路由命中率 18/18 = 100%)
- **对话式流畅前端**:5 智能体切换、SSE 流式打字机、思考过程可视化、卡片混合界面
- **人机协同(Human-in-the-loop)**:高风险单据触发 L2 协同,人类最终审批
- **Checkpoint 持久化**:基于 MemorySaver,支持会话记忆与长事务断点续跑

## 🤖 5 主 Agent × 18 模块映射
| 主 Agent | 承接模块 |
|---------|---------|
| 🙋 ClaimMate 报销伙伴 | 报销申请-自助、商务差旅申请-自助、商务差旅报销-自助、家庭信息 |
| ✅ ApprovalCopilot 审批副驾 | 报销申请-管理、差旅申请-管理、差旅报销-管理 |
| 🧠 HRStrategist HR战略顾问 | 报销类型、报销组、报销权益、生成权益流程、余额调整 |
| ⚙️ PayrollNavigator 薪资领航员 | 报销接口流程、审核接口数据、汇率 |
| 📊 InsightOracle 洞察先知 | 福利使用报表、差旅申请报表、报销申请报表 |

## 🌐 功能入口 URI
- `GET  /` —— 前端主页面(对话式 UI)
- `GET  /api/agents` —— 5 主 Agent 元信息
- `GET  /api/modules` —— 18 模块清单
- `POST /api/chat` —— 一次性对话(body: `{message, thread_id}`)
- `GET  /api/chat/stream?message=&thread_id=` —— SSE 流式对话(思考链 + 打字机 + 卡片)

## 🏗️ 技术架构(轻量化重构后)
```
前端: HTML + TailwindCSS + Chart.js (纯CDN,零构建)
  ↓ SSE 流式
AI编排: Python + FastAPI + LangGraph StateGraph
  · Orchestrator 意图路由 → 5主Agent → 8子Agent → 人机协同
  · MemorySaver Checkpoint 持久化
数据: Mock内存(阶段二替换为 Supabase Postgres+pgvector)
```

## 数据架构
- **状态模型**:`ClaimState`(消息/意图/抽取/校验/风险/政策/审批/卡片/思考链)
- **当前存储**:内存 Mock(报销类型、员工权益、待审单据、汇率、家属等)
- **阶段二**:Supabase(Postgres + pgvector)替换 Mock,实现三层记忆

## 🚀 本地运行
```bash
cd /home/user/claimgpt
pm2 start ecosystem.config.cjs   # 启动(端口 3000)
curl http://localhost:3000/api/modules  # 健康检查
pm2 logs claimgpt --nostream     # 查看日志
```

## 📋 用户指南
1. 打开页面,左侧是 5 个智能体团队成员
2. 直接用大白话对话,或点击示例气泡(系统会自动路由到正确的智能体)
3. 观察:思考过程可视化 → 打字机回复 → 结构化卡片
4. 审批高风险单据时,会看到「L2 人机协同」标志,体现人类最终审批权

## 🔜 未实现 / 下一步
- 接入真实 LLM(Claude/GPT/DeepSeek 多模型路由)替换规则引擎
- 接入 Supabase 实现三层记忆与状态持久化(阶段二)
- 接入真实 OCR、汇率 API、薪资接口工具(MCP)
- `interrupt()` 真正暂停-恢复的审批流(当前为标志位演示)
- 生产部署(FastAPI 上云 + 前端 Cloudflare Pages)

## 部署
- **平台**:沙盒(阶段一)
- **状态**:✅ 运行中
- **技术栈**:Python 3.13 + FastAPI + LangGraph 1.2.4 + TailwindCSS
- **最后更新**:2026-06-06
