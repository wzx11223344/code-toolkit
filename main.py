"""
开发编程工具箱 (code-toolkit)

提供10个开发辅助工具，包括代码质量分析、SQL格式化、正则表达式测试、
API文档生成、圈复杂度分析、依赖检查、JSON格式化、Base64编解码、UUID生成
和Cron表达式验证。所有功能仅使用Python标准库实现，无需安装额外依赖。

主要功能:
    - analyze_code_quality: 代码质量分析
    - format_sql: SQL格式化
    - test_regex: 正则表达式测试
    - generate_api_documentation: API文档生成
    - code_complexity_analyzer: 圈复杂度分析
    - dependency_checker: 依赖检查
    - json_formatter: JSON格式化/压缩
    - base64_encoder_decoder: Base64编解码
    - uuid_generator: UUID生成器
    - cron_validator: Cron表达式验证

依赖:
    无外部依赖（仅使用Python标准库）
"""

import re
import json
import uuid
import base64
import ast
import keyword
from collections import OrderedDict


# =============================================================================
# 1. 代码质量分析
# =============================================================================
def analyze_code_quality(code_string, language="python"):
    """
    分析代码质量，包括行数统计、注释率、空行率等。

    Args:
        code_string (str): 源代码字符串。
        language (str): 编程语言，支持 "python"/"java"/"javascript"/"c"。
            默认 "python"。

    Returns:
        dict: 包含以下键的字典:
            - "total_lines": 总行数
            - "code_lines": 代码行数
            - "comment_lines": 注释行数
            - "blank_lines": 空行数
            - "comment_ratio": 注释率（百分比）
            - "code_ratio": 代码占比（百分比）
            - "issues": 代码问题列表

    Example:
        >>> result = analyze_code_quality("def foo():\n    # comment\n    pass")
        {'total_lines': 3, 'code_lines': 2, 'comment_lines': 1, ...}
    """
    lines = code_string.split("\n")
    total_lines = len(lines)
    code_lines = 0
    comment_lines = 0
    blank_lines = 0
    issues = []

    # 语言注释标记
    comment_patterns = {
        "python": [(r"#",), (r'"""', r'"""'), (r"'''", r"'''")],
        "java": [(r"//",), (r"/\*", r"\*/")],
        "javascript": [(r"//",), (r"/\*", r"\*/")],
        "c": [(r"//",), (r"/\*", r"\*/")],
    }
    patterns = comment_patterns.get(language, comment_patterns["python"])

    in_block_comment = False
    block_start = patterns[1][0] if len(patterns) > 1 else None
    block_end = patterns[1][1] if len(patterns) > 1 else None

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        if not stripped:
            blank_lines += 1
            continue

        # 块注释处理
        if in_block_comment:
            comment_lines += 1
            if block_end and re.search(block_end, stripped):
                in_block_comment = False
            continue

        if block_start and re.search(block_start, stripped):
            comment_lines += 1
            if block_end and not re.search(block_end, stripped):
                in_block_comment = True
            continue

        # 单行注释
        single_comment = patterns[0][0]
        if re.match(single_comment, stripped):
            comment_lines += 1
            continue

        # 行尾注释
        if re.search(single_comment, stripped):
            code_lines += 1
        else:
            code_lines += 1

        # 检查常见问题
        if len(line) > 120:
            issues.append(f"第{i}行: 行长度超过120字符 ({len(line)}字符)")
        if language == "python":
            if "\t" in line:
                issues.append(f"第{i}行: 使用了Tab缩进，建议使用空格")
            if stripped.endswith(" ") or stripped.endswith("\t"):
                issues.append(f"第{i}行: 行尾有多余空格")

    comment_ratio = round(comment_lines / total_lines * 100, 1) if total_lines else 0
    code_ratio = round(code_lines / total_lines * 100, 1) if total_lines else 0

    return {
        "total_lines": total_lines,
        "code_lines": code_lines,
        "comment_lines": comment_lines,
        "blank_lines": blank_lines,
        "comment_ratio": comment_ratio,
        "code_ratio": code_ratio,
        "issues": issues,
    }


