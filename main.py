"""
code-toolkit — 开发编程工具箱

包含10个高级算法驱动的开发辅助工具，全部使用Python标准库实现（ast, re, json, uuid,
datetime, collections, time, hashlib等），无需安装任何外部依赖。

功能列表:
  1. code_complexity_analyzer      — AST解析的McCabe圈复杂度分析
  2. dependency_graph_builder      — 模块依赖图构建+循环依赖检测（DFS+拓扑排序）
  3. code_smell_detector           — 10类代码异味检测
  4. sql_formatter_and_validator   — SQL词法分析+语法验证+美化格式化
  5. regex_engine_tester           — 正则引擎批量测试+分组捕获+性能计时
  6. api_doc_generator             — 函数签名解析→Markdown/HTML API文档生成
  7. json_schema_inferrer          — 多JSON样本Schema推断与合并
  8. base64_codec_pipeline         — Base64编解码管线（标准/URL安全/分块）
  9. uuid_generator_with_strategy   — UUID v1/v3/v4/v5四种策略生成
 10. cron_expression_parser        — Cron表达式解析+下次执行时间计算

Author: github.com/wzx11223344
License: MIT
"""

import ast
import re
import json
import uuid
import time
import base64
import hashlib
import calendar
import tokenize
import io
from collections import defaultdict, deque, OrderedDict
from datetime import datetime, timedelta
from io import BytesIO


# ======================================================================
# 1. code_complexity_analyzer — 基于AST的McCabe圈复杂度分析
# ======================================================================

class _ComplexityVisitor(ast.NodeVisitor):
    """AST遍历器：统计每个函数的McCabe圈复杂度。

    McCabe复杂度 = 决策点数 + 1
    决策点包括: if/elif/for/while/and/or/except/with/comprehension/ternary
    """

    def __init__(self):
        self.complexity = 1  # 基础复杂度为1
        self.decisions = []  # 记录每个决策点详情

    def _add_decision(self, node_type, lineno):
        self.complexity += 1
        self.decisions.append({"type": node_type, "line": lineno})

    def visit_If(self, node):
        self._add_decision("if", node.lineno)
        self.generic_visit(node)

    def visit_For(self, node):
        self._add_decision("for", node.lineno)
        self.generic_visit(node)

    def visit_While(self, node):
        self._add_decision("while", node.lineno)
        self.generic_visit(node)

    def visit_ExceptHandler(self, node):
        self._add_decision("except", node.lineno)
        self.generic_visit(node)

    def visit_BoolOp(self, node):
        # and/or 每个额外操作数增加一个决策点
        self.complexity += len(node.values) - 1
        self.decisions.append({
            "type": f"boolop({type(node.op).__name__})",
            "line": node.lineno,
            "operands": len(node.values),
        })
        self.generic_visit(node)

    def visit_IfExp(self, node):
        # 三元表达式 a if cond else b
        self._add_decision("ternary", node.lineno)
        self.generic_visit(node)

    def visit_comprehension(self, node):
        # 列表/集合/字典推导式中的循环
        self._add_decision("comprehension", getattr(node, "lineno", 0))
        for cond in node.ifs:
            self._add_decision("comprehension_if", getattr(node, "lineno", 0))
        self.generic_visit(node)

    def visit_Assert(self, node):
        self._add_decision("assert", node.lineno)
        self.generic_visit(node)


def code_complexity_analyzer(source_code):
    """基于AST的McCabe圈复杂度分析器。

    解析Python源代码的AST（抽象语法树），遍历每个函数定义，
    统计决策点（if/elif/for/while/and/or/except/ternary等），
    计算McCabe圈复杂度 = 决策点数 + 1。

    算法步骤:
      1. 使用 ast.parse() 将源代码解析为AST
      2. 遍历AST，找到所有 FunctionDef/AsyncFunctionDef 节点
      3. 对每个函数，使用 _ComplexityVisitor 统计决策点
      4. 计算复杂度等级：
         - 1-10: 简单（低风险）
         - 11-20: 适中（中等风险）
         - 21-50: 复杂（高风险）
         - 50+: 极复杂（需重构）

    Args:
        source_code (str): Python源代码字符串

    Returns:
        dict: {
            "total_functions": int,
            "total_complexity": int,
            "average_complexity": float,
            "max_complexity": int,
            "functions": [
                {
                    "name": str,
                    "line": int,
                    "complexity": int,
                    "level": str,
                    "decisions": [{"type": str, "line": int}, ...]
                }, ...
            ]
        }
    """
    try:
        tree = ast.parse(source_code)
    except SyntaxError as e:
        return {"error": f"SyntaxError: {e}"}

    functions = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            visitor = _ComplexityVisitor()
            visitor.visit(node)

            complexity = visitor.complexity
            if complexity <= 10:
                level = "简单"
            elif complexity <= 20:
                level = "适中"
            elif complexity <= 50:
                level = "复杂"
            else:
                level = "极复杂"

            functions.append({
                "name": node.name,
                "line": node.lineno,
                "complexity": complexity,
                "level": level,
                "decision_count": len(visitor.decisions),
                "decisions": visitor.decisions,
            })

    total = sum(f["complexity"] for f in functions)
    avg = total / len(functions) if functions else 0
    max_c = max(f["complexity"] for f in functions) if functions else 0

    return {
        "total_functions": len(functions),
        "total_complexity": total,
        "average_complexity": round(avg, 2),
        "max_complexity": max_c,
        "functions": functions,
    }


# ======================================================================
# 2. dependency_graph_builder — 模块依赖图构建+循环依赖检测
# ======================================================================

class _DependencyGraph:
    """有向依赖图，支持拓扑排序和环检测。"""

    def __init__(self):
        self.graph = defaultdict(set)  # {module: set(dependencies)}
        self.reverse = defaultdict(set)  # 逆邻接表

    def add_edge(self, src, dst):
        if src != dst:  # 忽略自环
            self.graph[src].add(dst)
            self.reverse[dst].add(src)

    def topological_sort(self):
        """Kahn算法拓扑排序。

        算法: 每次找入度为0的节点，加入结果集并删除其出边。
        若结果集大小 != 节点数，说明存在环。

        Returns:
            (list, bool): (排序结果列表, 是否有环)
        """
        in_degree = {}
        all_nodes = set(self.graph.keys()) | {d for deps in self.graph.values() for d in deps}
        for node in all_nodes:
            in_degree[node] = 0
        for src, deps in self.graph.items():
            for dst in deps:
                in_degree[dst] = in_degree.get(dst, 0) + 1

        queue = deque([n for n, d in in_degree.items() if d == 0])
        result = []

        while queue:
            node = queue.popleft()
            result.append(node)
            for neighbor in self.graph.get(node, set()):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        has_cycle = len(result) != len(all_nodes)
        return result, has_cycle

    def detect_cycles_dfs(self):
        """DFS环检测算法（三色标记法）。

        算法: 使用白色/灰色/黑色三色标记节点：
          - 白色: 未访问
          - 灰色: 正在访问（在当前DFS路径中）
          - 黑色: 已完成访问
        遇到灰色节点说明发现环。

        Returns:
            list: 检测到的所有环路径
        """
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {n: WHITE for n in (set(self.graph.keys()) | {d for deps in self.graph.values() for d in deps})}
        cycles = []

        def dfs(node, path):
            color[node] = GRAY
            path.append(node)
            for neighbor in sorted(self.graph.get(node, set())):
                if color.get(neighbor, WHITE) == GRAY:
                    # 找到环
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(cycle)
                elif color.get(neighbor, WHITE) == WHITE:
                    dfs(neighbor, path)
            path.pop()
            color[node] = BLACK

        for node in sorted(color.keys()):
            if color[node] == WHITE:
                dfs(node, [])

        return cycles


