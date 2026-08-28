import ast

code = """\
x = 10

def calculate(a, b):
    result = a + b
    return result
"""

tree = ast.parse(code)

for node in ast.walk(tree):
    if isinstance(node, ast.Name):
        source = ast.get_source_segment(code, node)
        print(source)