# =============================================================================
# 2. SQL格式化
# =============================================================================
def format_sql(sql_string):
    """
    格式化SQL语句，使其更易读。

    将SQL关键字大写，并在适当位置添加换行和缩进。

    Args:
        sql_string (str): 待格式化的SQL语句。

    Returns:
        dict: 包含以下键的字典:
            - "formatted": 格式化后的SQL
            - "original_length": 原始长度
            - "formatted_length": 格式化后长度

    Example:
        >>> result = format_sql("select * from users where id = 1")
        {'formatted': 'SELECT *\nFROM users\nWHERE id = 1', ...}
    """
    # SQL关键字
    keywords = [
        "SELECT", "FROM", "WHERE", "INSERT INTO", "VALUES", "UPDATE",
        "SET", "DELETE FROM", "JOIN", "LEFT JOIN", "RIGHT JOIN", "INNER JOIN",
        "OUTER JOIN", "ON", "GROUP BY", "ORDER BY", "HAVING", "LIMIT",
        "OFFSET", "UNION", "UNION ALL", "CREATE TABLE", "ALTER TABLE",
        "DROP TABLE", "AND", "OR", "NOT", "IN", "NOT IN", "EXISTS",
        "BETWEEN", "LIKE", "IS NULL", "IS NOT NULL", "AS", "DISTINCT",
        "CASE", "WHEN", "THEN", "ELSE", "END", "WITH", "INSERT",
    ]

    formatted = sql_string.strip()

    # 移除多余空格
    formatted = re.sub(r"\s+", " ", formatted)

    # 关键字大写
    for kw in sorted(keywords, key=len, reverse=True):
        pattern = re.compile(re.escape(kw), re.IGNORECASE)
        formatted = pattern.sub(kw.upper(), formatted)

    # 在主要关键字前添加换行
    newline_keywords = [
        "SELECT", "FROM", "WHERE", "INSERT INTO", "VALUES", "UPDATE",
        "SET", "DELETE FROM", "JOIN", "LEFT JOIN", "RIGHT JOIN",
        "INNER JOIN", "GROUP BY", "ORDER BY", "HAVING", "LIMIT",
        "UNION", "UNION ALL", "CREATE TABLE", "ALTER TABLE", "DROP TABLE",
        "WITH",
    ]
    for kw in sorted(newline_keywords, key=len, reverse=True):
        formatted = re.sub(
            r"\s+" + re.escape(kw) + r"\b",
            "\n" + kw,
            formatted
        )

    # 缩进处理
    lines = formatted.split("\n")
    indented_lines = []
    for line in lines:
        line = line.strip()
        # AND/OR 缩进
        if line.upper().startswith("AND") or line.upper().startswith("OR"):
            indented_lines.append("    " + line)
        else:
            indented_lines.append(line)

    formatted = "\n".join(indented_lines)

    return {
        "formatted": formatted,
        "original_length": len(sql_string),
        "formatted_length": len(formatted),
    }


# =============================================================================
# 3. 正则表达式测试
# =============================================================================
def test_regex(pattern, test_string):
    """
    测试正则表达式，返回所有匹配结果。

    Args:
        pattern (str): 正则表达式模式字符串。
        test_string (str): 待测试的字符串。

    Returns:
        dict: 包含以下键的字典:
            - "pattern": 正则表达式
            - "matched": 是否匹配成功
            - "matches": 匹配结果列表，每项为 {"match": 匹配文本, "start": 起始位置, "end": 结束位置, "groups": 分组列表}
            - "match_count": 匹配数量
            - "replaced": 使用"REPLACED"替换后的文本（演示）
            - "error": 错误信息（如有）

    Example:
        >>> result = test_regex(r"\d+", "abc123def456")
        {'matched': True, 'matches': [{'match': '123', 'start': 3, 'end': 6, ...}, ...]}
    """
    result = {
        "pattern": pattern,
        "matched": False,
        "matches": [],
        "match_count": 0,
        "replaced": "",
        "error": None,
    }

    try:
        regex = re.compile(pattern)
    except re.error as e:
        result["error"] = f"正则表达式错误: {e}"
        return result

    matches = list(regex.finditer(test_string))

    if matches:
        result["matched"] = True
        result["match_count"] = len(matches)

        for m in matches:
            groups = [g for g in m.groups()] if m.groups() else []
            result["matches"].append({
                "match": m.group(),
                "start": m.start(),
                "end": m.end(),
                "groups": groups,
            })

        # 替换演示
        result["replaced"] = regex.sub("REPLACED", test_string)

    return result


