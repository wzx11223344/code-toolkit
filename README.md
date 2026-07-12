# code-toolkit

开发编程工具箱 - 10个高级算法驱动的开发者工具集

## 功能概览

| # | 函数名 | 算法原理 | 复杂度 |
|---|--------|----------|--------|
| 1 | `code_complexity_analyzer` | AST遍历 + McCabe圈复杂度计算 | O(n)，n=AST节点数 |
| 2 | `dependency_graph_builder` | import解析 + Kahn拓扑排序 + DFS三色环检测 | O(V+E) |
| 3 | `code_smell_detector` | AST分析 + 10类异味检测规则 | O(n) |
| 4 | `sql_formatter_and_validator` | 词法分析器 + 语法检查 + 美化格式化 | O(n) |
| 5 | `regex_engine_tester` | 批量测试 + 分组捕获 + 性能计时 + 边界用例生成 | O(n*m) |
| 6 | `api_doc_generator` | AST函数签名解析 + 文档字符串解析 + Markdown/HTML生成 | O(n) |
| 7 | `json_schema_inferrer` | 递归类型推断 + 多样本Schema合并 | O(n*m) |
| 8 | `base64_codec_pipeline` | Base64编解码 + URL安全变体 + 分块传输 + 哈希 | O(n) |
| 9 | `uuid_generator_with_strategy` | UUID v1(时间戳)/v3(MD5)/v4(随机)/v5(SHA1) | O(n) |
| 10 | `cron_expression_parser` | 5字段解析 + 下次执行时间计算 + 语法验证 | O(60*5)最坏 |

## 算法详解

### 1. 代码圈复杂度分析 (`code_complexity_analyzer`)
- **AST解析**: 使用 `ast` 模块将源代码解析为抽象语法树
- **McCabe复杂度**: 圈复杂度 = 分支节点数 + 1
- **检测节点**: `If`, `For`, `While`, `ExceptHandler`, `BoolOp`(and/or), `IfExp`(三元), `comprehension`(列表推导), `Assert`
- **复杂度等级**: 1-5简单, 6-10适中, 11-20复杂, 21-50高风险, 50+不可维护
- **复杂度**: O(n)，n=AST节点数

### 2. 依赖图构建器 (`dependency_graph_builder`)
- **import解析**: 遍历AST提取 `Import` 和 `ImportFrom` 节点
- **Kahn拓扑排序**: 
  1. 计算每个节点的入度
  2. 入度为0的节点入队
  3. 依次出队，将其邻接节点入度-1
  4. 若入度为0则入队
  5. 若排序后节点数 < 总节点数，存在环
- **DFS三色标记环检测**: 白(未访问)→灰(访问中)→黑(已完成)，遇到灰节点即存在环
- **复杂度**: O(V+E)

### 3. 代码异味检测器 (`code_smell_detector`)
- **10类异味检测**:
  1. **长函数**: 函数行数 > 50
  2. **深嵌套**: 嵌套层级 > 4
  3. **重复代码**: AST节点序列相似度 > 80%
  4. **过长参数列表**: 参数数 > 5
  5. **魔法数字**: 代码中出现非0/1的硬编码数字
  6. **未使用变量**: 赋值后从未引用
  7. **复杂条件**: 单个if条件中布尔运算 > 3个
  8. **空except**: `except: pass` 或 `except Exception: pass`
  9. **全局变量**: 使用 `global` 关键字
  10. **缺少文档字符串**: 函数/类无docstring
- **复杂度**: O(n)

### 4. SQL格式化与验证器 (`sql_formatter_and_validator`)
- **词法分析器**: 将SQL拆分为token（关键字/标识符/字面量/操作符/括号/分号）
- **语法检查**: 
  - 括号匹配验证
  - SELECT/FROM/WHERE等关键字顺序验证
  - 语句完整性检查
- **格式化规则**:
  - 关键字大写
  - SELECT字段每行一个
  - FROM/WHERE/GROUP BY/ORDER BY换行缩进
  - 子查询增加缩进层级
- **复杂度**: O(n)

### 5. 正则引擎测试器 (`regex_engine_tester`)
- **批量测试**: 对多个测试字符串执行同一正则
- **分组捕获**: 展示每个匹配的分组内容
- **性能计时**: 使用 `time.perf_counter()` 精确计时
- **边界用例生成**: 自动生成空字符串、特殊字符、超长字符串等边界用例
- **复杂度**: O(n*m)，n=测试字符串数，m=正则复杂度

### 6. API文档生成器 (`api_doc_generator`)
- **AST解析**: 遍历AST提取函数定义节点
- **签名解析**: 提取函数名、参数列表、类型注解、默认值
- **文档字符串解析**: 解析Google风格docstring（Args/Returns/Raises/Example）
- **格式输出**: Markdown或HTML格式文档
- **复杂度**: O(n)

### 7. JSON Schema推断器 (`json_schema_inferrer`)
- **递归类型推断**: 
  - 基本类型: string/number/integer/boolean/null
  - 对象: 递归推断每个属性
  - 数组: 推断元素类型
- **多样本合并**: 
  - 类型合并: 同名字段类型不一致 → 取并集
  - 枚举值收集: 收集所有出现过的值
  - 必填字段: 在所有样本中都出现的字段
- **复杂度**: O(n*m)，n=样本数，m=JSON深度

### 8. Base64编解码管线 (`base64_codec_pipeline`)
- **支持操作**:
  - `encode`: 标准Base64编码
  - `decode`: 标准Base64解码
  - `urlsafe_encode`: URL安全变体(+→-, /→_)
  - `urlsafe_decode`: URL安全变体解码
  - `chunk_encode`: 分块传输编码（每76字符加换行）
  - `chunk_decode`: 分块传输解码
  - `hex_encode` / `hex_decode`: 十六进制编解码
  - `md5_hash` / `sha256_hash`: 哈希计算
- **复杂度**: O(n)

### 9. UUID生成器 (`uuid_generator_with_strategy`)
- **UUID v1**: 基于时间戳 + MAC地址（使用uuid.getnode()）
- **UUID v3**: 基于命名空间 + 名称的MD5哈希
- **UUID v4**: 基于随机数
- **UUID v5**: 基于命名空间 + 名称的SHA1哈希
- **批量生成**: 支持一次生成多个UUID，支持名称模板
- **复杂度**: O(n)

### 10. Cron表达式解析器 (`cron_expression_parser`)
- **5字段解析**: 分钟 小时 日期 月份 星期
- **字段类型**: 
  - `*`: 任意值
  - `n`: 固定值
  - `a-b`: 范围
  - `*/n`: 步长
  - `a,b,c`: 列表
- **下次执行时间计算**: 从当前时间开始，逐分钟递增，找到第一个匹配的时间点
- **语法验证**: 检查字段数、值范围、语法合法性
- **人类可读描述**: 将cron表达式转换为中文描述
- **复杂度**: 最坏O(60*5)，通常O(1)

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

## License

MIT
