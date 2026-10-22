"""Security checker configuration for Python agent runtime.

This module defines security rules to restrict dangerous operations
in user-provided code execution contexts.
"""

from cave_agent import SecurityChecker, ImportRule, FunctionRule, AttributeRule, RegexRule


# Define forbidden imports that could compromise system security
FORBIDDEN_IMPORTS = {
    "os", "subprocess", "sys", "shutil", "pathlib",
    "socket", "urllib", "http", "ctypes", "gc",
    "csv", "multiprocessing", "threading"
}

# Define forbidden functions that could allow arbitrary code execution
FORBIDDEN_FUNCTIONS = {
    "exec", "compile", "open", "input", "raw_input",
    "exit", "quit", "__import__", "globals", "locals",
    "breakpoint", "eval"
}

# Define forbidden attributes that could expose internals
FORBIDDEN_ATTRIBUTES = {
    "__globals__", "__locals__", "__code__", "__closure__",
    "__defaults__", "__dict__", "__class__", "__bases__",
    "__mro__", "__subclasses__", "__import__", "__builtins__"
}


def create_security_checker() -> SecurityChecker:
    """Create and configure a security checker with all security rules.

    Returns:
        SecurityChecker: Configured security checker instance
    """
    return SecurityChecker([
        # Restrict dangerous imports
        ImportRule(FORBIDDEN_IMPORTS),

        # Restrict dangerous function calls
        FunctionRule(FORBIDDEN_FUNCTIONS),

        # Restrict access to internal attributes
        AttributeRule(FORBIDDEN_ATTRIBUTES),

        # Forbidden database modification statements (read-only access).
        #
        # Patterns are scoped to SQL-statement shapes (keyword + its required
        # SQL continuation), NOT bare keywords: bare `\bupdate\b`-style rules
        # blocked ordinary Python idioms (`dict.update()`, `df.insert()`,
        # `create_engine`, comments like "# create summary table"), which
        # penalized agents by coding style rather than by capability.
        #
        # This remains best-effort, client-side defense in depth — dynamically
        # assembled SQL can evade any regex. The authoritative enforcement is
        # (and must stay) the read-only role on the database server.
        RegexRule(r"(?i)\bdelete\s+from\b", "Detects SQL DELETE FROM"),
        RegexRule(r"(?i)\bdrop\s+(table|database|index|view|schema|extension|function|trigger|role|user)\b",
                  "Detects SQL DROP <object>"),
        RegexRule(r"(?i)\balter\s+(table|database|index|view|schema|role|user|system)\b",
                  "Detects SQL ALTER <object>"),
        RegexRule(r"(?i)\bcreate\s+(table|database|index|view|schema|extension|function|trigger|role|user|materialized)\b",
                  "Detects SQL CREATE <object>"),
        RegexRule(r"(?i)\binsert\s+into\b", "Detects SQL INSERT INTO"),
        RegexRule(r"(?i)\bupdate\s+[\w.\"]+\s+set\b", "Detects SQL UPDATE ... SET"),
        RegexRule(r"(?i)\btruncate\s+(table\s+)?[\w.\"]+", "Detects SQL TRUNCATE"),
        RegexRule(r"(?i)\bgrant\s+(select|insert|update|delete|all|usage|create|connect|references)\b",
                  "Detects SQL GRANT"),
        RegexRule(r"(?i)\brevoke\s+(select|insert|update|delete|all|usage|create|connect|references)\b",
                  "Detects SQL REVOKE"),
    ])


# Create singleton security checker instance
security_checker = create_security_checker()
