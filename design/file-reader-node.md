# File Reader Node Design

## Overview

Add a FILE_READER node that allows workflows to read files from the disk. This enables workflows to process files, extract data, and use file contents as input for downstream nodes.

**Inspired by:** [n8n Read/Write Files from Disk](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.readwritefile/)

---

## Use Cases

1. **Document Processing**: Read text files, PDFs, or documents for LLM analysis
2. **Configuration Loading**: Load JSON/YAML config files for workflow parameters
3. **Data Import**: Read CSV, JSON, or other data files for processing
4. **Log Analysis**: Read log files for monitoring and analysis
5. **Template Loading**: Read template files for dynamic content generation
6. **Image Processing**: Read images for computer vision workflows

---

## Node Type Definition

### Node Type: `FILE_READER`

**Category:** Data Input
**Icon:** 📁 (File/Folder icon)
**Color:** Blue (#3B82F6)

---

## Configuration Options

### 1. **File Path** (Required)
- **Type:** String (supports templates)
- **Description:** Path to the file to read
- **Examples:**
  - Absolute path: `/var/data/documents/report.pdf`
  - Relative path: `./data/config.json`
  - Template: `{{input-1.file_path}}`
  - Environment variable: `${DATA_DIR}/file.txt`
- **Validation:**
  - Must not be empty
  - File must exist and be readable
  - Path traversal protection (prevent `../` attacks)

### 2. **File Operation** (Required)
- **Type:** Select
- **Options:**
  - `read_text` - Read file as text (default)
  - `read_binary` - Read file as binary data
  - `read_json` - Read and parse JSON file
  - `read_csv` - Read and parse CSV file
  - `read_lines` - Read file as array of lines
  - `get_metadata` - Get file metadata only (size, modified date, etc.)
- **Default:** `read_text`

### 3. **Encoding** (for text operations)
- **Type:** Select
- **Options:**
  - `utf-8` (default)
  - `utf-16`
  - `ascii`
  - `latin1`
  - `base64`
- **Default:** `utf-8`
- **Applies to:** `read_text`, `read_json`, `read_csv`, `read_lines`

### 4. **Max File Size** (Optional)
- **Type:** Number (in MB)
- **Default:** 10 MB
- **Range:** 1 MB - 100 MB
- **Description:** Maximum file size to read (prevents memory issues)

### 5. **Error Handling** (Required)
- **Type:** Select
- **Options:**
  - `fail` - Stop workflow execution on error (default)
  - `continue` - Continue with empty result and log error
  - `default_value` - Use default value on error
- **Default:** `fail`

### 6. **Default Value** (Optional)
- **Type:** Text Area
- **Description:** Value to use if file cannot be read (when error handling = `default_value`)
- **Applies when:** Error Handling = `default_value`

### 7. **CSV Options** (when operation = `read_csv`)
- **Delimiter:** String (default: `,`)
- **Has Header:** Boolean (default: `true`)
- **Skip Empty Lines:** Boolean (default: `true`)
- **Trim Fields:** Boolean (default: `true`)

### 8. **JSON Options** (when operation = `read_json`)
- **Validate Schema:** Boolean (default: `false`)
- **JSON Schema:** Text Area (optional JSON schema for validation)

### 9. **Line Reading Options** (when operation = `read_lines`)
- **Skip Empty Lines:** Boolean (default: `true`)
- **Trim Lines:** Boolean (default: `true`)
- **Start Line:** Number (optional, 1-indexed)
- **End Line:** Number (optional, 1-indexed)

### 10. **Output Variable Name** (Optional)
- **Type:** String
- **Default:** `file_content`
- **Description:** Custom name for the output field
- **Pattern:** `^[a-zA-Z_][a-zA-Z0-9_]*$`

---

## Security Considerations

### Path Restrictions
1. **Whitelist Directories:** Only allow reading from configured safe directories
2. **Path Traversal Prevention:** Validate and sanitize paths to prevent `../` attacks
3. **Symbolic Link Handling:** Option to follow or reject symbolic links
4. **Hidden Files:** Option to allow/deny hidden file access (files starting with `.`)

### Configuration (Backend)
```python
# backend/app/core/config.py
class Settings:
    # File Reader Security Settings
    FILE_READER_ALLOWED_DIRS: List[str] = [
        "/var/data",
        "/app/data",
        "./uploads",
        "${WORKFLOW_DATA_DIR}"  # Environment variable
    ]
    FILE_READER_MAX_FILE_SIZE_MB: int = 100
    FILE_READER_FOLLOW_SYMLINKS: bool = False
    FILE_READER_ALLOW_HIDDEN_FILES: bool = False
    FILE_READER_TIMEOUT_SECONDS: int = 30
```

### Permissions
- Workflow must have `file_read` permission
- Organization-level restrictions can be configured
- Audit logging for all file access operations

---

## Output Schema

### Output Structure

#### For `read_text` operation:
```json
{
  "file_content": "text content here...",
  "file_path": "/var/data/file.txt",
  "file_size": 1024,
  "encoding": "utf-8",
  "read_time_ms": 15,
  "metadata": {
    "modified": "2025-12-02T10:30:00Z",
    "created": "2025-12-01T08:00:00Z",
    "size_bytes": 1024,
    "mime_type": "text/plain"
  }
}
```

#### For `read_json` operation:
```json
{
  "data": { /* parsed JSON content */ },
  "file_path": "/var/data/config.json",
  "file_size": 512,
  "encoding": "utf-8",
  "read_time_ms": 8,
  "metadata": { /* ... */ }
}
```

#### For `read_csv` operation:
```json
{
  "rows": [
    {"column1": "value1", "column2": "value2"},
    {"column1": "value3", "column2": "value4"}
  ],
  "headers": ["column1", "column2"],
  "row_count": 2,
  "file_path": "/var/data/data.csv",
  "read_time_ms": 20,
  "metadata": { /* ... */ }
}
```

#### For `read_lines` operation:
```json
{
  "lines": ["line 1", "line 2", "line 3"],
  "line_count": 3,
  "file_path": "/var/data/log.txt",
  "read_time_ms": 12,
  "metadata": { /* ... */ }
}
```

#### For `read_binary` operation:
```json
{
  "file_content": "base64_encoded_binary_data_here...",
  "file_path": "/var/data/image.png",
  "file_size": 204800,
  "encoding": "base64",
  "read_time_ms": 25,
  "metadata": {
    "modified": "2025-12-02T10:30:00Z",
    "size_bytes": 204800,
    "mime_type": "image/png"
  }
}
```

#### For `get_metadata` operation:
```json
{
  "file_path": "/var/data/document.pdf",
  "file_exists": true,
  "is_file": true,
  "is_directory": false,
  "size_bytes": 1048576,
  "size_readable": "1.0 MB",
  "modified": "2025-12-02T10:30:00Z",
  "created": "2025-12-01T08:00:00Z",
  "accessed": "2025-12-02T15:00:00Z",
  "mime_type": "application/pdf",
  "extension": ".pdf",
  "permissions": "rw-r--r--",
  "owner": "user",
  "is_readable": true,
  "is_writable": false
}
```

### Error Output (when error handling = `continue`):
```json
{
  "file_content": null,
  "file_path": "/var/data/missing.txt",
  "error": "File not found",
  "error_code": "FILE_NOT_FOUND",
  "success": false
}
```

---

## Implementation Plan

### Phase 1: Backend Implementation

#### 1.1 Add File Reader Service

**File:** `backend/app/services/file_reader.py` (NEW)

```python
"""
File Reader Service for reading files from disk with security controls
"""
import os
import json
import csv
import mimetypes
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import aiofiles
import base64

from app.core.config import settings
from app.core.exceptions import FileReaderError


class FileReaderService:
    """Service for secure file reading operations"""

    def __init__(self):
        self.allowed_dirs = self._parse_allowed_dirs()
        self.max_file_size_bytes = settings.FILE_READER_MAX_FILE_SIZE_MB * 1024 * 1024
        self.follow_symlinks = settings.FILE_READER_FOLLOW_SYMLINKS
        self.allow_hidden = settings.FILE_READER_ALLOW_HIDDEN_FILES

    def _parse_allowed_dirs(self) -> List[Path]:
        """Parse and expand environment variables in allowed directories"""
        dirs = []
        for dir_path in settings.FILE_READER_ALLOWED_DIRS:
            # Expand environment variables
            expanded = os.path.expandvars(dir_path)
            # Convert to absolute path
            abs_path = Path(expanded).resolve()
            dirs.append(abs_path)
        return dirs

    def _validate_path(self, file_path: str) -> Path:
        """
        Validate file path for security

        Raises:
            FileReaderError: If path is invalid or not allowed
        """
        # Resolve path (handles . and ..)
        path = Path(file_path).resolve()

        # Check if path is within allowed directories
        is_allowed = False
        for allowed_dir in self.allowed_dirs:
            try:
                path.relative_to(allowed_dir)
                is_allowed = True
                break
            except ValueError:
                continue

        if not is_allowed:
            raise FileReaderError(
                f"File path '{file_path}' is not within allowed directories",
                error_code="PATH_NOT_ALLOWED"
            )

        # Check if file exists
        if not path.exists():
            raise FileReaderError(
                f"File not found: {file_path}",
                error_code="FILE_NOT_FOUND"
            )

        # Check if it's a file (not directory)
        if path.is_dir():
            raise FileReaderError(
                f"Path is a directory, not a file: {file_path}",
                error_code="IS_DIRECTORY"
            )

        # Check symbolic links
        if path.is_symlink() and not self.follow_symlinks:
            raise FileReaderError(
                f"Symbolic links are not allowed: {file_path}",
                error_code="SYMLINK_NOT_ALLOWED"
            )

        # Check hidden files
        if not self.allow_hidden and path.name.startswith('.'):
            raise FileReaderError(
                f"Hidden files are not allowed: {file_path}",
                error_code="HIDDEN_FILE_NOT_ALLOWED"
            )

        # Check file size
        file_size = path.stat().st_size
        if file_size > self.max_file_size_bytes:
            raise FileReaderError(
                f"File size ({file_size} bytes) exceeds maximum allowed "
                f"({self.max_file_size_bytes} bytes)",
                error_code="FILE_TOO_LARGE"
            )

        # Check read permissions
        if not os.access(path, os.R_OK):
            raise FileReaderError(
                f"File is not readable: {file_path}",
                error_code="FILE_NOT_READABLE"
            )

        return path

    async def get_file_metadata(self, file_path: str) -> Dict[str, Any]:
        """Get file metadata without reading content"""
        path = self._validate_path(file_path)
        stat = path.stat()

        mime_type, _ = mimetypes.guess_type(str(path))

        return {
            "file_path": str(path),
            "file_exists": True,
            "is_file": path.is_file(),
            "is_directory": path.is_dir(),
            "size_bytes": stat.st_size,
            "size_readable": self._format_size(stat.st_size),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "accessed": datetime.fromtimestamp(stat.st_atime).isoformat(),
            "mime_type": mime_type or "application/octet-stream",
            "extension": path.suffix,
            "permissions": oct(stat.st_mode)[-3:],
            "is_readable": os.access(path, os.R_OK),
            "is_writable": os.access(path, os.W_OK),
        }

    async def read_text(
        self,
        file_path: str,
        encoding: str = "utf-8"
    ) -> Dict[str, Any]:
        """Read file as text"""
        start_time = datetime.now()
        path = self._validate_path(file_path)

        async with aiofiles.open(path, mode='r', encoding=encoding) as f:
            content = await f.read()

        metadata = await self.get_file_metadata(file_path)
        read_time_ms = (datetime.now() - start_time).total_seconds() * 1000

        return {
            "file_content": content,
            "file_path": str(path),
            "file_size": len(content),
            "encoding": encoding,
            "read_time_ms": round(read_time_ms, 2),
            "metadata": metadata,
        }

    async def read_binary(self, file_path: str) -> Dict[str, Any]:
        """Read file as binary (returns base64 encoded)"""
        start_time = datetime.now()
        path = self._validate_path(file_path)

        async with aiofiles.open(path, mode='rb') as f:
            content = await f.read()

        # Encode to base64 for JSON serialization
        encoded_content = base64.b64encode(content).decode('utf-8')

        metadata = await self.get_file_metadata(file_path)
        read_time_ms = (datetime.now() - start_time).total_seconds() * 1000

        return {
            "file_content": encoded_content,
            "file_path": str(path),
            "file_size": len(content),
            "encoding": "base64",
            "read_time_ms": round(read_time_ms, 2),
            "metadata": metadata,
        }

    async def read_json(
        self,
        file_path: str,
        encoding: str = "utf-8",
        validate_schema: bool = False,
        schema: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Read and parse JSON file"""
        start_time = datetime.now()
        path = self._validate_path(file_path)

        async with aiofiles.open(path, mode='r', encoding=encoding) as f:
            content = await f.read()

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise FileReaderError(
                f"Invalid JSON in file: {str(e)}",
                error_code="INVALID_JSON"
            )

        # TODO: Add JSON schema validation if needed
        if validate_schema and schema:
            # Use jsonschema library for validation
            pass

        metadata = await self.get_file_metadata(file_path)
        read_time_ms = (datetime.now() - start_time).total_seconds() * 1000

        return {
            "data": data,
            "file_path": str(path),
            "file_size": len(content),
            "encoding": encoding,
            "read_time_ms": round(read_time_ms, 2),
            "metadata": metadata,
        }

    async def read_csv(
        self,
        file_path: str,
        encoding: str = "utf-8",
        delimiter: str = ",",
        has_header: bool = True,
        skip_empty_lines: bool = True,
        trim_fields: bool = True
    ) -> Dict[str, Any]:
        """Read and parse CSV file"""
        start_time = datetime.now()
        path = self._validate_path(file_path)

        async with aiofiles.open(path, mode='r', encoding=encoding) as f:
            content = await f.read()

        lines = content.split('\n')
        if skip_empty_lines:
            lines = [line for line in lines if line.strip()]

        reader = csv.reader(lines, delimiter=delimiter)
        rows_list = list(reader)

        if not rows_list:
            return {
                "rows": [],
                "headers": [],
                "row_count": 0,
                "file_path": str(path),
                "read_time_ms": 0,
            }

        headers = None
        data_rows = rows_list

        if has_header:
            headers = rows_list[0]
            data_rows = rows_list[1:]

            if trim_fields:
                headers = [h.strip() for h in headers]

        # Convert to list of dicts if we have headers
        if headers:
            rows = []
            for row in data_rows:
                if trim_fields:
                    row = [field.strip() for field in row]
                row_dict = dict(zip(headers, row))
                rows.append(row_dict)
        else:
            rows = data_rows
            if trim_fields:
                rows = [[field.strip() for field in row] for row in rows]

        metadata = await self.get_file_metadata(file_path)
        read_time_ms = (datetime.now() - start_time).total_seconds() * 1000

        return {
            "rows": rows,
            "headers": headers or [],
            "row_count": len(rows),
            "file_path": str(path),
            "read_time_ms": round(read_time_ms, 2),
            "metadata": metadata,
        }

    async def read_lines(
        self,
        file_path: str,
        encoding: str = "utf-8",
        skip_empty_lines: bool = True,
        trim_lines: bool = True,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None
    ) -> Dict[str, Any]:
        """Read file as array of lines"""
        start_time = datetime.now()
        path = self._validate_path(file_path)

        async with aiofiles.open(path, mode='r', encoding=encoding) as f:
            content = await f.read()

        lines = content.split('\n')

        if skip_empty_lines:
            lines = [line for line in lines if line.strip()]

        if trim_lines:
            lines = [line.strip() for line in lines]

        # Apply line range if specified (1-indexed)
        if start_line is not None:
            start_idx = max(0, start_line - 1)
            lines = lines[start_idx:]

        if end_line is not None:
            end_idx = end_line
            lines = lines[:end_idx]

        metadata = await self.get_file_metadata(file_path)
        read_time_ms = (datetime.now() - start_time).total_seconds() * 1000

        return {
            "lines": lines,
            "line_count": len(lines),
            "file_path": str(path),
            "read_time_ms": round(read_time_ms, 2),
            "metadata": metadata,
        }

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format bytes to human readable size"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"


# Custom exception
class FileReaderError(Exception):
    """Exception raised for file reader errors"""

    def __init__(self, message: str, error_code: str = "FILE_READER_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


# Singleton instance
file_reader_service = FileReaderService()
```

#### 1.2 Add File Reader Node Handler to LangGraph Engine

**File:** `backend/app/services/langgraph_engine.py` (UPDATE)

Add the FILE_READER node handler:

```python
async def _handle_file_reader_node(self, state: AgentState) -> AgentState:
    """
    Handle FILE_READER node - read files from disk
    """
    from app.services.file_reader import file_reader_service, FileReaderError

    start_time = datetime.utcnow()
    node_id = state["current_node"]
    agent_config = state["agent_config"]

    # Find the FILE_READER node config
    file_reader_config = None
    for node in agent_config.get("nodes", []):
        if node["id"] == node_id and node["data"]["type"] == "FILE_READER":
            file_reader_config = node["data"].get("config", {})
            break

    if not file_reader_config:
        raise ValueError(f"FILE_READER node {node_id} not found in config")

    # Extract configuration
    file_path = file_reader_config.get("filePath", "")
    operation = file_reader_config.get("operation", "read_text")
    encoding = file_reader_config.get("encoding", "utf-8")
    error_handling = file_reader_config.get("errorHandling", "fail")
    default_value = file_reader_config.get("defaultValue", "")
    output_var_name = file_reader_config.get("outputVarName", "file_content")

    # Resolve templates in file path
    template_engine = NodeTemplateEngine()
    context = state.get("node_outputs", {})
    if "{{" in file_path:
        file_path = template_engine.resolve_template(file_path, context)

    # Capture input
    input_snapshot = {
        "file_path": file_path,
        "operation": operation,
        "encoding": encoding,
    }

    try:
        # Execute file operation
        if operation == "read_text":
            result = await file_reader_service.read_text(file_path, encoding)
        elif operation == "read_binary":
            result = await file_reader_service.read_binary(file_path)
        elif operation == "read_json":
            validate_schema = file_reader_config.get("validateSchema", False)
            json_schema = file_reader_config.get("jsonSchema")
            result = await file_reader_service.read_json(
                file_path, encoding, validate_schema, json_schema
            )
        elif operation == "read_csv":
            result = await file_reader_service.read_csv(
                file_path=file_path,
                encoding=encoding,
                delimiter=file_reader_config.get("csvDelimiter", ","),
                has_header=file_reader_config.get("csvHasHeader", True),
                skip_empty_lines=file_reader_config.get("csvSkipEmpty", True),
                trim_fields=file_reader_config.get("csvTrimFields", True),
            )
        elif operation == "read_lines":
            result = await file_reader_service.read_lines(
                file_path=file_path,
                encoding=encoding,
                skip_empty_lines=file_reader_config.get("linesSkipEmpty", True),
                trim_lines=file_reader_config.get("linesTrim", True),
                start_line=file_reader_config.get("linesStart"),
                end_line=file_reader_config.get("linesEnd"),
            )
        elif operation == "get_metadata":
            result = await file_reader_service.get_file_metadata(file_path)
        else:
            raise ValueError(f"Unknown operation: {operation}")

        result["success"] = True
        output_snapshot = result
        status = "success"
        error_msg = None

    except FileReaderError as e:
        # Handle file reader specific errors
        if error_handling == "fail":
            raise
        elif error_handling == "default_value":
            result = {output_var_name: default_value, "success": False, "error": str(e)}
        else:  # continue
            result = {output_var_name: None, "success": False, "error": str(e)}

        output_snapshot = result
        status = "error"
        error_msg = str(e)

    except Exception as e:
        if error_handling == "fail":
            raise
        result = {output_var_name: None, "success": False, "error": str(e)}
        output_snapshot = result
        status = "error"
        error_msg = str(e)

    # Store node output
    state["node_outputs"][node_id] = result

    # Add execution trace
    duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
    state["execution_trace"].append({
        "node_id": node_id,
        "node_type": "FILE_READER",
        "node_label": file_reader_config.get("label", "File Reader"),
        "input_data": input_snapshot,
        "output_data": output_snapshot,
        "timestamp": start_time.isoformat(),
        "duration_ms": round(duration_ms, 2),
        "status": status,
        "error": error_msg,
    })

    # Determine next node
    next_node = self._get_next_node(state, node_id)
    state["current_node"] = next_node
    state["execution_path"].append("FILE_READER")

    return state
```

#### 1.3 Update LangGraph Workflow Builder

**File:** `backend/app/services/langgraph_engine.py` (UPDATE)

Add FILE_READER to workflow builder:

```python
# In _build_workflow method, add:
if node_type == "FILE_READER":
    workflow.add_node("FILE_READER", self._handle_file_reader_node)
```

#### 1.4 Update Configuration

**File:** `backend/app/core/config.py` (UPDATE)

```python
class Settings(BaseSettings):
    # ... existing settings ...

    # File Reader Settings
    FILE_READER_ALLOWED_DIRS: List[str] = Field(
        default=["/var/data", "./data", "./uploads"],
        env="FILE_READER_ALLOWED_DIRS"
    )
    FILE_READER_MAX_FILE_SIZE_MB: int = Field(default=10, env="FILE_READER_MAX_FILE_SIZE_MB")
    FILE_READER_FOLLOW_SYMLINKS: bool = Field(default=False, env="FILE_READER_FOLLOW_SYMLINKS")
    FILE_READER_ALLOW_HIDDEN_FILES: bool = Field(default=False, env="FILE_READER_ALLOW_HIDDEN_FILES")
    FILE_READER_TIMEOUT_SECONDS: int = Field(default=30, env="FILE_READER_TIMEOUT_SECONDS")
```

#### 1.5 Add Dependencies

**File:** `backend/requirements.txt` (UPDATE)

```
aiofiles==23.2.1
python-magic==0.4.27  # For better MIME type detection
```

---

### Phase 2: Frontend Implementation

#### 2.1 Update Node Types

**File:** `frontend/src/types/workflow.ts` (UPDATE)

```typescript
export type NodeType =
  | 'INPUT'
  | 'MEMORY'
  | 'LLM_AGENT'
  | 'RAG_RETRIEVER'
  | 'DECISION'
  | 'TOOL'
  | 'OUTPUT'
  | 'SUBGRAPH'
  | 'FILE_READER';  // NEW

export interface FileReaderNodeConfig {
  filePath: string;
  operation: 'read_text' | 'read_binary' | 'read_json' | 'read_csv' | 'read_lines' | 'get_metadata';
  encoding?: string;
  maxFileSizeMB?: number;
  errorHandling: 'fail' | 'continue' | 'default_value';
  defaultValue?: string;
  outputVarName?: string;

  // CSV Options
  csvDelimiter?: string;
  csvHasHeader?: boolean;
  csvSkipEmpty?: boolean;
  csvTrimFields?: boolean;

  // JSON Options
  validateSchema?: boolean;
  jsonSchema?: string;

  // Line Reading Options
  linesSkipEmpty?: boolean;
  linesTrim?: boolean;
  linesStart?: number;
  linesEnd?: number;
}

export type NodeConfig =
  | InputNodeConfig
  | LLMAgentNodeConfig
  | RAGRetrieverNodeConfig
  | DecisionNodeConfig
  | ToolNodeConfig
  | OutputNodeConfig
  | SubgraphNodeConfig
  | FileReaderNodeConfig;  // NEW
```

#### 2.2 Update Node Schemas

**File:** `frontend/src/types/nodeSchemas.ts` (UPDATE)

```typescript
export const NODE_SCHEMAS: Record<string, NodeSchema> = {
  // ... existing schemas ...

  FILE_READER: {
    inputs: [
      { name: 'file_path', type: 'string', description: 'Path to the file (can be templated)' },
    ],
    outputs: [
      { name: 'file_content', type: 'string', description: 'File content or parsed data', required: true },
      { name: 'file_path', type: 'string', description: 'Resolved file path' },
      { name: 'file_size', type: 'number', description: 'File size in bytes' },
      { name: 'metadata', type: 'object', description: 'File metadata' },
      { name: 'success', type: 'boolean', description: 'Whether operation succeeded' },
      { name: 'error', type: 'string', description: 'Error message if failed' },
    ],
    customizable: false,
  },
};
```

#### 2.3 Create File Reader Node Component

**File:** `frontend/src/components/AgentBuilder/nodes/FileReaderNode.tsx` (NEW)

```typescript
import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { FileTextOutlined } from '@ant-design/icons';
import { BaseNode } from './BaseNode';
import type { NodeProps } from '@xyflow/react';

export const FileReaderNode = memo(({ data, selected }: NodeProps) => {
  const config = data.config || {};
  const operation = config.operation || 'read_text';

  return (
    <BaseNode
      icon={<FileTextOutlined style={{ fontSize: 24 }} />}
      title={data.label || 'File Reader'}
      subtitle={operation.replace('_', ' ').toUpperCase()}
      selected={selected}
      color="#3B82F6"
    >
      <Handle
        type="target"
        position={Position.Left}
        style={{ background: '#3B82F6' }}
      />
      <div style={{ fontSize: 10, color: '#666', marginTop: 4 }}>
        {config.filePath ? (
          <div style={{
            maxWidth: 150,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap'
          }}>
            📁 {config.filePath}
          </div>
        ) : (
          '⚠️ No file path configured'
        )}
      </div>
      <Handle
        type="source"
        position={Position.Right}
        style={{ background: '#3B82F6' }}
      />
    </BaseNode>
  );
});

FileReaderNode.displayName = 'FileReaderNode';
```

#### 2.4 Update Node Library

**File:** `frontend/src/components/AgentBuilder/NodeLibrary.tsx` (UPDATE)

Add FILE_READER to the node library:

```typescript
const nodeTypes = [
  // ... existing nodes ...
  {
    type: 'FILE_READER',
    label: 'File Reader',
    icon: <FileTextOutlined />,
    description: 'Read files from disk',
    category: 'Data Input',
  },
];
```

#### 2.5 Update PropertyPanel

**File:** `frontend/src/components/AgentBuilder/PropertyPanel.tsx` (UPDATE)

Add FILE_READER configuration section:

```typescript
{selectedNode.data.type === 'FILE_READER' && (
  <>
    <Typography.Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 8 }}>
      Read files from the server filesystem with configurable options
    </Typography.Text>

    <Form.Item
      name={['config', 'filePath']}
      label="File Path"
      rules={[{ required: true, message: 'Please enter file path' }]}
      tooltip="Absolute or relative path to the file. Supports templates like {{input-1.path}}"
    >
      <TemplateHelper
        value={form.getFieldValue(['config', 'filePath']) || ''}
        onChange={(value) => form.setFieldValue(['config', 'filePath'], value)}
        availableNodes={getUpstreamNodes(selectedNode)}
        placeholder="/var/data/file.txt or {{input-1.file_path}}"
        rows={2}
      />
    </Form.Item>

    <Form.Item
      name={['config', 'operation']}
      label="File Operation"
      initialValue="read_text"
      rules={[{ required: true, message: 'Please select operation' }]}
    >
      <Select
        options={[
          { label: 'Read as Text', value: 'read_text' },
          { label: 'Read as Binary (Base64)', value: 'read_binary' },
          { label: 'Read & Parse JSON', value: 'read_json' },
          { label: 'Read & Parse CSV', value: 'read_csv' },
          { label: 'Read as Lines', value: 'read_lines' },
          { label: 'Get Metadata Only', value: 'get_metadata' },
        ]}
      />
    </Form.Item>

    <Form.Item noStyle shouldUpdate>
      {() => {
        const operation = form.getFieldValue(['config', 'operation']) || 'read_text';
        const isTextOperation = ['read_text', 'read_json', 'read_csv', 'read_lines'].includes(operation);

        return (
          <>
            {isTextOperation && (
              <Form.Item name={['config', 'encoding']} label="Encoding" initialValue="utf-8">
                <Select
                  options={[
                    { label: 'UTF-8', value: 'utf-8' },
                    { label: 'UTF-16', value: 'utf-16' },
                    { label: 'ASCII', value: 'ascii' },
                    { label: 'Latin1', value: 'latin1' },
                  ]}
                />
              </Form.Item>
            )}

            {operation === 'read_csv' && (
              <Card size="small" title="CSV Options" className="mb-3">
                <Form.Item name={['config', 'csvDelimiter']} label="Delimiter" initialValue=",">
                  <Input placeholder="," />
                </Form.Item>
                <Form.Item name={['config', 'csvHasHeader']} valuePropName="checked" initialValue={true}>
                  <Checkbox>First row is header</Checkbox>
                </Form.Item>
                <Form.Item name={['config', 'csvSkipEmpty']} valuePropName="checked" initialValue={true}>
                  <Checkbox>Skip empty lines</Checkbox>
                </Form.Item>
                <Form.Item name={['config', 'csvTrimFields']} valuePropName="checked" initialValue={true}>
                  <Checkbox>Trim field whitespace</Checkbox>
                </Form.Item>
              </Card>
            )}

            {operation === 'read_json' && (
              <Card size="small" title="JSON Options" className="mb-3">
                <Form.Item name={['config', 'validateSchema']} valuePropName="checked" initialValue={false}>
                  <Checkbox>Validate against JSON schema</Checkbox>
                </Form.Item>
                {form.getFieldValue(['config', 'validateSchema']) && (
                  <Form.Item name={['config', 'jsonSchema']} label="JSON Schema">
                    <TextArea rows={6} placeholder="Enter JSON schema..." />
                  </Form.Item>
                )}
              </Card>
            )}

            {operation === 'read_lines' && (
              <Card size="small" title="Line Options" className="mb-3">
                <Form.Item name={['config', 'linesSkipEmpty']} valuePropName="checked" initialValue={true}>
                  <Checkbox>Skip empty lines</Checkbox>
                </Form.Item>
                <Form.Item name={['config', 'linesTrim']} valuePropName="checked" initialValue={true}>
                  <Checkbox>Trim line whitespace</Checkbox>
                </Form.Item>
                <Form.Item name={['config', 'linesStart']} label="Start Line (optional)">
                  <InputNumber min={1} style={{ width: '100%' }} placeholder="1" />
                </Form.Item>
                <Form.Item name={['config', 'linesEnd']} label="End Line (optional)">
                  <InputNumber min={1} style={{ width: '100%' }} placeholder="100" />
                </Form.Item>
              </Card>
            )}
          </>
        );
      }}
    </Form.Item>

    <Card size="small" title="Error Handling" className="mb-3">
      <Form.Item
        name={['config', 'errorHandling']}
        label="On Error"
        initialValue="fail"
        rules={[{ required: true }]}
      >
        <Select
          options={[
            { label: 'Fail Workflow', value: 'fail' },
            { label: 'Continue with Empty Result', value: 'continue' },
            { label: 'Use Default Value', value: 'default_value' },
          ]}
        />
      </Form.Item>

      {form.getFieldValue(['config', 'errorHandling']) === 'default_value' && (
        <Form.Item name={['config', 'defaultValue']} label="Default Value">
          <TextArea rows={3} placeholder="Value to use if file cannot be read..." />
        </Form.Item>
      )}
    </Card>

    <Form.Item name={['config', 'maxFileSizeMB']} label="Max File Size (MB)" initialValue={10}>
      <InputNumber min={1} max={100} style={{ width: '100%' }} />
    </Form.Item>

    <Form.Item
      name={['config', 'outputVarName']}
      label="Output Variable Name"
      initialValue="file_content"
      tooltip="Custom name for the output field in node outputs"
    >
      <Input placeholder="file_content" />
    </Form.Item>
  </>
)}
```

#### 2.6 Update Node Types Export

**File:** `frontend/src/components/AgentBuilder/nodes/index.ts` (UPDATE)

```typescript
export { FileReaderNode } from './FileReaderNode';
```

#### 2.7 Update AgentCanvas

**File:** `frontend/src/components/AgentBuilder/AgentCanvas.tsx` (UPDATE)

```typescript
import {
  // ... existing imports
  FileReaderNode,
} from './nodes';

const nodeTypes: NodeTypes = {
  // ... existing types
  FileReaderNode,
};

const nodeTypeMapping: Record<string, string> = {
  // ... existing mappings
  'FILE_READER': 'FileReaderNode',
};
```

---

## Testing Plan

### Unit Tests

**File:** `backend/tests/test_file_reader.py` (NEW)

```python
import pytest
from app.services.file_reader import file_reader_service, FileReaderError


@pytest.mark.asyncio
async def test_read_text_file():
    """Test reading a text file"""
    # Create test file
    test_file = "/tmp/test.txt"
    with open(test_file, 'w') as f:
        f.write("Hello, World!")

    result = await file_reader_service.read_text(test_file)

    assert result["file_content"] == "Hello, World!"
    assert result["success"] is True
    assert "metadata" in result


@pytest.mark.asyncio
async def test_read_json_file():
    """Test reading and parsing JSON file"""
    # Test implementation
    pass


@pytest.mark.asyncio
async def test_path_validation():
    """Test path security validation"""
    with pytest.raises(FileReaderError):
        await file_reader_service.read_text("../../etc/passwd")


@pytest.mark.asyncio
async def test_file_size_limit():
    """Test file size limit enforcement"""
    # Test implementation
    pass
```

### Integration Tests

1. Create workflow with FILE_READER node
2. Read text file and pass to LLM
3. Read CSV and process data
4. Test error handling modes
5. Test template resolution in file paths

---

## Security Checklist

- [ ] Path traversal prevention
- [ ] File size limits enforced
- [ ] Allowed directories whitelist
- [ ] Symbolic link handling
- [ ] Hidden file restrictions
- [ ] Audit logging for file access
- [ ] Permission checks
- [ ] Timeout enforcement
- [ ] MIME type validation
- [ ] Binary file handling (base64 encoding)

---

## Documentation

### User Guide

**Example 1: Read JSON Configuration**
```
Node: FILE_READER
- File Path: /var/data/config.json
- Operation: Read & Parse JSON
- Error Handling: Fail Workflow
```

**Example 2: Process CSV Data**
```
Node: FILE_READER
- File Path: {{input-1.csv_path}}
- Operation: Read & Parse CSV
- Delimiter: ,
- Has Header: Yes
- Error Handling: Continue
```

**Example 3: Analyze Log Files**
```
Node: FILE_READER
- File Path: /var/logs/app.log
- Operation: Read as Lines
- Skip Empty Lines: Yes
- Start Line: 1
- End Line: 1000
- Error Handling: Default Value
```

---

## Future Enhancements

1. **Write Operations**: Add file writing capabilities
2. **Directory Listing**: Read directory contents
3. **File Patterns**: Support glob patterns (e.g., `*.txt`)
4. **Compression**: Support for zip, gzip files
5. **Remote Files**: Support S3, HTTP URLs
6. **File Watching**: Trigger workflows on file changes
7. **Batch Processing**: Read multiple files at once
8. **Streaming**: Support for large files with streaming
9. **File Transformations**: Built-in text processing
10. **Cloud Storage**: Integration with cloud storage providers

---

## Migration Notes

- Existing workflows are not affected
- New FILE_READER node is opt-in
- Requires configuration of allowed directories
- Security settings should be reviewed before deployment
