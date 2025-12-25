"""
Template engine for resolving node references in workflow data.

This module provides Jinja2-based templating for data flow between nodes,
allowing nodes to reference outputs from previous nodes using template syntax.

Example:
    {{input-1.message}} - Reference message field from input-1 node
    {{llm-1.response}} - Reference response from llm-1 node
    {{tool-1.result.temperature}} - Access nested data
"""

from jinja2 import Environment, BaseLoader, TemplateSyntaxError, UndefinedError, StrictUndefined
from typing import Dict, Any, Optional, List
import json
import re
from app.core.logging_config import logger


class NodeTemplateEngine:
    """Template engine for resolving node references in workflow data."""

    def __init__(self):
        """Initialize the template engine with Jinja2 environment."""
        self.env = Environment(
            loader=BaseLoader(),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True
        )

        # Add custom filters
        self.env.filters['json'] = json.dumps
        self.env.filters['extract'] = self._extract_nested
        self.env.filters['default_if_none'] = lambda val, default: default if val is None else val

    def _extract_nested(self, obj: Any, path: str) -> Any:
        """
        Extract nested value using dot notation.

        Args:
            obj: The object to extract from
            path: Dot-separated path (e.g., "result.data.field")

        Returns:
            The extracted value or None if path doesn't exist
        """
        keys = path.split('.')
        result = obj
        for key in keys:
            if isinstance(result, dict):
                result = result.get(key)
                if result is None:
                    return None
            elif isinstance(result, list):
                try:
                    index = int(key)
                    result = result[index]
                except (ValueError, IndexError):
                    return None
            else:
                return None
        return result

    def resolve_template(
        self,
        template: str,
        context: Dict[str, Any],
        strict: bool = False
    ) -> str:
        """
        Resolve a template string using the context.

        Args:
            template: Template string with {{node_id.key}} references
            context: Dict of node_id -> output_data mappings
            strict: If True, raise error on undefined variables

        Returns:
            Resolved string

        Raises:
            ValueError: If template syntax is invalid or variables are undefined (in strict mode)

        Example:
            >>> engine = NodeTemplateEngine()
            >>> context = {"input-1": {"message": "Hello"}}
            >>> engine.resolve_template("User said: {{input-1.message}}", context)
            "User said: Hello"
        """
        try:
            if strict:
                self.env.undefined = StrictUndefined

            tmpl = self.env.from_string(template)
            result = tmpl.render(**context)

            # Reset to default undefined behavior
            if strict:
                from jinja2 import Undefined
                self.env.undefined = Undefined

            return result

        except TemplateSyntaxError as e:
            logger.error(f"Template syntax error: {e}")
            raise ValueError(f"Template syntax error: {e}")
        except UndefinedError as e:
            if strict:
                logger.error(f"Undefined variable in template: {e}")
                raise ValueError(f"Undefined variable in template: {e}")
            # In non-strict mode, return original template if resolution fails
            logger.warning(f"Could not resolve template (non-strict mode): {e}")
            return template

    def resolve_object(
        self,
        obj: Any,
        context: Dict[str, Any],
        strict: bool = False
    ) -> Any:
        """
        Recursively resolve templates in an object (dict, list, or string).

        Args:
            obj: Object to resolve (can be dict, list, str, or primitive)
            context: Context for template resolution
            strict: If True, raise error on undefined variables

        Returns:
            Object with all templates resolved

        Example:
            >>> engine = NodeTemplateEngine()
            >>> context = {"input-1": {"city": "SF", "temp": 72}}
            >>> obj = {"location": "{{input-1.city}}", "weather": {"temp": "{{input-1.temp}}"}}
            >>> engine.resolve_object(obj, context)
            {"location": "SF", "weather": {"temp": 72}}
        """
        if isinstance(obj, str):
            # Only resolve if it contains template markers
            if '{{' in obj and '}}' in obj:
                resolved = self.resolve_template(obj, context, strict)
                # Try to parse as JSON if the entire string is a template
                if obj.strip().startswith('{{') and obj.strip().endswith('}}'):
                    try:
                        # If resolved value is a number/bool/null, convert from string
                        if resolved.lower() in ('true', 'false'):
                            return resolved.lower() == 'true'
                        elif resolved.lower() == 'null':
                            return None
                        else:
                            # Try to convert to number
                            try:
                                if '.' in resolved:
                                    return float(resolved)
                                else:
                                    return int(resolved)
                            except ValueError:
                                return resolved
                    except:
                        pass
                return resolved
            return obj

        elif isinstance(obj, dict):
            return {
                key: self.resolve_object(value, context, strict)
                for key, value in obj.items()
            }

        elif isinstance(obj, list):
            return [
                self.resolve_object(item, context, strict)
                for item in obj
            ]

        else:
            # Primitive types (int, float, bool, None) pass through
            return obj

    def extract_dependencies(self, template: str) -> List[str]:
        """
        Extract node IDs that are referenced in a template.

        Args:
            template: Template string

        Returns:
            List of unique node IDs referenced in the template

        Example:
            >>> engine = NodeTemplateEngine()
            >>> engine.extract_dependencies("User {{input-1.name}} asked {{llm-1.question}}")
            ["input-1", "llm-1"]
        """
        # Match {{node_id.something}} or {{node_id}}
        pattern = r'\{\{([a-zA-Z0-9_-]+)(?:\.[^\}]+)?\}\}'
        matches = re.findall(pattern, template)
        return list(set(matches))

    def extract_object_dependencies(self, obj: Any) -> List[str]:
        """
        Extract all node dependencies from a complex object.

        Args:
            obj: Object to analyze (dict, list, str, etc.)

        Returns:
            List of unique node IDs referenced
        """
        dependencies = set()

        if isinstance(obj, str):
            dependencies.update(self.extract_dependencies(obj))
        elif isinstance(obj, dict):
            for value in obj.values():
                dependencies.update(self.extract_object_dependencies(value))
        elif isinstance(obj, list):
            for item in obj:
                dependencies.update(self.extract_object_dependencies(item))

        return list(dependencies)

    def validate_template(self, template: str) -> tuple[bool, Optional[str]]:
        """
        Validate template syntax without resolving it.

        Args:
            template: Template string to validate

        Returns:
            Tuple of (is_valid, error_message)

        Example:
            >>> engine = NodeTemplateEngine()
            >>> engine.validate_template("Hello {{name}}")
            (True, None)
            >>> engine.validate_template("Hello {{name")
            (False, "unexpected end of template")
        """
        try:
            self.env.from_string(template)
            return (True, None)
        except TemplateSyntaxError as e:
            return (False, str(e))


# Global instance
template_engine = NodeTemplateEngine()
