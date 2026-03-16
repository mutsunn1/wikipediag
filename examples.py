"""
输出目录使用示例
"""

import asyncio
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import main, quick_demo, custom_crawl


async def run_examples():
    """运行各种输出目录配置示例"""

    print("=" * 70)
    print("📁 输出目录配置示例")
    print("=" * 70)

    # 示例1：默认输出目录
    print("\n1️⃣ 示例1：默认输出目录 (output/)")
    print("   命令: python main.py")
    print("   输出: output/content/Computer Science/")

    # 示例2：自定义输出目录
    print("\n2️⃣ 示例2：自定义输出目录 (./my_data/)")
    print("   命令: python main.py --output ./my_data")
    print("   输出: my_data/content/Computer Science/")

    # 示例3：绝对路径
    print("\n3️⃣ 示例3：绝对路径")
    print("   命令: python main.py --output /tmp/wikipedia_data")
    print("   输出: /tmp/wikipedia_data/content/Computer Science/")

    # 示例4：演示模式 + 自定义目录
    print("\n4️⃣ 示例4：演示模式 + 自定义目录")
    print("   命令: python main.py --demo --output ./demo_output")
    print("   输出: demo_output/content/Computer Science/")

    # 示例5：自定义爬取 + 自定义目录
    print("\n5️⃣ 示例5：自定义爬取 + 自定义目录")
    print("   命令: python main.py --custom \"Physics\" 30 zh --output ./physics_data")
    print("   输出: physics_data/content/Physics/")

    print("\n" + "=" * 70)
    print("📋 实际运行示例（按需取消注释）")
    print("=" * 70)

    # 取消注释以下代码来实际运行示例

    # 示例1：默认输出目录
    # print("\n🚀 运行示例1：默认输出目录")
    # await main(output_dir="output", language="zh")

    # 示例2：自定义输出目录
    # print("\n🚀 运行示例2：自定义输出目录")
    # await main(output_dir="./my_data", language="zh")

    # 示例3：演示模式
    # print("\n🚀 运行示例3：演示模式 + 自定义目录")
    # await quick_demo(output_dir="./demo_output")

    # 示例4：自定义爬取
    # print("\n🚀 运行示例4：自定义爬取 + 自定义目录")
    # await custom_crawl(
    #     domain="Physics",
    #     max_pages=10,
    #     language="zh",
    #     output_dir="./physics_data"
    # )


def show_folder_structure(output_dir: str = "output"):
    """显示输出文件夹结构"""
    print(f"\n📁 输出文件夹结构: {output_dir}/")
    print("""
    {output_dir}/
    ├── content/                          # 内容文件夹
    │   └── {domain}/                     # 领域文件夹
    │       ├── {category1}/              # 分类文件夹
    │       │   ├── {page1}.md
    │       │   ├── {page2}.md
    │       │   └── ...
    │       ├── {category2}/
    │       └── ...
    │
    ├── index/                            # 索引文件夹
    │   └── {domain}_index.md             # Markdown索引文件
    │
    └── {domain}_data.json                # 原始JSON数据
    """.format(
        output_dir=output_dir,
        domain="Computer Science",
        category1="数据结构",
        category2="算法",
        page1="Array data structure",
        page2="Linked list"
    ))


if __name__ == "__main__":
    # 显示示例说明
    asyncio.run(run_examples())

    # 显示文件夹结构示例
    print("\n" + "=" * 70)
    print("📂 文件夹结构示例")
    print("=" * 70)

    show_folder_structure("output")
    show_folder_structure("./my_data")
    show_folder_structure("./demo_output")

    print("\n" + "=" * 70)
    print("💡 提示：")
    print("   1. 输出目录可以是相对路径或绝对路径")
    print("   2. 目录不存在时会自动创建")
    print("   3. 确保有写入权限")
    print("=" * 70)