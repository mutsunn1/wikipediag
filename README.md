# wikipediagent

基于Oxygent框架的Wikipedia内容自动爬取与智能分类系统。

## ✨ 核心特性

- 🤖 **自动分类**: AI分析内容后自动归纳分类，无需预定义
- 📁 **本地保存**: 按分类自动创建文件夹，保存Markdown文件
- 📝 **Markdown索引**: 生成美观的索引文件，支持中英文
- 🌐 **多语言支持**: 默认简体中文，可配置为英文
- ⚡ **并行分析**: 多SubAgent并行分析页面
- 📋 **Plan-Execute**: Agent先规划再执行

## 📁 输出结构

```
output/
├── content/                          # 内容文件夹
│   └── Computer Science/             # 领域文件夹
│       ├── 数据结构/                  # 分类文件夹（中文）
│       │   ├── Array data structure.md
│       │   ├── Linked list.md
│       │   └── ...
│       ├── 算法/                      # 另一个分类
│       │   ├── Sorting algorithm.md
│       │   └── ...
│       └── 操作系统/                  # 再一个分类
│           └── ...
│
├── index/                            # 索引文件夹
│   └── Computer Science_index.md     # Markdown索引文件
│
└── Computer Science_data.json        # 原始JSON数据
```

### Markdown索引示例

```markdown
# Computer Science - Wikipedia 内容索引

*2024-01-15 10:30*

## 📊 概述

- **总页面数:** 50
- **分类列表:** 8

本次爬取涵盖计算机科学领域的核心内容，已自动分类为数据结构、算法、操作系统等8个主要类别...

## 目录

1. [数据结构](#数据结构) - 12 pages
2. [算法](#算法) - 15 pages
3. [操作系统](#操作系统) - 10 pages
...

---

## 📁 数据结构

*计算机中组织和存储数据的方式*

**页面数量:** 12

### Array data structure

- **链接:** [https://en.wikipedia.org/wiki/Array_data_structure](...)
- **摘要:** 数组是一种基础数据结构，元素存储在连续的内存位置...
- **关键概念:** array, index, memory, contiguous

### Linked list

- **链接:** [https://en.wikipedia.org/wiki/Linked_list](...)
- **摘要:** 链表是一种线性数据结构，元素通过指针连接...
- **关键概念:** node, pointer, dynamic

---

*由 Oxygent Wikipedia Crawler 自动生成*
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入你的API密钥
```

### 3. 运行程序

| 命令 | 说明 |
|------|------|
| `python main.py` | 标准模式：爬取50个CS页面，中文输出 |
| `python main.py --output ./my_data` | 指定输出目录为 `./my_data` |
| `python main.py --demo --output ./demo_output` | 演示模式 + 指定输出目录 |
| `python main.py --custom "Physics" 30 zh --output ./physics_data` | 自定义爬取 + 指定输出目录 |

## 📖 使用示例

### 标准模式（默认）

```python
# main.py 中的配置
crawl_configs = [
    {
        "domain": "Computer Science",
        "max_pages": 50,
        "language": "zh"  # 简体中文
    },
]
```

运行：
```bash
python main.py
```

### 自定义爬取

```python
# 使用命令行参数
python main.py --custom "Artificial Intelligence" 40 zh

# 或修改代码
async def main():
    crawl_configs = [
        {
            "domain": "Artificial Intelligence",
            "max_pages": 40,
            "language": "zh"
        },
        {
            "domain": "Physics",
            "max_pages": 30,
            "language": "en"  # 英文输出
        },
    ]
    # ...
```

### 指定输出文件夹

#### 命令行参数
```bash
# 标准模式，指定输出目录
python main.py --output ./my_data

# 演示模式，指定输出目录
python main.py --demo --output ./demo_output

# 自定义爬取，指定输出目录
python main.py --custom "Physics" 30 zh --output ./physics_data
```