def dependency_graph_builder(source_code, module_name=None):
    """依赖图构建器：解析import语句，构建模块依赖关系图，检测循环依赖。

    算法步骤:
      1. 使用 ast.parse() 解析源代码
      2. 遍历AST，提取所有 import/from...import 语句
      3. 构建邻接表表示的依赖图
      4. 使用Kahn算法进行拓扑排序，检测是否存在环
      5. 使用DFS三色标记法找到所有环的路径

    Args:
        source_code (str): Python源代码，可以是单个或多个文件用 # ---file--- 分隔
        module_name (str): 当前模块名（默认从代码中推断）

    Returns:
        dict: {
            "module": str,
            "dependencies": {module: [deps]},
            "topological_order": list,
            "has_cycle": bool,
            "cycles": [[node, ...], ...],
            "import_count": int,
            "unique_modules": int
        }
    """
    try:
        tree = ast.parse(source_code)
    except SyntaxError as e:
        return {"error": f"SyntaxError: {e}"}

    graph = _DependencyGraph()
    imports = []

    # 推断当前模块名
    current_module = module_name or "__main__"

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                graph.add_edge(current_module, alias.name)
                imports.append({"type": "import", "module": alias.name, "line": node.lineno})
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                graph.add_edge(current_module, node.module)
                imported_names = [a.name for a in node.names]
                imports.append({
                    "type": "from",
                    "module": node.module,
                    "names": imported_names,
                    "line": node.lineno,
                })

    topo_order, has_cycle = graph.topological_sort()
    cycles = graph.detect_cycles_dfs()

    # 构建邻接表字典
    dep_dict = {}
    for src, deps in graph.graph.items():
        dep_dict[src] = sorted(deps)

    return {
        "module": current_module,
        "dependencies": dep_dict,
        "topological_order": topo_order,
        "has_cycle": has_cycle,
        "cycles": cycles,
        "import_count": len(imports),
        "imports_detail": imports,
        "unique_modules": len(dep_dict),
    }


# ======================================================================
# 3. code_smell_detector — 10类代码异味检测
# ======================================================================

class _CodeSmellVisitor(ast.NodeVisitor):
    """AST遍历器：检测10类代码异味。"""

    LONG_FUNCTION_THRESHOLD = 50
    DEEP_NESTING_THRESHOLD = 4
    LONG_PARAM_THRESHOLD = 5
    MAGIC_NUMBER_THRESHOLD = 10  # 不计算0, 1, -1

    def __init__(self):
        self.smells = []

    def _add_smell(self, category, description, line, severity="warning"):
        self.smells.append({
            "category": category,
            "description": description,
            "line": line,
            "severity": severity,
        })

    def visit_FunctionDef(self, node):
        # 检测长函数
        end_lineno = getattr(node, "end_lineno", node.lineno + 1)
        func_length = end_lineno - node.lineno
        if func_length > self.LONG_FUNCTION_THRESHOLD:
            self._add_smell(
                "长函数",
                f"函数 '{node.name}' 有 {func_length} 行，超过阈值 {self.LONG_FUNCTION_THRESHOLD}",
                node.lineno,
                "warning",
            )

        # 检测过长参数列表
        args = node.args
        all_args = (args.args + args.posonlyargs + args.kwonlyargs)
        if args.vararg:
            all_args = list(all_args)
        if len(all_args) > self.LONG_PARAM_THRESHOLD:
            self._add_smell(
                "过长参数列表",
                f"函数 '{node.name}' 有 {len(all_args)} 个参数，超过阈值 {self.LONG_PARAM_THRESHOLD}",
                node.lineno,
            )

        # 检测缺少文档字符串
        if not (node.body and isinstance(node.body[0], ast.Expr) and
                isinstance(node.body[0].value, (ast.Str, ast.Constant))):
            self._add_smell(
                "缺少文档字符串",
                f"函数 '{node.name}' 缺少docstring",
                node.lineno,
                "info",
            )

        # 检测深嵌套
        self._check_nesting(node, 0, node.name)
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def _check_nesting(self, node, depth, func_name):
        """递归检查嵌套深度。"""
        control_types = (ast.If, ast.For, ast.While, ast.With, ast.Try,
                         ast.ExceptHandler)
        if isinstance(node, control_types):
            depth += 1
            if depth > self.DEEP_NESTING_THRESHOLD:
                self._add_smell(
                    "深嵌套",
                    f"函数 '{func_name}' 中有 {depth} 层嵌套，超过阈值 {self.DEEP_NESTING_THRESHOLD}",
                    getattr(node, "lineno", 0),
                )
        for child in ast.iter_child_nodes(node):
            self._check_nesting(child, depth, func_name)

    def visit_ExceptHandler(self, node):
        # 检测空except
        if node.body and len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
            self._add_smell(
                "空except",
                "空的except块，直接pass会吞掉异常",
                node.lineno,
                "error",
            )
        self.generic_visit(node)

    def visit_Assign(self, node):
        # 检测全局变量（模块级别赋值）
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id.isupper():
                # 常量不算全局变量异味
                pass
        self.generic_visit(node)

    def visit_Compare(self, node):
        # 检测魔法数字
        for comparator in [node.left] + node.comparators:
            if isinstance(comparator, ast.Constant) and isinstance(comparator.value, (int, float)):
                val = comparator.value
                if abs(val) > self.MAGIC_NUMBER_THRESHOLD:
                    self._add_smell(
                        "魔法数字",
                        f"硬编码数字 {val}，建议提取为命名常量",
                        getattr(node, "lineno", 0),
                        "info",
                    )
        self.generic_visit(node)


def code_smell_detector(source_code):
    """代码异味检测器，检测10类代码异味。

    检测的10类异味:
      1. 长函数（>50行）
      2. 深嵌套（>4层控制结构嵌套）
      3. 重复代码（基于Token序列相似度）
      4. 过长参数列表（>5个参数）
      5. 魔法数字（硬编码数字）
      6. 未使用变量（赋值后未引用）
      7. 复杂条件（BoolOp操作数过多）
      8. 空except块（吞异常）
      9. 全局变量（模块级别可变变量）
     10. 缺少文档字符串

    Args:
        source_code (str): Python源代码

    Returns:
        dict: {
            "total_smells": int,
            "by_category": {category: count},
            "by_severity": {severity: count},
            "smells": [{category, description, line, severity}, ...],
            "score": int (0-100, 越高越好)
        }
    """
    try:
        tree = ast.parse(source_code)
    except SyntaxError as e:
        return {"error": f"SyntaxError: {e}"}

    visitor = _CodeSmellVisitor()
    visitor.visit(tree)

    # 使用tokenize检测重复代码块
    duplicate_smells = _detect_duplicate_code(source_code)
    visitor.smells.extend(duplicate_smells)

    # 检测未使用变量
    unused_smells = _detect_unused_variables(tree)
    visitor.smells.extend(unused_smells)

    # 检测复杂条件表达式
    complex_cond_smells = _detect_complex_conditions(tree)
    visitor.smells.extend(complex_cond_smells)

    # 检测全局变量
    global_var_smells = _detect_global_variables(tree)
    visitor.smells.extend(global_var_smells)

    # 统计
    by_category = defaultdict(int)
    by_severity = defaultdict(int)
    for smell in visitor.smells:
        by_category[smell["category"]] += 1
        by_severity[smell["severity"]] += 1

    # 计算质量评分
    penalty = by_severity["error"] * 10 + by_severity["warning"] * 5 + by_severity["info"] * 1
    score = max(0, 100 - penalty)

    return {
        "total_smells": len(visitor.smells),
        "by_category": dict(by_category),
        "by_severity": dict(by_severity),
        "smells": visitor.smells,
        "score": score,
    }


def _detect_duplicate_code(source_code):
    """通过Token序列的滑动窗口检测重复代码块。"""
    smells = []
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source_code).readline))
    except tokenize.TokenError:
        return smells

    # 提取有意义的token
    meaningful = [(t.type, t.string) for t in tokens if t.type in (tokenize.NAME, tokenize.OP)]

    # 使用滑动窗口检测重复
    window_size = 15
    seen = {}
    for i in range(len(meaningful) - window_size):
        window = tuple(meaningful[i:i + window_size])
        window_hash = hash(window)
        if window_hash in seen:
            start_line = tokens[i].start[0]
            smells.append({
                "category": "重复代码",
                "description": f"检测到重复代码块（与第{seen[window_hash]}行开始相似）",
                "line": start_line,
                "severity": "warning",
            })
        else:
            seen[window_hash] = tokens[i].start[0]

    return smells


def _detect_unused_variables(tree):
    """检测赋值后从未被引用的变量。"""
    smells = []
    assigned = {}  # {var_name: line}
    used = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            if isinstance(node.ctx, ast.Store):
                assigned[node.id] = node.lineno
            elif isinstance(node.ctx, ast.Load):
                used.add(node.id)

    for var, line in assigned.items():
        if var not in used and not var.startswith("_"):
            smells.append({
                "category": "未使用变量",
                "description": f"变量 '{var}' 赋值后从未使用",
                "line": line,
                "severity": "warning",
            })

    return smells


