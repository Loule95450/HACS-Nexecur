"""
Syntax validation tests for all Python files
"""
import pytest
import os
import py_compile
import tempfile
import ast


class TestPythonSyntax:
    """Test that all Python files have valid syntax"""

    def test_config_flow_syntax(self):
        """Test config_flow.py has valid syntax"""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'custom_components', 'nexecur', 'config_flow.py')
        
        # Try to compile the file
        try:
            py_compile.compile(file_path, doraise=True)
        except py_compile.PyCompileError as e:
            pytest.fail(f"Syntax error in config_flow.py: {e}")

    def test_alarm_control_panel_syntax(self):
        """Test alarm_control_panel.py has valid syntax"""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'custom_components', 'nexecur', 'alarm_control_panel.py')
        
        try:
            py_compile.compile(file_path, doraise=True)
        except py_compile.PyCompileError as e:
            pytest.fail(f"Syntax error in alarm_control_panel.py: {e}")

    def test_const_syntax(self):
        """Test const.py has valid syntax"""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'custom_components', 'nexecur', 'const.py')
        
        try:
            py_compile.compile(file_path, doraise=True)
        except py_compile.PyCompileError as e:
            pytest.fail(f"Syntax error in const.py: {e}")

    def test_all_python_files_syntax(self):
        """Test all Python files in custom_components have valid syntax"""
        base_dir = os.path.join(os.path.dirname(__file__), '..', 'custom_components', 'nexecur')
        
        errors = []
        
        for root, dirs, files in os.walk(base_dir):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    try:
                        py_compile.compile(file_path, doraise=True)
                    except py_compile.PyCompileError as e:
                        errors.append(f"{file}: {e}")
        
        if errors:
            pytest.fail("Syntax errors found:\n" + "\n".join(errors))

    def test_no_conflict_markers(self):
        """Test that no Git conflict markers exist in Python files"""
        base_dir = os.path.join(os.path.dirname(__file__), '..', 'custom_components', 'nexecur')
        
        markers = ['<<<<<<<', '=======', '>>>>>>>']
        errors = []
        
        for root, dirs, files in os.walk(base_dir):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    with open(file_path, 'r') as f:
                        content = f.read()
                        for marker in markers:
                            if marker in content:
                                errors.append(f"{file}: contains '{marker}'")
        
        if errors:
            pytest.fail("Git conflict markers found:\n" + "\n".join(errors))

    def test_balanced_parentheses(self):
        """Test that parentheses are balanced in config_flow.py"""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'custom_components', 'nexecur', 'config_flow.py')
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Count parentheses
        open_paren = content.count('(')
        close_paren = content.count(')')
        
        assert open_paren == close_paren, f"Unbalanced parentheses: {open_paren} '(' vs {close_paren} ')'"

    def test_balanced_braces(self):
        """Test that braces are balanced in config_flow.py"""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'custom_components', 'nexecur', 'config_flow.py')
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        open_brace = content.count('{')
        close_brace = content.count('}')
        
        assert open_brace == close_brace, f"Unbalanced braces: {open_brace} '{{' vs {close_brace} '}}'"

    def test_balanced_brackets(self):
        """Test that brackets are balanced in config_flow.py"""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'custom_components', 'nexecur', 'config_flow.py')
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        open_bracket = content.count('[')
        close_bracket = content.count(']')
        
        assert open_bracket == close_bracket, f"Unbalanced brackets: {open_bracket} '[' vs {close_bracket} ']'"