# =============================================================================
# 4. API文档生成
# =============================================================================
def generate_api_documentation(routes, output_format="markdown"):
    """
    根据路由定义生成API文档。

    Args:
        routes (list): 路由列表，每项为字典:
            {
                "method": "GET"/"POST"/"PUT"/"DELETE",
                "path": "/api/users",
                "description": "获取用户列表",
                "parameters": [{"name": "id", "type": "int", "required": True, "description": "用户ID"}],
                "responses": {"200": "成功", "404": "未找到"}
            }
        output_format (str): 输出格式，支持 "markdown"/"html"/"json"。

    Returns:
        dict: 包含以下键的字典:
            - "documentation": 生成的文档文本
            - "format": 输出格式
            - "route_count": 路由数量

    Example:
        >>> doc = generate_api_documentation([
        ...     {"method": "GET", "path": "/users", "description": "获取用户", "parameters": [], "responses": {"200": "OK"}}
        ... ])
    """
    if output_format == "json":
        return {
            "documentation": json.dumps(routes, indent=2, ensure_ascii=False),
            "format": "json",
            "route_count": len(routes),
        }

    if output_format == "html":
        html_parts = ["<!DOCTYPE html>", "<html>", "<head><meta charset='utf-8'><title>API Documentation</title></head>", "<body>", "<h1>API Documentation</h1>"]
        for route in routes:
            method = route.get("method", "GET")
            path = route.get("path", "")
            desc = route.get("description", "")
            html_parts.append(f"<h2>{method} {path}</h2>")
            html_parts.append(f"<p>{desc}</p>")
            params = route.get("parameters", [])
            if params:
                html_parts.append("<h3>Parameters</h3><table border='1'><tr><th>Name</th><th>Type</th><th>Required</th><th>Description</th></tr>")
                for p in params:
                    html_parts.append(f"<tr><td>{p.get('name','')}</td><td>{p.get('type','')}</td><td>{'Yes' if p.get('required') else 'No'}</td><td>{p.get('description','')}</td></tr>")
                html_parts.append("</table>")
            responses = route.get("responses", {})
            if responses:
                html_parts.append("<h3>Responses</h3><ul>")
                for code, desc in responses.items():
                    html_parts.append(f"<li>{code}: {desc}</li>")
                html_parts.append("</ul>")
        html_parts.append("</body></html>")
        return {
            "documentation": "\n".join(html_parts),
            "format": "html",
            "route_count": len(routes),
        }

    # Markdown 格式（默认）
    md_lines = ["# API Documentation\n"]

    for route in routes:
        method = route.get("method", "GET")
        path = route.get("path", "")
        desc = route.get("description", "")

        md_lines.append(f"## {method} `{path}`\n")
        md_lines.append(f"**描述**: {desc}\n")

        # 参数表
        params = route.get("parameters", [])
        if params:
            md_lines.append("### Parameters\n")
            md_lines.append("| Name | Type | Required | Description |")
            md_lines.append("|------|------|----------|-------------|")
            for p in params:
                name = p.get("name", "")
                ptype = p.get("type", "")
                required = "Yes" if p.get("required") else "No"
                pdesc = p.get("description", "")
                md_lines.append(f"| {name} | {ptype} | {required} | {pdesc} |")
            md_lines.append("")

        # 响应
        responses = route.get("responses", {})
        if responses:
            md_lines.append("### Responses\n")
            for code, rdesc in responses.items():
                md_lines.append(f"- **{code}**: {rdesc}")
            md_lines.append("")

        md_lines.append("---\n")

    return {
        "documentation": "\n".join(md_lines),
        "format": "markdown",
        "route_count": len(routes),
    }


