import ast

source_code = "x = 5 + 10"
tree = ast.parse(source_code)


# print(ast.dump(tree, indent=4))
print(ast.unparse(tree))
