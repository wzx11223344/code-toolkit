---
name: code-toolkit-zx
displayName: 开发编程工具箱
version: 1.0.1
summary: 10个开发工具：代码质量分析/SQL格式化/正则测试/API文档/圈复杂度/依赖检查/JSON格式化/Base64/UUID/Cron验证
tags: [development, code, sql, api]
license: MIT
---

# 开发编程工具箱 (code-toolkit)

## 简介

code-toolkit 是一套包含10个开发辅助工具的 Python 技能包，覆盖代码质量分析、SQL格式化、正则测试、API文档生成、JSON处理等日常开发场景。所有功能仅使用Python标准库实现，无需安装额外依赖。

## 功能列表

| # | 函数名 | 功能描述 |
|---|--------|----------|
| 1 | `analyze_code_quality` | 代码质量分析（复杂度/行数/注释率） |
| 2 | `format_sql` | SQL格式化 |
| 3 | `test_regex` | 正则表达式测试 |
| 4 | `generate_api_documentation` | API文档生成（Markdown/HTML/JSON） |
| 5 | `code_complexity_analyzer` | 圈复杂度分析（AST） |
| 6 | `dependency_checker` | 依赖检查（requirements.txt分析） |
| 7 | `json_formatter` | JSON格式化/压缩 |
| 8 | `base64_encoder_decoder` | Base64编解码 |
| 9 | `uuid_generator` | UUID生成器（v1/v3/v4/v5） |
| 10 | `cron_validator` | Cron表达式验证与解析 |

## 安装

无需安装额外依赖，仅使用Python标准库。

## 使用示例

```python
from main import code_complexity_analyzer, uuid_generator, cron_validator

# 圈复杂度分析
code = "def foo():\n    if True:\n        for i in range(10):\n            pass"
result = code_complexity_analyzer(code)
print(f"复杂度: {result['complexity']} ({result['level']})")

# UUID生成
uuids = uuid_generator(version=4, count=5)
print(uuids["uuids"])

# Cron验证
cron_result = cron_validator("0 2 * * *")
print(f"有效: {cron_result['valid']}, 描述: {cron_result['description']}")
```

## 依赖

无外部依赖（仅使用Python标准库）

## License

MIT
