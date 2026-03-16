"""
简单测试脚本 - 验证环境配置
"""

import asyncio
import os

from dotenv import load_dotenv

load_dotenv()


def check_env():
    """检查环境变量"""
    print("=" * 60)
    print("🔍 环境检查")
    print("=" * 60)
    
    api_key = os.getenv("DEFAULT_LLM_API_KEY")
    base_url = os.getenv("DEFAULT_LLM_BASE_URL")
    model = os.getenv("DEFAULT_LLM_MODEL_NAME")
    
    print(f"API Key: {'✅ 已设置' if api_key and api_key != 'your_api_key_here' else '❌ 未设置'}")
    print(f"Base URL: {base_url or '❌ 未设置'}")
    print(f"Model: {model or '❌ 未设置'}")
    
    if not api_key or api_key == 'your_api_key_here':
        print("\n⚠️ 请先配置 .env 文件中的 API 密钥！")
        print("\n步骤:")
        print("  1. cp .env.example .env")
        print("  2. 编辑 .env 填入你的API密钥")
        return False
    
    return True


async def test_wikipedia_api():
    """测试Wikipedia API"""
    print("\n" + "=" * 60)
    print("🔍 Wikipedia API 测试")
    print("=" * 60)
    
    try:
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            params = {
                "action": "query",
                "list": "search",
                "srsearch": "Computer Science",
                "srlimit": 3,
                "format": "json"
            }
            
            async with session.get(
                "https://en.wikipedia.org/w/api.php",
                params=params,
                timeout=10
            ) as resp:
                data = await resp.json()
                results = data.get("query", {}).get("search", [])
                
                print(f"✅ Wikipedia API 连接成功！")
                print(f"   搜索结果: {len(results)} 条")
                for r in results:
                    print(f"   - {r['title']}")
                return True
                
    except Exception as e:
        print(f"❌ Wikipedia API 测试失败: {e}")
        return False


def test_oxygent_import():
    """测试Oxygent导入"""
    print("\n" + "=" * 60)
    print("🔍 Oxygent 导入测试")
    print("=" * 60)
    
    try:
        from oxygent import MAS, oxy, Config
        print("✅ Oxygent 导入成功！")
        return True
    except ImportError as e:
        print(f"❌ Oxygent 导入失败: {e}")
        print("\n请运行: pip install oxygent")
        return False


def print_next_steps():
    """打印下一步操作"""
    print("\n" + "=" * 60)
    print("📝 下一步操作")
    print("=" * 60)
    print("\n1. 快速演示 (10个页面):")
    print("   python main.py --demo")
    print("\n2. 完整运行 (50个CS页面 + 自动分类):")
    print("   python main.py")
    print("\n3. 并行工作流模式:")
    print("   python parallel_workflow.py")
    print("\n4. 查看帮助:")
    print("   cat README.md")


async def main():
    """主测试函数"""
    print("\n" + "🚀 " * 20)
    print("\n   Oxygent Wikipedia Crawler - 自动分类版")
    print("\n" + "🚀 " * 20 + "\n")
    
    # 检查环境变量
    env_ok = check_env()
    
    # 测试Oxygent导入
    oxygent_ok = test_oxygent_import()
    
    # 测试Wikipedia API
    wiki_ok = await test_wikipedia_api()
    
    # 总结
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)
    
    if env_ok and oxygent_ok and wiki_ok:
        print("✅ 所有检查通过！系统可以正常运行。")
        print_next_steps()
        return 0
    else:
        print("❌ 部分检查未通过，请修复上述问题。")
        if not env_ok:
            print("\n⚠️ 请配置 .env 文件")
        if not oxygent_ok:
            print("\n⚠️ 请安装依赖: pip install -r requirements.txt")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