def _detect_complex_conditions(tree):
    """检测过于复杂的条件表达式（BoolOp操作数>3）。"""
    smells = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp) and len(node.values) > 3:
            smells.append({
                "category": "复杂条件",
                "description": f"条件表达式有 {len(node.values)} 个操作数，建议拆分",
                "line": getattr(node, "lineno", 0),
                "severity": "warning",
            })
    return smells


def _detect_global_variables(tree):
    """检测模块级别的全局可变变量。"""
    smells = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and not target.id.isupper():
                    smells.append({
                        "category": "全局变量",
                        "description": f"模块级变量 '{target.id}'，建议封装为类属性或使用配置",
                        "line": node.lineno,
                        "severity": "info",
                    })
    return smells


# ======================================================================
# 4. sql_formatter_and_validator — SQL词法分析+语法验证+美化格式化
# ======================================================================

_SQL_KEYWORDS = {
    "SELECT", "FROM", "WHERE", "INSERT", "INTO", "VALUES", "UPDATE", "SET",
    "DELETE", "CREATE", "TABLE", "ALTER", "DROP", "INDEX", "VIEW", "JOIN",
    "INNER", "LEFT", "RIGHT", "OUTER", "FULL", "CROSS", "ON", "GROUP", "BY",
    "ORDER", "HAVING", "LIMIT", "OFFSET", "UNION", "ALL", "AS", "AND", "OR",
    "NOT", "IN", "EXISTS", "BETWEEN", "LIKE", "IS", "NULL", "DISTINCT",
    "CASE", "WHEN", "THEN", "ELSE", "END", "BEGIN", "COMMIT", "ROLLBACK",
    "PRIMARY", "KEY", "FOREIGN", "REFERENCES", "CONSTRAINT", "DEFAULT",
    "CHECK", "UNIQUE", "WITH", "RECURSIVE", "OVER", "PARTITION", "WINDOW",
    "INT", "INTEGER", "VARCHAR", "TEXT", "CHAR", "DATE", "DATETIME",
    "TIMESTAMP", "DECIMAL", "FLOAT", "DOUBLE", "BOOLEAN", "BLOB",
}

_SQL_FUNCTIONS = {
    "COUNT", "SUM", "AVG", "MIN", "MAX", "COALESCE", "CAST", "CONVERT",
    "SUBSTRING", "TRIM", "LENGTH", "REPLACE", "UPPER", "LOWER",
    "NOW", "CURRENT_DATE", "CURRENT_TIME", "CURRENT_TIMESTAMP",
    "EXTRACT", "DATE_PART", "CONCAT", "ROW_NUMBER", "RANK", "DENSE_RANK",
}


def _tokenize_sql(sql):
    """SQL词法分析器。

    将SQL字符串分割为token列表，每个token包含类型和值。

    Token类型:
      - KEYWORD: SQL关键字
      - FUNCTION: SQL函数名
      - IDENTIFIER: 标识符（表名/列名/别名）
      - STRING: 字符串字面量
      - NUMBER: 数字字面量
      - OPERATOR: 运算符
      - PUNCTUATION: 标点符号（括号/逗号/分号）
      - COMMENT: 注释
      - WHITESPACE: 空白
    """
    tokens = []
    i = 0
    n = len(sql)

    while i < n:
        c = sql[i]

        # 空白
        if c.isspace():
            j = i
            while j < n and sql[j].isspace():
                j += 1
            tokens.append(("WHITESPACE", sql[i:j]))
            i = j
            continue

        # 注释 -- ...
        if c == "-" and i + 1 < n and sql[i + 1] == "-":
            j = i
            while j < n and sql[j] != "\n":
                j += 1
            tokens.append(("COMMENT", sql[i:j]))
            i = j
            continue

        # 注释 /* ... */
        if c == "/" and i + 1 < n and sql[i + 1] == "*":
            j = i + 2
            while j < n - 1 and not (sql[j] == "*" and sql[j + 1] == "/"):
                j += 1
            j = min(j + 2, n)
            tokens.append(("COMMENT", sql[i:j]))
            i = j
            continue

        # 字符串字面量（单引号）
        if c == "'":
            j = i + 1
            while j < n:
                if sql[j] == "'":
                    if j + 1 < n and sql[j + 1] == "'":  # 转义
                        j += 2
                        continue
                    j += 1
                    break
                j += 1
            tokens.append(("STRING", sql[i:j]))
            i = j
            continue

        # 双引号标识符
        if c == '"':
            j = i + 1
            while j < n and sql[j] != '"':
                j += 1
            j = min(j + 1, n)
            tokens.append(("IDENTIFIER", sql[i:j]))
            i = j
            continue

        # 数字
        if c.isdigit() or (c == "." and i + 1 < n and sql[i + 1].isdigit()):
            j = i
            while j < n and (sql[j].isdigit() or sql[j] == "."):
                j += 1
            tokens.append(("NUMBER", sql[i:j]))
            i = j
            continue

        # 标识符/关键字
        if c.isalpha() or c == "_":
            j = i
            while j < n and (sql[j].isalnum() or sql[j] == "_"):
                j += 1
            word = sql[i:j]
            upper = word.upper()
            if upper in _SQL_KEYWORDS:
                tokens.append(("KEYWORD", upper))
            elif upper in _SQL_FUNCTIONS:
                tokens.append(("FUNCTION", upper))
            else:
                tokens.append(("IDENTIFIER", word))
            i = j
            continue

        # 多字符运算符
        if c in "!<>=" and i + 1 < n and sql[i + 1] == "=":
            tokens.append(("OPERATOR", sql[i:i + 2]))
            i += 2
            continue

        # 单字符
        if c in "(),;.":
            tokens.append(("PUNCTUATION", c))
        elif c in "<>=+-*/%":
            tokens.append(("OPERATOR", c))
        else:
            tokens.append(("UNKNOWN", c))
        i += 1

    return tokens


def _validate_sql_syntax(tokens):
    """基础SQL语法验证。"""
    errors = []
    meaningful = [(t, v) for t, v in tokens if t not in ("WHITESPACE", "COMMENT")]

    if not meaningful:
        return ["空SQL语句"]

    # 检查是否有起始关键字
    first_type, first_val = meaningful[0]
    valid_starts = {"SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "ALTER",
                     "DROP", "WITH", "BEGIN", "COMMIT", "ROLLBACK"}
    if first_type == "KEYWORD" and first_val not in valid_starts:
        errors.append(f"SQL以 '{first_val}' 开头，不是有效起始关键字")

    # 检查括号匹配
    paren_stack = []
    for token_type, token_val in meaningful:
        if token_type == "PUNCTUATION":
            if token_val == "(":
                paren_stack.append(token_val)
            elif token_val == ")":
                if not paren_stack:
                    errors.append("括号不匹配：多余的 ')'")
                else:
                    paren_stack.pop()
    if paren_stack:
        errors.append(f"括号不匹配：缺少 {len(paren_stack)} 个 ')'")

    # 检查SELECT是否有FROM（简单检查）
    if first_val == "SELECT":
        has_from = any(v == "FROM" for t, v in meaningful if t == "KEYWORD")
        if not has_from and not any(v == "VALUES" for t, v in meaningful):
            # 可能是 SELECT 1+1 这种无FROM查询
            pass

    # 检查分号结尾
    last_type, last_val = meaningful[-1]
    if last_val != ";":
        errors.append("SQL语句应以分号结尾")

    return errors