#### 代码中配置
```python
# main.py 中的配置
async def main():
    crawl_configs = [
        {
            "domain": "Computer Science",
            "max_pages": 50,
            "language": "zh"
        },
    ]

    # 指定输出目录
    asyncio.run(main(output_dir="./custom_output", language="zh"))
```

#### 全局配置
```python
# config.py 中的 CrawlerConfig 类
config = CrawlerConfig(
    output_dir="./my_data",  # 自定义输出目录
    language="zh",
    max_pages=50
)
```

### 切换语言

修改 `language` 参数：

```python
{
    "domain": "Computer Science",
    "max_pages": 50,
    "language": "zh"  # 简体中文（默认）
}
```

或：

```python
{
    "domain": "Computer Science",
    "max_pages": 50,
    "language": "en"  # 英文
}
```


## 🤖 Agent说明

### 1. Plan Agent
- **输入**: 领域名称、目标页面数、语言
- **输出**: 搜索关键词策略
- **作用**: 制定爬取计划，覆盖领域各个方向

### 2. Page Analyzer (并行)
- **输入**: 单个页面内容
- **输出**: 
  - `main_topics`: 主要主题
  - `key_concepts`: 关键概念
  - `suggested_category_tags`: 建议标签
  - `analysis_summary`: 内容摘要（指定语言）

### 3. Clustering Agent
- **输入**: 所有页面的分析结果
- **输出**: 自动生成的分类体系（指定语言）
- **作用**: 基于内容相似度自动聚类

### 4. Save Tools
- `save_page_to_category`: 保存页面到分类文件夹
- `generate_markdown_index`: 生成Markdown索引
- `save_categorized_content`: 一键保存所有内容

## 📂 项目结构

```
wikipediag/
├── config.py               # 全局配置（语言、输出目录等）
├── main.py                 # 主程序入口
├── prompts.py              # Agent提示词
├── tools.py                # 工具函数（爬取、保存、索引生成）
├── parallel_workflow.py    # 并行工作流示例
├── examples.py             # 输出目录使用示例
├── test_simple.py          # 环境测试
├── requirements.txt        # 依赖
├── .env.example           # 环境变量模板
└── README.md              # 本文档
```

## ⚙️ 配置说明

### 环境变量 (.env)

```env
DEFAULT_LLM_API_KEY=your_api_key_here
DEFAULT_LLM_BASE_URL=https://api.openai.com/v1
DEFAULT_LLM_MODEL_NAME=gpt-4o-mini
```

### 全局配置 (config.py)

```python
CrawlerConfig(
    language="zh",              # 默认语言：zh=中文, en=英文
    output_dir="output",        # 输出目录（可自定义）
    save_content=True,          # 是否保存内容
    create_category_folders=True,  # 是否创建分类文件夹
    generate_markdown_index=True,  # 是否生成Markdown索引
    max_pages=50,               # 默认爬取页面数
)
```

**输出目录说明：**
- `output_dir`: 指定所有输出文件的根目录
- 默认值为 `"output"`，会创建在当前工作目录
- 可以指定绝对路径或相对路径
- 程序会自动创建目录结构

### 多语言支持

`config.py` 中的 `TRANSLATIONS` 字典定义了所有可翻译文本：

```python
TRANSLATIONS = {
    "zh": {
        "title": "标题",
        "summary": "摘要",
        "category": "分类",
        # ...
    },
    "en": {
        "title": "Title",
        "summary": "Summary",
        "category": "Category",
        # ...
    }
}
```

```
1. Plan Agent制定爬取计划
         ↓
2. 爬取N个领域相关页面
         ↓
3. 并行分析每个页面的内容
   (提取主题、概念、标签)
         ↓
4. Clustering Agent自动归纳分类
         ↓
5. 保存到本地分类文件夹
   output/content/{domain}/{category}/{title}.md
         ↓
6. 生成Markdown索引
   output/index/{domain}_index.md
```


## License

MIT