# =============================================================================
# 5. 圈复杂度分析
# =============================================================================
def code_complexity_analyzer(code_string):
    """
    分析Python代码的圈复杂度（Cyclomatic Complexity）。

    圈复杂度通过统计控制流分支（if/for/while/and/or/except等）来衡量代码复杂程度。

    Args:
        code_string (str): Python源代码字符串。

    Returns:
        dict: 包含以下键的字典:
            - "complexity": 圈复杂度数值
            - "level": 复杂度等级（"低"/"中"/"高"/"极高"）
            - "branches": 分支详情字典（各类型的分支数量）
            - "functions": 函数级复杂度列表
            - "recommendation": 优化建议

    Example:
        >>> result = code_complexity_analyzer("def f():\n    if True:\n        pass")
        {'complexity': 2, 'level': '低', ...}
    """
    complexity = 1  # 基础复杂度
    branches = {
        "if": 0,
        "elif": 0,
        "for": 0,
        "while": 0,
        "except": 0,
        "and": 0,
        "or": 0,
        "ternary": 0,
        "comprehension": 0,
    }

    functions = []

    try:
        tree = ast.parse(code_string)
    except SyntaxError as e:
        return {
            "complexity": 0,
            "level": "未知",
            "branches": branches,
            "functions": [],
            "recommendation": f"代码存在语法错误: {e}",
        }

    # 统计各节点
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            # if 语句：第一个if计为if，后续elif也计为if
            complexity += 1
            branches["if"] += 1
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            complexity += 1
            branches["for"] += 1
        elif isinstance(node, ast.While):
            complexity += 1
            branches["while"] += 1
        elif isinstance(node, ast.ExceptHandler):
            complexity += 1
            branches["except"] += 1
        elif isinstance(node, ast.BoolOp):
            # and/or 操作符
            complexity += len(node.values) - 1
            if isinstance(node.op, ast.And):
                branches["and"] += len(node.values) - 1
            else:
                branches["or"] += len(node.values) - 1
        elif isinstance(node, ast.IfExp):
            # 三元表达式
            complexity += 1
            branches["ternary"] += 1
        elif isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            # 推导式
            complexity += len(node.generators)
            branches["comprehension"] += len(node.generators)

    # 函数级复杂度
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_complexity = 1
            for child in ast.walk(node):
                if child is node:
                    continue
                if isinstance(child, ast.If):
                    func_complexity += 1
                elif isinstance(child, (ast.For, ast.AsyncFor, ast.While)):
                    func_complexity += 1
                elif isinstance(child, ast.ExceptHandler):
                    func_complexity += 1
                elif isinstance(child, ast.BoolOp):
                    func_complexity += len(child.values) - 1
                elif isinstance(child, ast.IfExp):
                    func_complexity += 1
                elif isinstance(child, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                    func_complexity += len(child.generators)

            func_level = "低"
            if func_complexity > 10:
                func_level = "极高"
            elif func_complexity > 7:
                func_level = "高"
            elif func_complexity > 4:
                func_level = "中"

            functions.append({
                "name": node.name,
                "line": node.lineno,
                "complexity": func_complexity,
                "level": func_level,
            })

    # 评级
    if complexity <= 5:
        level = "低"
        recommendation = "代码复杂度低，易于维护。"
    elif complexity <= 10:
        level = "中"
        recommendation = "代码复杂度适中，可考虑适当拆分。"
    elif complexity <= 20:
        level = "高"
        recommendation = "代码复杂度较高，建议拆分函数或简化逻辑。"
    else:
        level = "极高"
        recommendation = "代码复杂度极高，强烈建议重构，拆分为更小的函数。"

    return {
        "complexity": complexity,
        "level": level,
        "branches": branches,
        "functions": functions,
        "recommendation": recommendation,
    }


# =============================================================================
# 6. 依赖检查
# =============================================================================
def dependency_checker(requirements_text):
    """
    检查requirements.txt中的依赖项，分析版本规范。

    Args:
        requirements_text (str): requirements.txt 文件内容。

    Returns:
        dict: 包含以下键的字典:
            - "total_packages": 总包数
            - "packages": 包信息列表，每项为 {"name": 包名, "version_spec": 版本规范, "pinned": 是否锁定版本, "status": 状态}
            - "warnings": 警告列表
            - "summary": 统计摘要

    Example:
        >>> result = dependency_checker("requests>=2.0\nflask\nnumpy==1.21")
    """
    lines = requirements_text.strip().split("\n")
    packages = []
    warnings = []

    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # 解析包名和版本
        # 常见格式: package, package==1.0, package>=1.0, package~=1.0
        match = re.match(
            r"^([a-zA-Z0-9_-]+)\s*(.*)$",
            line.split("#")[0].strip()
        )
        if not match:
            warnings.append(f"第{line_num}行: 无法解析依赖项 '{line}'")
            continue

        name = match.group(1)
        version_spec = match.group(2).strip()

        # 判断版本锁定状态
        pinned = False
        status = "OK"
        if not version_spec:
            status = "未指定版本"
            warnings.append(f"第{line_num}行: '{name}' 未指定版本，建议锁定版本")
        elif version_spec.startswith("=="):
            pinned = True
        elif version_spec.startswith(">=") or version_spec.startswith(">"):
            status = "使用最低版本约束"
        elif version_spec.startswith("~="):
            status = "兼容版本"
        elif version_spec.startswith("*"):
            status = "通配符版本"
            warnings.append(f"第{line_num}行: '{name}' 使用通配符，可能不稳定")

        packages.append({
            "name": name,
            "version_spec": version_spec if version_spec else "(无)",
            "pinned": pinned,
            "status": status,
        })

    pinned_count = sum(1 for p in packages if p["pinned"])

    return {
        "total_packages": len(packages),
        "packages": packages,
        "warnings": warnings,
        "summary": {
            "total": len(packages),
            "pinned": pinned_count,
            "unpinned": len(packages) - pinned_count,
            "warnings_count": len(warnings),
        },
    }


# =============================================================================
# 7. JSON格式化/压缩
# =============================================================================
def json_formatter(json_string, indent=2):
    """
    格式化或压缩JSON字符串。

    Args:
        json_string (str): JSON字符串。如果为无效JSON则返回错误信息。
        indent (int): 缩进空格数。设为0则输出压缩格式。默认2。

    Returns:
        dict: 包含以下键的字典:
            - "formatted": 格式化后的JSON字符串
            - "is_valid": 是否为有效JSON
            - "original_size": 原始大小（字符数）
            - "formatted_size": 格式化后大小
            - "error": 错误信息（如有）

    Example:
        >>> result = json_formatter('{"a":1,"b":2}', indent=4)
        {'formatted': '{\n    "a": 1,\n    "b": 2\n}', 'is_valid': True, ...}
    """
    original_size = len(json_string)

    try:
        data = json.loads(json_string)
    except json.JSONDecodeError as e:
        return {
            "formatted": json_string,
            "is_valid": False,
            "original_size": original_size,
            "formatted_size": original_size,
            "error": f"JSON解析错误: {e}",
        }

    if indent and indent > 0:
        formatted = json.dumps(data, indent=indent, ensure_ascii=False, sort_keys=False)
    else:
        # 压缩模式
        formatted = json.dumps(data, ensure_ascii=False, separators=(",", ":"))

    return {
        "formatted": formatted,
        "is_valid": True,
        "original_size": original_size,
        "formatted_size": len(formatted),
        "error": None,
    }


# =============================================================================
# 8. Base64编解码
# =============================================================================
def base64_encoder_decoder(text, mode="encode"):
    """
    Base64编码或解码文本。

    Args:
        text (str): 待处理的文本。编码模式下为普通文本，解码模式下为Base64字符串。
        mode (str): 操作模式，"encode" 编码 / "decode" 解码。默认 "encode"。

    Returns:
        dict: 包含以下键的字典:
            - "input": 输入文本
            - "output": 输出文本
            - "mode": 操作模式
            - "success": 是否成功
            - "error": 错误信息（如有）

    Example:
        >>> result = base64_encoder_decoder("Hello World", mode="encode")
        {'output': 'SGVsbG8gV29ybGQ=', 'mode': 'encode', 'success': True, ...}
    """
    result = {
        "input": text,
        "output": "",
        "mode": mode,
        "success": False,
        "error": None,
    }

    try:
        if mode == "encode":
            encoded_bytes = base64.b64encode(text.encode("utf-8"))
            result["output"] = encoded_bytes.decode("utf-8")
            result["success"] = True
        elif mode == "decode":
            # 清理可能的换行和空格
            clean_text = text.strip().replace("\n", "").replace(" ", "")
            decoded_bytes = base64.b64decode(clean_text)
            result["output"] = decoded_bytes.decode("utf-8")
            result["success"] = True
        else:
            result["error"] = f"不支持的模式: {mode}，请使用 'encode' 或 'decode'"
    except Exception as e:
        result["error"] = f"{mode}操作失败: {e}"

    return result


# =============================================================================
# 9. UUID生成器
# =============================================================================
def uuid_generator(version=4, count=1):
    """
    生成指定版本的UUID。

    Args:
        version (int): UUID版本，支持 1/3/4/5。默认4。
            - 1: 基于时间戳和MAC地址
            - 3: 基于MD5哈希（命名空间+名称）
            - 4: 随机UUID（最常用）
            - 5: 基于SHA-1哈希（命名空间+名称）
        count (int): 生成数量，默认1。

    Returns:
        dict: 包含以下键的字典:
            - "uuids": UUID字符串列表
            - "version": UUID版本
            - "count": 生成数量

    Example:
        >>> result = uuid_generator(version=4, count=3)
        {'uuids': ['a3f4...', 'b5e2...', 'c7d1...'], 'version': 4, 'count': 3}
    """
    uuids = []

    for _ in range(count):
        if version == 1:
            generated_uuid = uuid.uuid1()
        elif version == 3:
            # 版本3和5需要命名空间和名称，这里使用DNS命名空间作为示例
            generated_uuid = uuid.uuid3(uuid.NAMESPACE_DNS, str(uuid.uuid4()))
        elif version == 4:
            generated_uuid = uuid.uuid4()
        elif version == 5:
            generated_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, str(uuid.uuid4()))
        else:
            return {
                "uuids": [],
                "version": version,
                "count": 0,
                "error": f"不支持的UUID版本: {version}",
            }
        uuids.append(str(generated_uuid))

    return {
        "uuids": uuids,
        "version": version,
        "count": len(uuids),
    }