def sql_formatter_and_validator(sql):
    """SQL格式化与验证器。

    算法步骤:
      1. 词法分析：将SQL字符串分割为token列表
      2. 语法验证：检查括号匹配、关键字顺序、分号结尾
      3. 美化格式化：
         - 关键字大写
         - 主要子句（SELECT/FROM/WHERE等）换行
         - 子查询缩进
         - JOIN对齐
         - 逗号后加空格
         - 运算符两侧加空格

    Args:
        sql (str): SQL语句字符串

    Returns:
        dict: {
            "formatted": str,
            "valid": bool,
            "errors": [str],
            "warnings": [str],
            "tokens": [{"type": str, "value": str}, ...],
            "stats": {"token_count": int, "keyword_count": int}
        }
    """
    tokens = _tokenize_sql(sql)
    errors = _validate_sql_syntax(tokens)

    # 格式化
    formatted_lines = []
    current_line = ""
    indent_level = 0
    max_line_length = 80

    newline_keywords = {
        "SELECT", "FROM", "WHERE", "GROUP", "ORDER", "HAVING", "LIMIT",
        "INSERT", "INTO", "VALUES", "UPDATE", "SET", "DELETE", "CREATE",
        "TABLE", "ALTER", "DROP", "UNION", "WITH", "JOIN", "INNER",
        "LEFT", "RIGHT", "OUTER", "FULL", "CROSS",
    }

    for token_type, token_val in tokens:
        if token_type in ("WHITESPACE", "COMMENT"):
            continue

        # 关键字大写
        if token_type == "KEYWORD":
            token_val = token_val.upper()

        # 主要关键字换行
        if token_type == "KEYWORD" and token_val in newline_keywords and current_line.strip():
            formatted_lines.append("  " * indent_level + current_line.strip())
            current_line = ""
            # JOIN 前不需要增加缩进
            if token_val not in ("INNER", "LEFT", "RIGHT", "OUTER", "FULL", "CROSS", "JOIN"):
                pass

        # 括号处理
        if token_type == "PUNCTUATION" and token_val == "(":
            current_line += " ("
            formatted_lines.append("  " * indent_level + current_line.strip())
            current_line = ""
            indent_level += 1
            continue
        elif token_type == "PUNCTUATION" and token_val == ")":
            if current_line.strip():
                formatted_lines.append("  " * indent_level + current_line.strip())
                current_line = ""
            indent_level = max(0, indent_level - 1)
            current_line = ")"
            continue

        # 逗号后加空格
        if token_type == "PUNCTUATION" and token_val == ",":
            current_line += ","
            continue

        # 运算符两侧加空格
        if token_type == "OPERATOR":
            current_line += f" {token_val} "
            continue

        # 普通token
        if current_line and not current_line.endswith(" ") and not current_line.endswith("("):
            current_line += " "
        current_line += token_val

    # 最后一行
    if current_line.strip():
        formatted_lines.append("  " * indent_level + current_line.strip())

    formatted = "\n".join(formatted_lines)

    # 统计
    keyword_count = sum(1 for t, v in tokens if t == "KEYWORD")

    # 生成警告
    warnings = []
    if formatted.count("\n") > 0 and len(formatted.split("\n")[0]) > max_line_length:
        warnings.append("第一行超过建议长度")

    return {
        "formatted": formatted,
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "tokens": [{"type": t, "value": v} for t, v in tokens if t not in ("WHITESPACE", "COMMENT")],
        "stats": {
            "token_count": sum(1 for t, v in tokens if t not in ("WHITESPACE", "COMMENT")),
            "keyword_count": keyword_count,
        },
    }


# ======================================================================
# 5. regex_engine_tester — 正则引擎测试器
# ======================================================================

def regex_engine_tester(pattern, test_strings):
    """正则引擎测试器：支持批量测试、分组捕获展示、性能计时、边界用例生成。

    算法步骤:
      1. 编译正则表达式，检查语法合法性
      2. 对每个测试字符串执行匹配
      3. 提取分组捕获结果
      4. 精确计时每个匹配操作
      5. 自动生成边界用例（空字符串/特殊字符/超长字符串）
      6. 汇总匹配率/性能统计

    Args:
        pattern (str): 正则表达式字符串
        test_strings (list): 待测试字符串列表

    Returns:
        dict: {
            "pattern": str,
            "valid": bool,
            "compile_error": str or None,
            "results": [
                {
                    "input": str,
                    "matched": bool,
                    "match": str or None,
                    "groups": [str, ...],
                    "named_groups": {name: str},
                    "span": (start, end) or None,
                    "time_us": float,  # 微秒
                }, ...
            ],
            "summary": {
                "total": int,
                "matched": int,
                "not_matched": int,
                "match_rate": float,
                "avg_time_us": float,
                "total_time_us": float,
            },
            "edge_cases": [...],
        }
    """
    # 编译正则
    try:
        regex = re.compile(pattern)
        valid = True
        compile_error = None
    except re.error as e:
        return {
            "pattern": pattern,
            "valid": False,
            "compile_error": str(e),
            "results": [],
            "summary": {},
            "edge_cases": [],
        }

    results = []
    total_time = 0.0

    for test_str in test_strings:
        start_time = time.perf_counter()
        match = regex.search(test_str)
        elapsed = (time.perf_counter() - start_time) * 1_000_000  # 转微秒
        total_time += elapsed

        if match:
            groups = [g if g is not None else "" for g in match.groups()]
            named_groups = {k: v if v else "" for k, v in match.groupdict().items()}
            results.append({
                "input": test_str,
                "matched": True,
                "match": match.group(),
                "groups": groups,
                "named_groups": named_groups,
                "span": match.span(),
                "time_us": round(elapsed, 3),
            })
        else:
            results.append({
                "input": test_str,
                "matched": False,
                "match": None,
                "groups": [],
                "named_groups": {},
                "span": None,
                "time_us": round(elapsed, 3),
            })

    # 生成边界用例
    edge_cases = _generate_edge_cases(regex)

    matched_count = sum(1 for r in results if r["matched"])
    total = len(results)

    return {
        "pattern": pattern,
        "valid": valid,
        "compile_error": compile_error,
        "results": results,
        "summary": {
            "total": total,
            "matched": matched_count,
            "not_matched": total - matched_count,
            "match_rate": round(matched_count / total * 100, 2) if total else 0,
            "avg_time_us": round(total_time / total, 3) if total else 0,
            "total_time_us": round(total_time, 3),
        },
        "edge_cases": edge_cases,
    }


def _generate_edge_cases(regex):
    """自动生成边界测试用例。"""
    edge_strings = [
        "",
        " ",
        "a",
        "A",
        "0",
        "   ",
        "\t",
        "\n",
        "test",
        "TEST",
        "123",
        "!@#$%^&*()",
        "a" * 1000,
        " " * 100,
        "日本語中文English",
        "test@example.com",
        "127.0.0.1",
        "2024-01-15",
        "https://example.com/path?q=1",
        None,  # None值测试
    ]

    edge_results = []
    for s in edge_strings:
        if s is None:
            continue
        try:
            m = regex.search(s)
            edge_results.append({
                "input": s[:50] + "..." if len(s) > 50 else s,
                "matched": bool(m),
                "match": m.group() if m else None,
            })
        except Exception:
            edge_results.append({
                "input": str(s)[:50],
                "matched": False,
                "match": None,
                "error": True,
            })

    return edge_results


# ======================================================================
# 6. api_doc_generator — API文档生成器
# ======================================================================

def api_doc_generator(source_code, format='markdown'):
    """API文档生成器：解析Python函数签名/类型注解/文档字符串，生成API文档。

    算法步骤:
      1. 使用 ast.parse() 解析源代码
      2. 遍历AST，提取所有函数定义
      3. 解析函数签名：
         - 参数名、默认值、类型注解
         - 返回值类型注解
         - 可变参数 (*args, **kwargs)
      4. 解析docstring（支持Google/NumPy/Sphinx风格）
      5. 生成Markdown或HTML格式文档

    Args:
        source_code (str): Python源代码
        format (str): 输出格式 ('markdown' 或 'html')

    Returns:
        dict: {
            "format": str,
            "content": str,
            "functions": [
                {
                    "name": str,
                    "signature": str,
                    "docstring": str,
                    "params": [{"name", "type", "default", "description"}, ...],
                    "returns": {"type", "description"},
                    "raises": [{"type", "description"}, ...],
                    "examples": [str],
                    "line": int,
                }, ...
            ],
            "class_count": int,
            "function_count": int,
        }
    """
    try:
        tree = ast.parse(source_code)
    except SyntaxError as e:
        return {"error": f"SyntaxError: {e}"}

    functions = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_info = _parse_function_node(node)
            functions.append(func_info)

    if format == 'html':
        content = _generate_html_doc(functions)
    else:
        content = _generate_markdown_doc(functions)

    return {
        "format": format,
        "content": content,
        "functions": functions,
        "function_count": len(functions),
    }


