import sublime
import sublime_plugin
import os
import re
import threading
from functools import lru_cache
from pathlib import Path

class PhpClassNavigator(sublime_plugin.EventListener):
    """Enables PHPStorm-like class navigation in Sublime Text"""

    def on_hover(self, view, point, hover_zone):
        """Handle Ctrl+Click on class names"""
        if (hover_zone != sublime.HOVER_TEXT or
            not (sublime.get_mouse_additional_buttons() &
                 (sublime.MOUSE_CTRL | sublime.MOUSE_CMD))):
            return

        class_name = view.substr(view.word(point))
        if self._is_php_file(view):
            view.run_command("dynamic_class_search_and_import",
                           {"class_name": class_name})

    def _is_php_file(self, view):
        """Check if file is PHP or Blade template"""
        syntax = view.syntax()
        return syntax and ("php" in syntax.name.lower() or
                         "blade" in syntax.name.lower())

class DynamicClassSearchAndImportCommand(sublime_plugin.TextCommand):
    """Main command for finding and importing PHP classes"""

    def run(self, edit, class_name=None):
        """Entry point for the command"""
        if not class_name:
            class_name = self._get_selection()

        if not class_name:
            return sublime.status_message("No class name selected")

        if project_dir := self._get_project_root():
            threading.Thread(
                target=self._find_and_handle_class,
                args=(project_dir, class_name.strip())
            ).start()
        else:
            sublime.status_message("No project directory found")

    def _get_project_root(self):
        """Get the first project folder"""
        if folders := sublime.active_window().folders():
            return folders[0]
        return None

    def _get_selection(self):
        """Get currently selected text or word under cursor"""
        for region in self.view.sel():
            return (self.view.substr(region) if not region.empty()
                    else self.view.substr(self.view.word(region)))
        return None

    def _find_and_handle_class(self, project_dir, class_name):
        """Threaded class search and handling"""
        if class_info := self._find_php_class(project_dir, class_name):
            sublime.set_timeout(
                lambda: self._open_class_file(class_info[1]), 0)
        else:
            sublime.set_timeout(
                lambda: sublime.status_message(f"Class not found: {class_name}"), 0)

    @lru_cache(maxsize=100)
    def _find_php_class(self, project_dir, class_name):
        """Find class in project with caching"""
        return self._build_class_map(project_dir).get(class_name)

    def _build_class_map(self, directory):
        """Create mapping of all classes to their files"""
        class_map = {}
        for php_file in Path(directory).rglob('*.php'):
            for class_name, namespace in self._extract_classes_from_file(php_file):
                fqcn = f"{namespace}\\{class_name}" if namespace else class_name
                class_map.update({class_name: (fqcn, str(php_file)),
                                fqcn: (fqcn, str(php_file))})
        return class_map

    def _extract_classes_from_file(self, file_path):
        """Extract class definitions from PHP file"""
        content = file_path.read_text(encoding='utf-8')
        namespace = self._extract_namespace(content)

        return [
            (match.group(2), namespace)
            for match in re.finditer(r'(class|interface|trait)\s+(\w+)', content)
            if not self._is_in_comment_or_string(content, match.start())
        ]

    def _extract_namespace(self, content):
        """Extract namespace from PHP file content"""
        if match := re.search(r'namespace\s+([^;]+);', content):
            return match.group(1).strip()
        return ''

    def _is_in_comment_or_string(self, content, pos):
        """Check if position is inside comment or string"""
        preceding = content[:pos]
        return ('/*' in preceding or
                '//' in preceding.splitlines()[-1] or
                preceding.count('"') % 2 != 0 or
                preceding.count("'") % 2 != 0)

    def _open_class_file(self, file_path):
        """Open file and scroll to class definition"""
        view = sublime.active_window().open_file(file_path)

        def scroll_to_class():
            if view.is_loading():
                return sublime.set_timeout(scroll_to_class, 100)

            if class_region := view.find(r'(class|interface|trait)\s+\w+', 0):
                view.show_at_center(class_region)
                view.sel().clear()
                view.sel().add(class_region.begin())

        sublime.set_timeout(scroll_to_class, 100)

class InsertUseStatementCommand(sublime_plugin.TextCommand):
    """Command for inserting use statements"""

    def run(self, edit, class_name):
        """Insert use statement at correct location"""
        insert_point = self._find_insert_position()
        self.view.insert(edit, insert_point, f'use {class_name};\n')

    def _find_insert_position(self):
        """Find position after existing use statements or namespace"""
        if use_region := self.view.find(r'^\s*use\s+.*?;', 0):
            return use_region.end() + 1
        if ns_region := self.view.find(r'<\?php|\bnamespace\b', 0):
            return self.view.line(ns_region).end()
        return 0

def plugin_loaded():
    """Initialization callback"""
    print("PHP Class Navigator successfully loaded")