# =============================================================================
# 10. Cron表达式验证
# =============================================================================
def cron_validator(cron_expression):
    """
    验证Cron表达式的有效性并解析其含义。

    支持标准5字段Cron格式: 分 时 日 月 周

    Args:
        cron_expression (str): Cron表达式，例如 "0 2 * * *" 或 "*/15 8-18 * * 1-5"。

    Returns:
        dict: 包含以下键的字典:
            - "valid": 是否有效
            - "expression": 原始表达式
            - "fields": 各字段解析结果
            - "description": 人类可读的描述
            - "error": 错误信息（如有）

    Example:
        >>> result = cron_validator("0 2 * * *")
        {'valid': True, 'description': '每天 02:00 执行', ...}
    """
    # 各字段的范围
    field_ranges = [
        {"name": "分钟", "min": 0, "max": 59},
        {"name": "小时", "min": 0, "max": 23},
        {"name": "日", "min": 1, "max": 31},
        {"name": "月", "min": 1, "max": 12},
        {"name": "星期", "min": 0, "max": 7},  # 0和7都是周日
    ]

    field_names_cn = ["分钟", "小时", "日", "月", "星期"]
    weekday_names = ["周日", "周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    month_names = ["", "一月", "二月", "三月", "四月", "五月", "六月",
                   "七月", "八月", "九月", "十月", "十一月", "十二月"]

    parts = cron_expression.strip().split()

    if len(parts) != 5:
        return {
            "valid": False,
            "expression": cron_expression,
            "fields": [],
            "description": "",
            "error": f"Cron表达式需要5个字段，但得到{len(parts)}个",
        }

    fields = []
    descriptions = []
    valid = True
    error = None

    for i, (part, field_info) in enumerate(zip(parts, field_ranges)):
        field_name = field_info["name"]
        fmin = field_info["min"]
        fmax = field_info["max"]

        field_desc_parts = []

        if part == "*":
            field_desc_parts.append(f"每{field_name}")
            fields.append({"field": field_name, "value": part, "desc": f"每{field_name}"})
        elif part.startswith("*/"):
            # */n 表示每n个单位
            try:
                step = int(part[2:])
                if fmin <= step <= fmax:
                    field_desc_parts.append(f"每{step}{field_name}")
                    fields.append({"field": field_name, "value": part, "desc": f"每{step}{field_name}"})
                else:
                    valid = False
                    error = f"{field_name}步长超出范围: {step}"
                    fields.append({"field": field_name, "value": part, "desc": "无效"})
            except ValueError:
                valid = False
                error = f"{field_name}步长格式错误: {part}"
                fields.append({"field": field_name, "value": part, "desc": "无效"})
        else:
            # 处理逗号分隔、范围、单个值
            values = []
            desc_parts = []
            for item in part.split(","):
                item = item.strip()
                if "-" in item:
                    # 范围: 1-5
                    range_parts = item.split("-")
                    if len(range_parts) == 2:
                        try:
                            start = int(range_parts[0])
                            end = int(range_parts[1])
                            if fmin <= start <= fmax and fmin <= end <= fmax and start <= end:
                                values.extend(range(start, end + 1))
                                if i == 4:  # 星期
                                    desc_parts.append(f"{weekday_names[start]}至{weekday_names[end]}")
                                else:
                                    desc_parts.append(f"{start}-{end}")
                            else:
                                valid = False
                                error = f"{field_name}范围无效: {item}"
                        except ValueError:
                            valid = False
                            error = f"{field_name}范围格式错误: {item}"
                else:
                    try:
                        val = int(item)
                        if fmin <= val <= fmax:
                            values.append(val)
                            if i == 4:  # 星期
                                desc_parts.append(weekday_names[val])
                            elif i == 3:  # 月
                                desc_parts.append(month_names[val])
                            else:
                                desc_parts.append(str(val))
                        else:
                            valid = False
                            error = f"{field_name}值超出范围: {val} (有效范围: {fmin}-{fmax})"
                    except ValueError:
                        valid = False
                        error = f"{field_name}值格式错误: {item}"

            fields.append({
                "field": field_name,
                "value": part,
                "desc": "、".join(desc_parts) if desc_parts else part,
            })

    # 生成描述
    if valid:
        desc_parts = []
        minute_field = fields[0]
        hour_field = fields[1]
        day_field = fields[2]
        month_field = fields[3]
        weekday_field = fields[4]

        # 简单描述生成
        time_desc = ""
        if minute_field["value"] != "*":
            time_desc = f"{minute_field['desc']}"
        if hour_field["value"] != "*":
            time_desc = f"{hour_field['desc']}{minute_field['desc']}"

        frequency_desc = ""
        if weekday_field["value"] != "*" and day_field["value"] == "*":
            frequency_desc = f"每{weekday_field['desc']}"
        elif month_field["value"] != "*":
            frequency_desc = f"{month_field['desc']}"
        elif day_field["value"] != "*":
            frequency_desc = f"{month_field['desc']}{day_field['desc']}"
        else:
            frequency_desc = "每天"

        if time_desc:
            description = f"{frequency_desc} {time_desc}执行"
        else:
            description = f"{frequency_desc} 每分钟执行"
    else:
        description = ""

    return {
        "valid": valid,
        "expression": cron_expression,
        "fields": fields,
        "description": description,
        "error": error,
    }