def _parse_function_node(node):
    """解析单个函数AST节点，提取签名信息。"""
    # 提取参数
    params = []
    args = node.args

    # 位置参数
    for i, arg in enumerate(args.posonlyargs + args.args):
        param = {
            "name": arg.arg,
            "type": _get_annotation(arg.annotation),
            "default": None,
            "kind": "positional" if i < len(args.posonlyargs) else "positional_or_keyword",
        }
        # 默认值
        defaults = args.defaults
        n_defaults = len(defaults)
        n_args = len(args.posonlyargs) + len(args.args)
        if i >= n_args - n_defaults:
            default_idx = i - (n_args - n_defaults)
            param["default"] = ast.unparse(defaults[default_idx]) if defaults else None
        params.append(param)

    # *args
    if args.vararg:
        params.append({
            "name": f"*{args.vararg.arg}",
            "type": _get_annotation(args.vararg.annotation),
            "default": None,
            "kind": "var_positional",
        })

    # **kwargs
    if args.kwarg:
        params.append({
            "name": f"**{args.kwarg.arg}",
            "type": _get_annotation(args.kwarg.annotation),
            "default": None,
            "kind": "var_keyword",
        })

    # 返回值类型
    return_type = _get_annotation(node.returns)

    # docstring
    docstring = ast.get_docstring(node) or ""

    # 解析docstring中的参数说明
    doc_params, doc_returns, doc_raises, doc_examples = _parse_docstring(docstring, params)

    # 合并参数描述
    for p in params:
        if p["name"] in doc_params:
            p["description"] = doc_params[p["name"]]

    # 构建签名字符串
    sig_params = []
    for p in params:
        s = p["name"]
        if p["type"]:
            s += f": {p['type']}"
        if p["default"] is not None:
            s += f" = {p['default']}"
        sig_params.append(s)
    signature = f"{node.name}({', '.join(sig_params)})"
    if return_type:
        signature += f" -> {return_type}"

    return {
        "name": node.name,
        "signature": signature,
        "docstring": docstring,
        "params": params,
        "returns": {"type": return_type, "description": doc_returns},
        "raises": doc_raises,
        "examples": doc_examples,
        "line": node.lineno,
    }


def _get_annotation(annotation):
    """从AST注解节点提取类型字符串。"""
    if annotation is None:
        return None
    try:
        return ast.unparse(annotation)
    except Exception:
        return str(annotation)


def _parse_docstring(docstring, params):
    """解析docstring，提取参数说明/返回值/异常/示例。

    支持Google风格:
        Args:
            param_name: Description
        Returns:
            Description
        Raises:
            ExceptionType: Description
        Examples:
            >>> func()
    """
    doc_params = {}
    doc_returns = ""
    doc_raises = []
    doc_examples = []

    if not docstring:
        return doc_params, doc_returns, doc_raises, doc_examples

    lines = docstring.split("\n")
    section = None
    current_param = None

    for line in lines:
        stripped = line.strip()

        # 检测段落标记
        if stripped in ("Args:", "Arguments:", "Parameters:"):
            section = "args"
            continue
        elif stripped in ("Returns:", "Return:"):
            section = "returns"
            continue
        elif stripped in ("Raises:", "Raise:"):
            section = "raises"
            continue
        elif stripped in ("Examples:", "Example:", "Usage:"):
            section = "examples"
            continue
        elif stripped in ("Yields:", "Note:", "Notes:"):
            section = None
            continue

        if section == "args":
            # param_name: description  或  param_name (type): description
            match = re.match(r'^(\w+)(?:\s*\([^)]*\))?\s*:\s*(.*)', stripped)
            if match:
                current_param = match.group(1)
                doc_params[current_param] = match.group(2)
            elif current_param and stripped:
                doc_params[current_param] += " " + stripped
        elif section == "returns" and stripped:
            doc_returns += (" " if doc_returns else "") + stripped
        elif section == "raises":
            match = re.match(r'^(\w+)\s*(?:\([^)]*\))?\s*:\s*(.*)', stripped)
            if match:
                doc_raises.append({
                    "type": match.group(1),
                    "description": match.group(2),
                })
        elif section == "examples" and stripped:
            doc_examples.append(stripped)

    return doc_params, doc_returns, doc_raises, doc_examples


def _generate_markdown_doc(functions):
    """生成Markdown格式API文档。"""
    lines = ["# API Documentation\n"]

    for func in functions:
        lines.append(f"## `{func['name']}`\n")
        lines.append(f"**Line:** {func['line']}\n")

        if func["signature"]:
            lines.append(f"```python\n{func['signature']}\n```\n")

        if func["docstring"]:
            lines.append(f"### Description\n\n{func['docstring']}\n")

        if func["params"]:
            lines.append("### Parameters\n")
            lines.append("| Name | Type | Default | Description |")
            lines.append("|------|------|---------|-------------|")
            for p in func["params"]:
                default = p.get("default") or "-"
                desc = p.get("description", "")
                lines.append(f"| `{p['name']}` | `{p.get('type', '-')}` | {default} | {desc} |")
            lines.append("")

        if func["returns"]["type"] or func["returns"]["description"]:
            lines.append("### Returns\n")
            ret_type = func["returns"]["type"] or "Any"
            ret_desc = func["returns"]["description"] or ""
            lines.append(f"- **Type:** `{ret_type}`")
            if ret_desc:
                lines.append(f"- **Description:** {ret_desc}")
            lines.append("")

        if func["raises"]:
            lines.append("### Raises\n")
            for r in func["raises"]:
                lines.append(f"- `{r['type']}`: {r['description']}")
            lines.append("")

        if func["examples"]:
            lines.append("### Examples\n")
            lines.append("```python")
            for ex in func["examples"]:
                lines.append(ex)
            lines.append("```\n")

        lines.append("---\n")

    return "\n".join(lines)


def _generate_html_doc(functions):
    """生成HTML格式API文档。"""
    html_parts = ['<!DOCTYPE html>', '<html lang="en">', '<head>',
                  '<meta charset="UTF-8">', '<title>API Documentation</title>',
                  '<style>body{font-family:sans-serif;max-width:900px;margin:auto;padding:20px;}'
                  'pre{background:#f4f4f4;padding:10px;border-radius:5px;}'
                  'table{border-collapse:collapse;width:100%;}'
                  'th,td{border:1px solid #ddd;padding:8px;text-align:left;}'
                  'th{background:#f0f0f0;}</style></head><body>']
    html_parts.append('<h1>API Documentation</h1>')

    for func in functions:
        html_parts.append(f'<h2>{func["name"]}</h2>')
        if func["signature"]:
            html_parts.append(f'<pre>{func["signature"]}</pre>')
        if func["docstring"]:
            html_parts.append(f'<p>{func["docstring"]}</p>')

        if func["params"]:
            html_parts.append('<h3>Parameters</h3><table>')
            html_parts.append('<tr><th>Name</th><th>Type</th><th>Default</th><th>Description</th></tr>')
            for p in func["params"]:
                html_parts.append(
                    f'<tr><td>{p["name"]}</td><td>{p.get("type", "-")}</td>'
                    f'<td>{p.get("default", "-")}</td><td>{p.get("description", "")}</td></tr>'
                )
            html_parts.append('</table>')

        if func["raises"]:
            html_parts.append('<h3>Raises</h3><ul>')
            for r in func["raises"]:
                html_parts.append(f'<li><strong>{r["type"]}</strong>: {r["description"]}</li>')
            html_parts.append('</ul>')

    html_parts.append('</body></html>')
    return "\n".join(html_parts)


# ======================================================================
# 7. json_schema_inferrer — JSON Schema推断器
# ======================================================================

def json_schema_inferrer(json_samples):
    """JSON Schema推断器：从多个JSON样本中推断Schema。

    算法步骤:
      1. 解析每个JSON样本
      2. 递归分析每个值的类型
      3. 对对象类型：收集所有key，统计出现频率，推断必填字段
      4. 对数组类型：合并所有元素的Schema
      5. 推断枚举值（字段唯一值数<10时）
      6. 合并多个样本的Schema

    Args:
        json_samples (list): JSON字符串列表或Python对象列表

    Returns:
        dict: 推断的JSON Schema
    """
    samples = []
    for s in json_samples:
        if isinstance(s, str):
            try:
                samples.append(json.loads(s))
            except json.JSONDecodeError:
                continue
        else:
            samples.append(s)

    if not samples:
        return {"type": "null"}

    merged_schema = _infer_schema_from_value(samples[0])
    for sample in samples[1:]:
        sample_schema = _infer_schema_from_value(sample)
        merged_schema = _merge_schemas(merged_schema, sample_schema)

    return merged_schema


def _infer_schema_from_value(value, depth=0):
    """递归推断单个值的Schema。"""
    if depth > 20:  # 防止无限递归
        return {"type": "any"}

    if value is None:
        return {"type": "null"}
    elif isinstance(value, bool):
        return {"type": "boolean"}
    elif isinstance(value, int):
        return {"type": "integer", "minimum": value, "maximum": value}
    elif isinstance(value, float):
        return {"type": "number"}
    elif isinstance(value, str):
        schema = {"type": "string"}
        schema["examples"] = [value]
        return schema
    elif isinstance(value, list):
        if not value:
            return {"type": "array", "items": {}}
        # 合并所有元素的Schema
        items_schema = _infer_schema_from_value(value[0], depth + 1)
        for item in value[1:]:
            items_schema = _merge_schemas(items_schema, _infer_schema_from_value(item, depth + 1))
        return {"type": "array", "items": items_schema, "minItems": len(value)}
    elif isinstance(value, dict):
        properties = {}
        required = []
        for key, val in value.items():
            properties[key] = _infer_schema_from_value(val, depth + 1)
            required.append(key)
        schema = {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        }
        return schema
    else:
        return {"type": "any"}


