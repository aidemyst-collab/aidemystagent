from typing import Dict, Any
import ast
import operator
from .base import BaseTool, ToolOutput


class CalculatorTool(BaseTool):
    """Calculator tool for mathematical operations."""

    def __init__(self):
        super().__init__(
            name="calculator",
            description="Perform mathematical calculations. Supports +, -, *, /, **, sqrt, and parentheses."
        )

        # Safe operators
        self.operators = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.Pow: operator.pow,
            ast.USub: operator.neg,
        }

    async def execute(self, input_data: Dict[str, Any]) -> ToolOutput:
        """Execute mathematical calculation."""
        try:
            expression = input_data.get("expression", "")

            if not expression:
                return ToolOutput(
                    success=False,
                    result=None,
                    error="No expression provided"
                )

            # Evaluate expression safely
            result = self._safe_eval(expression)

            return ToolOutput(
                success=True,
                result=result,
                error=None
            )

        except Exception as e:
            return ToolOutput(
                success=False,
                result=None,
                error=str(e)
            )

    def _safe_eval(self, expression: str) -> float:
        """Safely evaluate mathematical expression."""
        try:
            node = ast.parse(expression, mode='eval')
            return self._eval_node(node.body)
        except Exception as e:
            raise ValueError(f"Invalid expression: {e}")

    def _eval_node(self, node):
        """Recursively evaluate AST node."""
        if isinstance(node, ast.Num):
            return node.n
        elif isinstance(node, ast.BinOp):
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            return self.operators[type(node.op)](left, right)
        elif isinstance(node, ast.UnaryOp):
            operand = self._eval_node(node.operand)
            return self.operators[type(node.op)](operand)
        else:
            raise ValueError("Unsupported operation")

    def _get_parameters(self) -> Dict[str, Any]:
        """Get tool parameters schema."""
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Mathematical expression to evaluate"
                }
            },
            "required": ["expression"]
        }