# =============================================================================
# 主入口
# =============================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("开发编程工具箱 (code-toolkit)")
    print("=" * 60)
    print("可用工具:")
    tools = [
        "1. analyze_code_quality       - 代码质量分析",
        "2. format_sql                 - SQL格式化",
        "3. test_regex                 - 正则表达式测试",
        "4. generate_api_documentation - API文档生成",
        "5. code_complexity_analyzer   - 圈复杂度分析",
        "6. dependency_checker         - 依赖检查",
        "7. json_formatter             - JSON格式化/压缩",
        "8. base64_encoder_decoder     - Base64编解码",
        "9. uuid_generator             - UUID生成器",
        "10. cron_validator            - Cron表达式验证",
    ]
    for tool in tools:
        print(f"  {tool}")
    print("=" * 60)

    # 演示：UUID生成
    print("\n演示 - UUID生成:")
    uuid_result = uuid_generator(version=4, count=3)
    for i, u in enumerate(uuid_result["uuids"], 1):
        print(f"  UUID {i}: {u}")

    # 演示：JSON格式化
    print("\n演示 - JSON格式化:")
    json_result = json_formatter('{"name":"Alice","age":30}', indent=2)
    print(f"  有效: {json_result['is_valid']}")
    print(f"  格式化:\n{json_result['formatted']}")