def _merge_schemas(schema1, schema2):
    """合并两个Schema。"""
    if not schema1:
        return schema2
    if not schema2:
        return schema1

    # 取类型交集
    type1 = schema1.get("type", "any")
    type2 = schema2.get("type", "any")

    if type1 == type2:
        merged = {"type": type1}

        # 合并对象属性
        if type1 == "object":
            props1 = schema1.get("properties", {})
            props2 = schema2.get("properties", {})
            merged_props = {}
            for key in set(props1.keys()) | set(props2.keys()):
                if key in props1 and key in props2:
                    merged_props[key] = _merge_schemas(props1[key], props2[key])
                elif key in props1:
                    merged_props[key] = props1[key]
                else:
                    merged_props[key] = props2[key]
            merged["properties"] = merged_props

            # 必填字段：两个Schema都有的
            req1 = set(schema1.get("required", []))
            req2 = set(schema2.get("required", []))
            merged["required"] = sorted(req1 & req2)
            merged["additionalProperties"] = (
                schema1.get("additionalProperties", False) or schema2.get("additionalProperties", False)
            )

        # 合并数组元素
        elif type1 == "array":
            items1 = schema1.get("items", {})
            items2 = schema2.get("items", {})
            merged["items"] = _merge_schemas(items1, items2)

        # 合并枚举值
        if "enum" in schema1 and "enum" in schema2:
            merged["enum"] = sorted(set(schema1["enum"]) | set(schema2["enum"]))

        # 合并范围
        if type1 in ("integer", "number"):
            if "minimum" in schema1 and "minimum" in schema2:
                merged["minimum"] = min(schema1["minimum"], schema2["minimum"])
            if "maximum" in schema1 and "maximum" in schema2:
                merged["maximum"] = max(schema1["maximum"], schema2["maximum"])

        return merged
    else:
        # 不同类型，返回anyOf
        return {"anyOf": [{"type": type1}, {"type": type2}]}


# ======================================================================
# 8. base64_codec_pipeline — Base64编解码管线
# ======================================================================

def base64_codec_pipeline(data, operations):
    """Base64编解码管线：支持编码/解码/URL安全变体/分块传输。

    算法步骤:
      1. 按操作列表依次执行
      2. 每个操作可以是: encode, decode, urlsafe_encode, urlsafe_decode,
         chunk_encode (分块编码), chunk_decode
      3. 分块编码：将数据分成指定大小的块，每块单独Base64编码
      4. 支持链式操作

    Args:
        data (bytes or str): 输入数据
        operations (list): 操作列表，每个操作为 dict:
            {"action": str, "chunk_size": int (可选)}

    Returns:
        dict: {
            "input_type": str,
            "output": bytes or str,
            "operations_applied": int,
            "steps": [{"action", "input_type", "output_type", "data_size"}, ...],
            "success": bool,
            "error": str or None,
        }
    """
    current = data
    steps = []

    try:
        for op in operations:
            action = op.get("action", "encode")
            input_type = type(current).__name__

            if isinstance(current, str):
                current_bytes = current.encode("utf-8")
            elif isinstance(current, bytes):
                current_bytes = current
            else:
                return {
                    "error": f"不支持的数据类型: {type(current)}",
                    "success": False,
                    "output": None,
                }

            if action == "encode":
                result = base64.b64encode(current_bytes)
                current = result.decode("ascii")
                steps.append({"action": "encode", "input_type": input_type,
                              "output_type": "str", "data_size": len(result)})

            elif action == "decode":
                decoded_str = current if isinstance(current, str) else current.decode("ascii")
                result = base64.b64decode(decoded_str)
                current = result
                steps.append({"action": "decode", "input_type": input_type,
                              "output_type": "bytes", "data_size": len(result)})

            elif action == "urlsafe_encode":
                result = base64.urlsafe_b64encode(current_bytes)
                current = result.decode("ascii")
                steps.append({"action": "urlsafe_encode", "input_type": input_type,
                              "output_type": "str", "data_size": len(result)})

            elif action == "urlsafe_decode":
                decoded_str = current if isinstance(current, str) else current.decode("ascii")
                result = base64.urlsafe_b64decode(decoded_str)
                current = result
                steps.append({"action": "urlsafe_decode", "input_type": input_type,
                              "output_type": "bytes", "data_size": len(result)})

            elif action == "chunk_encode":
                chunk_size = op.get("chunk_size", 1024)
                chunks = []
                for i in range(0, len(current_bytes), chunk_size):
                    chunk = current_bytes[i:i + chunk_size]
                    encoded_chunk = base64.b64encode(chunk).decode("ascii")
                    chunks.append(encoded_chunk)
                current = "\n".join(chunks)
                steps.append({"action": "chunk_encode", "input_type": input_type,
                              "output_type": "str", "data_size": len(current),
                              "chunks": len(chunks), "chunk_size": chunk_size})

            elif action == "chunk_decode":
                if isinstance(current, str):
                    chunks = current.strip().split("\n")
                else:
                    chunks = [current.decode("ascii")]
                result = b""
                for chunk in chunks:
                    result += base64.b64decode(chunk.strip())
                current = result
                steps.append({"action": "chunk_decode", "input_type": input_type,
                              "output_type": "bytes", "data_size": len(result),
                              "chunks": len(chunks)})

            elif action == "hex_encode":
                current = current_bytes.hex()
                steps.append({"action": "hex_encode", "input_type": input_type,
                              "output_type": "str", "data_size": len(current)})

            elif action == "hex_decode":
                hex_str = current if isinstance(current, str) else current.decode("ascii")
                current = bytes.fromhex(hex_str)
                steps.append({"action": "hex_decode", "input_type": input_type,
                              "output_type": "bytes", "data_size": len(current)})

            elif action == "md5_hash":
                current = hashlib.md5(current_bytes).hexdigest()
                steps.append({"action": "md5_hash", "input_type": input_type,
                              "output_type": "str", "data_size": len(current)})

            elif action == "sha256_hash":
                current = hashlib.sha256(current_bytes).hexdigest()
                steps.append({"action": "sha256_hash", "input_type": input_type,
                              "output_type": "str", "data_size": len(current)})

            else:
                return {"error": f"未知操作: {action}", "success": False,
                        "output": None, "steps": steps}

        return {
            "input_type": type(data).__name__,
            "output": current,
            "operations_applied": len(steps),
            "steps": steps,
            "success": True,
            "error": None,
        }

    except Exception as e:
        return {
            "input_type": type(data).__name__,
            "output": None,
            "operations_applied": len(steps),
            "steps": steps,
            "success": False,
            "error": str(e),
        }


# ======================================================================
# 9. uuid_generator_with_strategy — UUID多策略生成器
# ======================================================================

