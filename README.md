# AI-PPT

AI 驱动的智能演示文稿生成工具。上传文档或输入想法，AI 自动分析内容、生成大纲、设计页面并导出为 PDF 或图片。

## 功能特性

- **三种创建方式**：上传文档分析、一句话生成、大纲生成
- **风格参考**：上传参考图或文字描述风格，预设多种风格模板
- **内容关系识别**：自动识别并列/递进/总分/因果/对比/流程等关系
- **结构化图表**：根据内容关系自动生成对应的可视化图表
- **页面编辑**：单页重新生成、文字替换、遮罩局部重绘
- **多格式导出**：PDF、图片集 ZIP

## 技术栈

- **前端**：React 18 + TypeScript + Vite + TailwindCSS + Zustand
- **后端**：Python Flask + SQLite + OpenAI API
- **AI 模型**：
  - 分析模型：`[V]gemini-3.1-pro-preview`
  - 生图模型：`[V]gemini-3-flash-preview`
  - API 端点：`https://www.lemonapi.ai/v1`

## 快速开始

### 本地开发

**后端**：

```bash
cd backend
pip install -r requirements.txt
python app.py
```

**前端**：

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:3000

### Docker 部署

```bash
docker compose up -d
```

## 配置

编辑 `backend/.env`：

```env
OPENAI_API_KEY=your-api-key
OPENAI_API_BASE=https://www.lemonapi.ai/v1
TEXT_MODEL=[V]gemini-3.1-pro-preview
IMAGE_MODEL=[V]gemini-3-flash-preview
```

## 使用流程

1. 首页选择创建方式（上传文档/一句话/大纲）
2. 设置风格参考（上传参考图/描述风格/选择预设）
3. 编辑 AI 生成的大纲
4. 生成页面图片，逐页编辑优化
5. 导出为 PDF 或图片集
