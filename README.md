# code-toolkit

开发编程工具箱 - 10个开发辅助工具集（仅标准库）

## 功能概览

- **代码质量分析** - 行数/注释率/问题检测
- **SQL格式化** - 自动大写关键字、换行缩进
- **正则表达式测试** - 匹配结果、分组、替换演示
- **API文档生成** - Markdown/HTML/JSON三种格式
- **圈复杂度分析** - AST解析，函数级复杂度
- **依赖检查** - requirements.txt分析
- **JSON格式化** - 格式化/压缩，验证
- **Base64编解码** - UTF-8支持
- **UUID生成器** - v1/v3/v4/v5
- **Cron验证** - 5字段解析与描述

## 安装

无需安装额外依赖，仅使用Python标准库。

## 快速开始

```python
from main import test_regex

result = test_regex(r"\d+", "abc123def456")
print(f"匹配数: {result['match_count']}")
for m in result["matches"]:
    print(f"  匹配: {m['match']} 位置: {m['start']}-{m['end']}")
```

## License

MIT