def uuid_generator_with_strategy(strategy, count):
    """UUID生成器：支持v1/v3/v4/v5四种策略。

    算法说明:
      - v1: 基于时间戳和MAC地址（node参数可选）
      - v3: 基于命名空间UUID和名称的MD5哈希
      - v4: 随机UUID
      - v5: 基于命名空间UUID和名称的SHA-1哈希

    Args:
        strategy (str or dict): UUID策略
            - "v1": 时间戳UUID
            - "v4": 随机UUID
            - {"version": "v3", "namespace": uuid, "name": str}: MD5命名UUID
            - {"version": "v5", "namespace": uuid, "name": str}: SHA1命名UUID
        count (int): 生成数量

    Returns:
        dict: {
            "strategy": str,
            "count": int,
            "uuids": [str, ...],
            "versions": [int, ...],
            "unique": bool,
        }
    """
    uuids = []

    # 解析策略
    if isinstance(strategy, str):
        version = strategy
        namespace = None
        name = None
        node = None
    elif isinstance(strategy, dict):
        version = strategy.get("version", "v4")
        namespace = strategy.get("namespace")
        name = strategy.get("name")
        node = strategy.get("node")
    else:
        return {"error": "无效的策略参数"}

    # 处理命名空间
    if isinstance(namespace, str):
        try:
            namespace = uuid.UUID(namespace)
        except ValueError:
            namespace = uuid.NAMESPACE_DNS
    elif namespace is None and version in ("v3", "v5"):
        namespace = uuid.NAMESPACE_DNS

    for i in range(count):
        if version == "v1":
            # 时间戳UUID
            kwargs = {}
            if node is not None:
                kwargs["node"] = node
            # 每次生成不同的时钟序列
            u = uuid.uuid1(**kwargs)
        elif version == "v3":
            # MD5命名UUID
            if name is None:
                u = uuid.uuid3(namespace, str(i))
            else:
                # 如果name是模板，替换序号
                actual_name = name.replace("{i}", str(i)) if "{i}" in name else name
                u = uuid.uuid3(namespace, actual_name)
        elif version == "v4":
            # 随机UUID
            u = uuid.uuid4()
        elif version == "v5":
            # SHA1命名UUID
            if name is None:
                u = uuid.uuid5(namespace, str(i))
            else:
                actual_name = name.replace("{i}", str(i)) if "{i}" in name else name
                u = uuid.uuid5(namespace, actual_name)
        else:
            return {"error": f"不支持的UUID版本: {version}"}

        uuids.append(str(u))

    return {
        "strategy": version,
        "count": count,
        "uuids": uuids,
        "versions": [u.version for u in [uuid.UUID(s) for s in uuids]],
        "unique": len(set(uuids)) == len(uuids),
    }


# ======================================================================
# 10. cron_expression_parser — Cron表达式解析器
# ======================================================================

class _CronField:
    """Cron字段解析器。"""
    FIELD_RANGES = {
        "minute": (0, 59),
        "hour": (0, 23),
        "day_of_month": (1, 31),
        "month": (1, 12),
        "day_of_week": (0, 7),  # 0和7都表示周日
    }
    MONTH_NAMES = {
        "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
        "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
    }
    DAY_NAMES = {
        "SUN": 0, "MON": 1, "TUE": 2, "WED": 3, "THU": 4, "FRI": 5, "SAT": 6,
    }

    def __init__(self, field_name):
        self.field_name = field_name
        self.min_val, self.max_val = self.FIELD_RANGES[field_name]
        self.values = set()
        self.raw = ""

    def parse(self, expr):
        """解析cron字段表达式。"""
        self.raw = expr
        expr = expr.upper().strip()
        self.values = set()

        # 处理逗号分隔的列表
        for part in expr.split(","):
            self._parse_part(part.strip())

        return sorted(self.values)

    def _parse_part(self, part):
        """解析单个部分（如 1-5, */2, 3, MON）。"""
        if not part:
            return

        # 处理 */N 步进
        if part.startswith("*/"):
            step = int(part[2:])
            for v in range(self.min_val, self.max_val + 1, step):
                self.values.add(v)
            return

        # 处理 * 通配符
        if part == "*":
            for v in range(self.min_val, self.max_val + 1):
                self.values.add(v)
            return

        # 处理范围 A-B/N
        if "/" in part:
            range_part, step_part = part.split("/", 1)
            step = int(step_part)
            if range_part == "*":
                start, end = self.min_val, self.max_val
            elif "-" in range_part:
                parts = range_part.split("-")
                start = self._resolve_value(parts[0])
                end = self._resolve_value(parts[1])
            else:
                start = self._resolve_value(range_part)
                end = self.max_val
            for v in range(start, end + 1, step):
                self.values.add(v)
            return

        # 处理范围 A-B
        if "-" in part:
            parts = part.split("-")
            start = self._resolve_value(parts[0])
            end = self._resolve_value(parts[1])
            for v in range(start, end + 1):
                self.values.add(v)
            return

        # 单个值
        val = self._resolve_value(part)
        self.values.add(val)

    def _resolve_value(self, s):
        """解析单个值，支持数字和名称。"""
        s = s.strip().upper()
        if self.field_name == "month" and s in self.MONTH_NAMES:
            return self.MONTH_NAMES[s]
        if self.field_name == "day_of_week" and s in self.DAY_NAMES:
            return self.DAY_NAMES[s]
        try:
            val = int(s)
        except ValueError:
            raise ValueError(f"无法解析值 '{s}' 在字段 '{self.field_name}'")
        if val < self.min_val or val > self.max_val:
            raise ValueError(f"值 {val} 超出字段 '{self.field_name}' 范围 [{self.min_val}, {self.max_val}]")
        return val


def cron_expression_parser(cron_expr, from_time=None):
    """Cron表达式解析器：解析5字段cron表达式，计算下次执行时间。

    算法步骤:
      1. 分割cron表达式为5个字段：minute hour day_of_month month day_of_week
      2. 解析每个字段为允许值集合
      3. 语法验证（范围/步进/通配符合法性）
      4. 从基准时间开始，逐分钟扫描找到第一个匹配的时间点
      5. 优化：跳过不匹配的月份/日期/小时

    Cron字段:
      minute:        0-59
      hour:          0-23
      day_of_month:  1-31
      month:         1-12 (JAN-DEC)
      day_of_week:   0-6 (SUN-SAT, 7也=SUN)

    特殊字符:
      *  = 任意值
      */N = 每N个单位
      A-B = 范围A到B
      A,B,C = 列表
      A-B/N = 范围A到B，步进N

    Args:
        cron_expr (str): 5字段cron表达式
        from_time (datetime): 计算下次执行时间的基准（默认当前时间）

    Returns:
        dict: {
            "expression": str,
            "valid": bool,
            "error": str or None,
            "fields": {
                "minute": [int, ...],
                "hour": [int, ...],
                "day_of_month": [int, ...],
                "month": [int, ...],
                "day_of_week": [int, ...],
            },
            "description": str,
            "next_run": str (ISO格式) or None,
            "next_5_runs": [str, ...],
        }
    """
    parts = cron_expr.strip().split()

    if len(parts) != 5:
        return {
            "expression": cron_expr,
            "valid": False,
            "error": f"Cron表达式需要5个字段，收到{len(parts)}个",
            "fields": {},
            "description": "",
            "next_run": None,
            "next_5_runs": [],
        }

    field_names = ["minute", "hour", "day_of_month", "month", "day_of_week"]
    fields = {}

    for fname, fexpr in zip(field_names, parts):
        field = _CronField(fname)
        try:
            values = field.parse(fexpr)
            fields[fname] = values
        except ValueError as e:
            return {
                "expression": cron_expr,
                "valid": False,
                "error": str(e),
                "fields": {},
                "description": "",
                "next_run": None,
                "next_5_runs": [],
            }

    # day_of_week: 7映射为0
    if 7 in fields["day_of_week"]:
        fields["day_of_week"].add(0)
        fields["day_of_week"].discard(7)

    # 生成描述
    description = _describe_cron(fields, parts)

    # 计算下次执行时间
    base_time = from_time or datetime.now()
    next_runs = []

    # 从下一分钟开始搜索
    search_time = base_time.replace(second=0, microsecond=0) + timedelta(minutes=1)

    for _ in range(5):  # 找最近5次
        next_time = _find_next_match(search_time, fields)
        if next_time:
            next_runs.append(next_time.isoformat())
            search_time = next_time + timedelta(minutes=1)
        else:
            break

    return {
        "expression": cron_expr,
        "valid": True,
        "error": None,
        "fields": {
            "minute": sorted(fields["minute"]),
            "hour": sorted(fields["hour"]),
            "day_of_month": sorted(fields["day_of_month"]),
            "month": sorted(fields["month"]),
            "day_of_week": sorted(fields["day_of_week"]),
        },
        "description": description,
        "next_run": next_runs[0] if next_runs else None,
        "next_5_runs": next_runs,
    }


