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


class FileReaderError(Exception):
    """Exception raised for file reader errors"""

    def __init__(self, message: str, error_code: str = "FILE_READER_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class FileReaderService:
    """Service for secure file reading operations"""

    def __init__(self):
        self.allowed_dirs = self._parse_allowed_dirs()
        self.max_file_size_bytes = getattr(settings, 'FILE_READER_MAX_FILE_SIZE_MB', 10) * 1024 * 1024
        self.follow_symlinks = getattr(settings, 'FILE_READER_FOLLOW_SYMLINKS', False)
        self.allow_hidden = getattr(settings, 'FILE_READER_ALLOW_HIDDEN_FILES', False)

    def _parse_allowed_dirs(self) -> List[Path]:
        """Parse and expand environment variables in allowed directories"""
        dirs = []
        allowed_dirs_config = getattr(settings, 'FILE_READER_ALLOWED_DIRS', ['/var/data', './data', './uploads'])

        for dir_path in allowed_dirs_config:
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


# Singleton instance
file_reader_service = FileReaderService()
