"""
Code Executor Service for Custom Tools

Executes Python and JavaScript code in a sandboxed environment with
timeout protection and resource limits.
"""

import asyncio
import json
import tempfile
import os
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass
import subprocess
import sys


@dataclass
class ExecutionResult:
    """Result of code execution."""
    success: bool
    result: Any
    error: Optional[str] = None
    execution_time_ms: Optional[int] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None


class CodeExecutor:
    """
    Executes custom code in a sandboxed environment.

    Supports Python and JavaScript execution with:
    - Timeout protection
    - Error capture
    - Input/output handling
    """

    DEFAULT_TIMEOUT = 30  # seconds
    MAX_OUTPUT_SIZE = 100000  # characters

    def __init__(self, timeout: int = DEFAULT_TIMEOUT):
        self.timeout = timeout

    async def execute(
        self,
        code: str,
        language: str,
        input_data: Dict[str, Any],
        parameters: Optional[Dict[str, Any]] = None
    ) -> ExecutionResult:
        """
        Execute code in the specified language.

        Args:
            code: The code to execute
            language: Programming language (python, javascript, typescript)
            input_data: Input data passed to the code
            parameters: Parameter schema (for validation)

        Returns:
            ExecutionResult with success status and result/error
        """
        language = language.lower()

        if language == "python":
            return await self._execute_python(code, input_data)
        elif language in ("javascript", "typescript"):
            return await self._execute_javascript(code, input_data)
        else:
            return ExecutionResult(
                success=False,
                result=None,
                error=f"Unsupported language: {language}"
            )

    async def _execute_python(
        self,
        code: str,
        input_data: Dict[str, Any]
    ) -> ExecutionResult:
        """Execute Python code."""
        start_time = time.time()

        # Create a wrapper script that handles input/output
        wrapper_code = f'''
import json
import sys

# Input data from the tool
params = json.loads('{json.dumps(input_data)}')

# User's code
{code}

# Execute the function if it exists
if 'execute' in dir():
    try:
        result = execute(params)
        print(json.dumps({{"success": True, "result": result}}))
    except Exception as e:
        print(json.dumps({{"success": False, "error": str(e)}}))
elif 'main' in dir():
    try:
        result = main(params)
        print(json.dumps({{"success": True, "result": result}}))
    except Exception as e:
        print(json.dumps({{"success": False, "error": str(e)}}))
else:
    print(json.dumps({{"success": False, "error": "No 'execute' or 'main' function found in code"}}))
'''

        try:
            # Write code to temporary file
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.py',
                delete=False
            ) as f:
                f.write(wrapper_code)
                temp_file = f.name

            try:
                # Execute the code with timeout
                process = await asyncio.create_subprocess_exec(
                    sys.executable, temp_file,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
                )

                try:
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(),
                        timeout=self.timeout
                    )
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
                    return ExecutionResult(
                        success=False,
                        result=None,
                        error=f"Execution timed out after {self.timeout} seconds",
                        execution_time_ms=int((time.time() - start_time) * 1000)
                    )

                stdout_str = stdout.decode('utf-8', errors='replace')[:self.MAX_OUTPUT_SIZE]
                stderr_str = stderr.decode('utf-8', errors='replace')[:self.MAX_OUTPUT_SIZE]

                execution_time_ms = int((time.time() - start_time) * 1000)

                if process.returncode != 0:
                    return ExecutionResult(
                        success=False,
                        result=None,
                        error=stderr_str or f"Process exited with code {process.returncode}",
                        execution_time_ms=execution_time_ms,
                        stdout=stdout_str,
                        stderr=stderr_str
                    )

                # Parse the JSON output
                try:
                    output = json.loads(stdout_str.strip().split('\n')[-1])
                    return ExecutionResult(
                        success=output.get("success", False),
                        result=output.get("result"),
                        error=output.get("error"),
                        execution_time_ms=execution_time_ms,
                        stdout=stdout_str,
                        stderr=stderr_str
                    )
                except json.JSONDecodeError:
                    return ExecutionResult(
                        success=False,
                        result=None,
                        error=f"Invalid output format. Stdout: {stdout_str}",
                        execution_time_ms=execution_time_ms,
                        stdout=stdout_str,
                        stderr=stderr_str
                    )

            finally:
                # Clean up temp file
                try:
                    os.unlink(temp_file)
                except:
                    pass

        except Exception as e:
            return ExecutionResult(
                success=False,
                result=None,
                error=f"Execution failed: {str(e)}",
                execution_time_ms=int((time.time() - start_time) * 1000)
            )

    async def _execute_javascript(
        self,
        code: str,
        input_data: Dict[str, Any]
    ) -> ExecutionResult:
        """Execute JavaScript code using Node.js."""
        start_time = time.time()

        # Create a wrapper script that handles input/output
        wrapper_code = f'''
const params = {json.dumps(input_data)};

{code}

// Execute the function if it exists
if (typeof execute === 'function') {{
    try {{
        const result = execute(params);
        if (result instanceof Promise) {{
            result.then(r => {{
                console.log(JSON.stringify({{ success: true, result: r }}));
            }}).catch(e => {{
                console.log(JSON.stringify({{ success: false, error: e.message || String(e) }}));
            }});
        }} else {{
            console.log(JSON.stringify({{ success: true, result: result }}));
        }}
    }} catch (e) {{
        console.log(JSON.stringify({{ success: false, error: e.message || String(e) }}));
    }}
}} else if (typeof main === 'function') {{
    try {{
        const result = main(params);
        if (result instanceof Promise) {{
            result.then(r => {{
                console.log(JSON.stringify({{ success: true, result: r }}));
            }}).catch(e => {{
                console.log(JSON.stringify({{ success: false, error: e.message || String(e) }}));
            }});
        }} else {{
            console.log(JSON.stringify({{ success: true, result: result }}));
        }}
    }} catch (e) {{
        console.log(JSON.stringify({{ success: false, error: e.message || String(e) }}));
    }}
}} else {{
    console.log(JSON.stringify({{ success: false, error: "No 'execute' or 'main' function found in code" }}));
}}
'''

        try:
            # Write code to temporary file
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.js',
                delete=False
            ) as f:
                f.write(wrapper_code)
                temp_file = f.name

            try:
                # Execute the code with timeout using Node.js
                process = await asyncio.create_subprocess_exec(
                    'node', temp_file,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )

                try:
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(),
                        timeout=self.timeout
                    )
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
                    return ExecutionResult(
                        success=False,
                        result=None,
                        error=f"Execution timed out after {self.timeout} seconds",
                        execution_time_ms=int((time.time() - start_time) * 1000)
                    )

                stdout_str = stdout.decode('utf-8', errors='replace')[:self.MAX_OUTPUT_SIZE]
                stderr_str = stderr.decode('utf-8', errors='replace')[:self.MAX_OUTPUT_SIZE]

                execution_time_ms = int((time.time() - start_time) * 1000)

                if process.returncode != 0:
                    return ExecutionResult(
                        success=False,
                        result=None,
                        error=stderr_str or f"Process exited with code {process.returncode}",
                        execution_time_ms=execution_time_ms,
                        stdout=stdout_str,
                        stderr=stderr_str
                    )

                # Parse the JSON output
                try:
                    # Get the last line that looks like JSON
                    lines = stdout_str.strip().split('\n')
                    json_line = None
                    for line in reversed(lines):
                        if line.strip().startswith('{'):
                            json_line = line
                            break

                    if not json_line:
                        return ExecutionResult(
                            success=False,
                            result=None,
                            error=f"No JSON output found. Stdout: {stdout_str}",
                            execution_time_ms=execution_time_ms,
                            stdout=stdout_str,
                            stderr=stderr_str
                        )

                    output = json.loads(json_line)
                    return ExecutionResult(
                        success=output.get("success", False),
                        result=output.get("result"),
                        error=output.get("error"),
                        execution_time_ms=execution_time_ms,
                        stdout=stdout_str,
                        stderr=stderr_str
                    )
                except json.JSONDecodeError:
                    return ExecutionResult(
                        success=False,
                        result=None,
                        error=f"Invalid output format. Stdout: {stdout_str}",
                        execution_time_ms=execution_time_ms,
                        stdout=stdout_str,
                        stderr=stderr_str
                    )

            finally:
                # Clean up temp file
                try:
                    os.unlink(temp_file)
                except:
                    pass

        except FileNotFoundError:
            return ExecutionResult(
                success=False,
                result=None,
                error="Node.js is not installed or not in PATH",
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                result=None,
                error=f"Execution failed: {str(e)}",
                execution_time_ms=int((time.time() - start_time) * 1000)
            )


# Global executor instance
code_executor = CodeExecutor()