def _find_next_match(start_time, fields, max_days=366):
    """从start_time开始逐分钟搜索，找到第一个匹配cron表达式的时间。"""
    current = start_time
    days_searched = 0

    while days_searched < max_days:
        # 检查月份
        if current.month not in fields["month"]:
            # 跳到下个月1号0点
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1, day=1, hour=0, minute=0)
            else:
                current = current.replace(month=current.month + 1, day=1, hour=0, minute=0)
            continue

        # 检查日期
        day_ok = True
        if fields["day_of_month"] != list(range(1, 32)) and fields["day_of_week"] != [0, 1, 2, 3, 4, 5, 6]:
            # 如果两个字段都设置了（不是*），则取并集
            day_ok = (current.day in fields["day_of_month"] or
                      current.weekday() in [d % 7 for d in fields["day_of_week"]])
        else:
            day_ok = (current.day in fields["day_of_month"] and
                      current.weekday() in [d % 7 for d in fields["day_of_week"]])

        if not day_ok:
            # 跳到明天0点
            current = current.replace(hour=0, minute=0) + timedelta(days=1)
            days_searched += 1
            # 检查是否跨月
            while current.month not in fields["month"]:
                if current.month == 12:
                    current = current.replace(year=current.year + 1, month=1, day=1)
                else:
                    current = current.replace(month=current.month + 1, day=1)
            continue

        # 检查小时
        if current.hour not in fields["hour"]:
            next_hour = current.hour + 1
            if next_hour > 23:
                current = current.replace(hour=0, minute=0) + timedelta(days=1)
            else:
                current = current.replace(hour=next_hour, minute=0)
            continue

        # 检查分钟
        if current.minute not in fields["minute"]:
            next_minute = current.minute + 1
            if next_minute > 59:
                current = current.replace(minute=0) + timedelta(hours=1)
            else:
                current = current.replace(minute=next_minute)
            continue

        # 全部匹配
        return current

    return None


def _describe_cron(fields, raw_parts):
    """生成cron表达式的人类可读描述。"""
    minute_raw, hour_raw, dom_raw, month_raw, dow_raw = raw_parts

    # 常见模式的描述
    if minute_raw == "0" and hour_raw == "0" and dom_raw == "*" and month_raw == "*" and dow_raw == "*":
        return "每天午夜执行"
    if minute_raw == "0" and hour_raw == "*" and dom_raw == "*" and month_raw == "*" and dow_raw == "*":
        return "每小时整点执行"
    if minute_raw == "*/30" and hour_raw == "*" and dom_raw == "*" and month_raw == "*" and dow_raw == "*":
        return "每30分钟执行一次"
    if minute_raw == "*/5" and hour_raw == "*" and dom_raw == "*" and month_raw == "*" and dow_raw == "*":
        return "每5分钟执行一次"
    if minute_raw == "0" and hour_raw == "0" and dom_raw == "*" and month_raw == "*" and dow_raw == "1-5":
        return "工作日（周一到周五）午夜执行"
    if minute_raw == "0" and hour_raw == "0" and dom_raw == "1" and month_raw == "*" and dow_raw == "*":
        return "每月1号午夜执行"

    # 构建自定义描述
    parts = []

    if minute_raw == "*":
        parts.append("每分钟")
    elif "/" in minute_raw:
        step = minute_raw.split("/")[1]
        parts.append(f"每{step}分钟")
    else:
        parts.append(f"在第{','.join(str(m) for m in sorted(fields['minute']))}分钟")

    if hour_raw == "*":
        if "每分钟" not in parts[0]:
            parts.append("每小时")
    elif "/" in hour_raw:
        step = hour_raw.split("/")[1]
        parts.append(f"每{step}小时")
    else:
        parts.append(f"在{','.join(str(h) for h in sorted(fields['hour']))}时")

    if dow_raw != "*":
        day_names = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"]
        days = [day_names[d % 7] for d in sorted(fields["day_of_week"])]
        parts.append(f"的{','.join(days)}")

    if month_raw != "*":
        month_names = ["1月", "2月", "3月", "4月", "5月", "6月",
                       "7月", "8月", "9月", "10月", "11月", "12月"]
        months = [month_names[m - 1] for m in sorted(fields["month"])]
        parts.append(f"的{','.join(months)}")

    return "执行".join(["".join(parts[:1]), "".join(parts[1:])]) if len(parts) > 1 else "".join(parts)


# ======================================================================
# 主程序测试
# ======================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("code-toolkit 测试")
    print("=" * 60)

    # 1. 代码复杂度分析
    print("\n--- 1. code_complexity_analyzer ---")
    test_code = '''
def calculate_score(data):
    """计算得分"""
    score = 0
    for item in data:
        if item > 0:
            if item > 10:
                score += item * 2
            else:
                score += item
        elif item < -10:
            score -= abs(item)
    return score if score > 0 or data else -1
'''
    result = code_complexity_analyzer(test_code)
    print(f"函数数: {result['total_functions']}")
    print(f"平均复杂度: {result['average_complexity']}")
    for func in result["functions"]:
        print(f"  {func['name']}: 复杂度={func['complexity']} ({func['level']})")

    # 2. 依赖图
    print("\n--- 2. dependency_graph_builder ---")
    dep_code = '''
import os
import sys
from collections import defaultdict
from datetime import datetime
'''
    dep_result = dependency_graph_builder(dep_code, "test_module")
    print(f"模块: {dep_result['module']}")
    print(f"依赖数: {dep_result['import_count']}")
    print(f"依赖模块: {dep_result['dependencies']}")

    # 3. 代码异味
    print("\n--- 3. code_smell_detector ---")
    smell_result = code_smell_detector(test_code)
    print(f"异味总数: {smell_result['total_smells']}")
    print(f"质量评分: {smell_result['score']}/100")
    for cat, count in smell_result["by_category"].items():
        print(f"  {cat}: {count}")

    # 4. SQL格式化
    print("\n--- 4. sql_formatter_and_validator ---")
    sql = "select id,name,email from users where age>18 and status='active' order by name;"
    sql_result = sql_formatter_and_validator(sql)
    print(f"有效: {sql_result['valid']}")
    print(f"关键字数: {sql_result['stats']['keyword_count']}")
    print(f"格式化结果:\n{sql_result['formatted']}")

    # 5. 正则测试
    print("\n--- 5. regex_engine_tester ---")
    regex_result = regex_engine_tester(
        r"(\d{4})-(\d{2})-(\d{2})",
        ["2024-01-15", "not a date", "2023-12-31", "99-99-99"]
    )
    print(f"有效: {regex_result['valid']}")
    print(f"匹配率: {regex_result['summary']['match_rate']}%")
    for r in regex_result["results"]:
        print(f"  '{r['input']}' → matched={r['matched']}, groups={r['groups']}")

    # 6. API文档生成
    print("\n--- 6. api_doc_generator ---")
    api_code = '''
def add(a: int, b: int = 0) -> int:
    """Add two numbers.

    Args:
        a: First number
        b: Second number, default 0

    Returns:
        Sum of a and b

    Raises:
        TypeError: If inputs are not numbers
    """
    return a + b
'''
    doc_result = api_doc_generator(api_code, "markdown")
    print(f"函数数: {doc_result['function_count']}")
    if doc_result["functions"]:
        f = doc_result["functions"][0]
        print(f"  签名: {f['signature']}")
        print(f"  参数: {len(f['params'])}个")
        print(f"  返回类型: {f['returns']['type']}")

    # 7. JSON Schema推断
    print("\n--- 7. json_schema_inferrer ---")
    samples = [
        '{"name": "Alice", "age": 30, "email": "a@b.com"}',
        '{"name": "Bob", "age": 25, "email": "b@c.com", "phone": "123"}',
    ]
    schema = json_schema_inferrer(samples)
    print(f"类型: {schema.get('type')}")
    print(f"必填字段: {schema.get('required', [])}")
    if "properties" in schema:
        for k, v in schema["properties"].items():
            print(f"  {k}: {v.get('type')}")

    # 8. Base64管线
    print("\n--- 8. base64_codec_pipeline ---")
    b64_result = base64_codec_pipeline(
        "Hello, World!",
        [{"action": "encode"}, {"action": "md5_hash"}]
    )
    print(f"成功: {b64_result['success']}")
    print(f"操作数: {b64_result['operations_applied']}")
    print(f"输出: {b64_result['output']}")

    # 9. UUID生成
    print("\n--- 9. uuid_generator_with_strategy ---")
    uuid_result = uuid_generator_with_strategy({"version": "v5", "namespace": None, "name": "test"}, 3)
    print(f"策略: {uuid_result['strategy']}")
    print(f"唯一: {uuid_result['unique']}")
    for u in uuid_result["uuids"]:
        print(f"  {u}")

    # 10. Cron解析
    print("\n--- 10. cron_expression_parser ---")
    cron_result = cron_expression_parser("0 9 * * 1-5")
    print(f"有效: {cron_result['valid']}")
    print(f"描述: {cron_result['description']}")
    print(f"下次执行: {cron_result['next_run']}")

    cron_result2 = cron_expression_parser("*/30 * * * *")
    print(f"\n有效: {cron_result2['valid']}")
    print(f"描述: {cron_result2['description']}")
    print(f"下次执行: {cron_result2['next_run']}")

    print("\n" + "=" * 60)
    print("所有测试完成")
    print("=" * 60)
