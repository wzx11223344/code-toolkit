---
name: code-toolkit-zx
displayName: 开发编程工具箱
version: 2.0.0
summary: 10个高级算法开发工具：AST圈复杂度/Kahn拓扑排序+DFS环检测/10类代码异味/SQL词法分析格式化/正则引擎测试/API文档生成/JSON Schema推断/Base64管线/UUID v1-v5/Cron表达式解析
tags: [development, code, ast, mccabe, topological-sort, sql, cron, uuid]
license: MIT
---

# 开发编程工具箱 (code-toolkit)

## 简介

code-toolkit 是一套包含10个高级算法驱动的开发者工具的 Python 技能包。所有功能仅使用Python标准库实现，无需安装任何外部依赖。涵盖代码圈复杂度分析、依赖图构建、代码异味检测、SQL格式化、正则测试、API文档生成、JSON Schema推断、Base64编解码、UUID生成、Cron表达式解析等场景。

## 功能列表

| # | 函数名 | 算法原理 | 复杂度 |
|---|--------|----------|--------|
| 1 | `code_complexity_analyzer` | AST遍历 + McCabe圈复杂度 | O(n) |
| 2 | `dependency_graph_builder` | import解析 + Kahn拓扑排序 + DFS三色环检测 | O(V+E) |
| 3 | `code_smell_detector` | AST分析 + 10类异味检测规则 | O(n) |
| 4 | `sql_formatter_and_validator` | 词法分析器 + 语法检查 + 美化格式化 | O(n) |
| 5 | `regex_engine_tester` | 批量测试 + 分组捕获 + 性能计时 + 边界用例 | O(n*m) |
| 6 | `api_doc_generator` | AST函数签名解析 + 文档字符串解析 + MD/HTML生成 | O(n) |
| 7 | `json_schema_inferrer` | 递归类型推断 + 多样本Schema合并 | O(n*m) |
| 8 | `base64_codec_pipeline` | Base64编解码 + URL安全变体 + 分块传输 + 哈希 | O(n) |
| 9 | `uuid_generator_with_strategy` | UUID v1(时间戳)/v3(MD5)/v4(随机)/v5(SHA1) | O(n) |
| 10 | `cron_expression_parser` | 5字段解析 + 下次执行时间计算 + 语法验证 | O(60*5) |

## 安装

无需安装额外依赖，仅使用Python标准库（ast, re, json, uuid, time, base64, hashlib, calendar, collections, datetime等）。

## 使用示例

```python
from main import code_complexity_analyzer, dependency_graph_builder, cron_expression_parser

# 圈复杂度分析
code = open("module.py").read()
result = code_complexity_analyzer(code)
for func in result["functions"]:
    print(f"{func['name']}: 复杂度={func['complexity']} ({func['level']})")

# 依赖图 + 循环检测
deps = dependency_graph_builder(code)
print(f"循环依赖: {deps['cycles']}")

# Cron表达式解析
cron = cron_expression_parser("0 9 * * 1-5")
print(f"下次执行: {cron['next_run']}, 描述: {cron['description']}")
```

## 依赖

无外部依赖（仅使用Python标准库）

## License

MIT
