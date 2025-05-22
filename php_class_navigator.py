import sublime
import sublime_plugin
import os
import re
import threading
import json
from functools import lru_cache

class PhpClassNavigator(sublime_plugin.EventListener):
    def on_hover(self, view, point, hover_zone):
        if hover_zone != sublime.HOVER_TEXT:
            return
        modifiers = sublime.get_mouse_additional_buttons()
        if not (modifiers & sublime.MOUSE_CTRL or modifiers & sublime.MOUSE_CMD):
            return
        word_region = view.word(point)
        class_name = view.substr(word_region)
        syntax = view.syntax()
        if not syntax or ("php" not in syntax.name.lower() and "blade" not in syntax.name.lower()):
            return
        view.run_command("dynamic_class_search_and_import", {"class_name": class_name})

class DynamicClassSearchAndImportCommand(sublime_plugin.TextCommand):
    def run(self, edit, class_name=None):
        if not class_name:
            class_name = self.get_selection()
            if not class_name:
                sublime.status_message("No class name selected.")
                return
        project_dir = self.get_project_root()
        if not project_dir:
            sublime.status_message("No project directory found.")
            return
        threading.Thread(
            target=self.find_and_handle_class,
            args=(project_dir, class_name.strip())
        ).start()

    def get_project_root(self):
        window = sublime.active_window()
        if not window.folders():
            return None
        return window.folders()[0]

    def get_selection(self):
        for region in self.view.sel():
            if not region.empty():
                return self.view.substr(region)
            return self.view.substr(self.view.word(region))
        return None

    def find_and_handle_class(self, project_dir, class_name):
        class_info = self.find_php_class(project_dir, class_name)
        sublime.set_timeout(lambda: self.handle_class_result(class_info, class_name), 0)

    @lru_cache(maxsize=100)
    def find_php_class(self, project_dir, class_name):
        class_map = self.build_class_map(project_dir)
        return class_map.get(class_name)

    def build_class_map(self, directory):
        class_map = {}
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith('.php'):
                    full_path = os.path.join(root, file)
                    classes = self.extract_classes_from_file(full_path)
                    for class_name, namespace in classes:
                        fqcn = f"{namespace}\{class_name}" if namespace else class_name
                        class_map[class_name] = (fqcn, full_path)
                        class_map[fqcn] = (fqcn, full_path)
        return class_map

    def extract_classes_from_file(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        namespace_match = re.search(r'namespace\s+([^;]+);', content)
        namespace = namespace_match.group(1).strip() if namespace_match else ''
        classes = []
        for match in re.finditer(r'(class|interface|trait)\s+(\w+)', content):
            if not self.is_in_comment_or_string(content, match.start()):
                classes.append((match.group(2), namespace))
        return classes

    def is_in_comment_or_string(self, content, pos):
        preceding = content[:pos]
        return (
            '/*' in preceding or 
            '//' in preceding.splitlines()[-1] or
            preceding.count('"') % 2 != 0 or
            preceding.count("'") % 2 != 0
        )

    def handle_class_result(self, class_info, class_name):
        if not class_info:
            sublime.status_message(f"Class not found: {class_name}")
            return
        fqcn, file_path = class_info
        self.open_class_file(file_path)

    def open_class_file(self, file_path):
        window = sublime.active_window()
        view = window.open_file(file_path)
        def scroll_to_class():
            if view.is_loading():
                sublime.set_timeout(scroll_to_class, 100)
            else:
                class_region = view.find(r'(class|interface|trait)\s+\w+', 0)
                if class_region:
                    view.show_at_center(class_region)
                    view.sel().clear()
                    view.sel().add(class_region.begin())
        sublime.set_timeout(scroll_to_class, 100)

class InsertUseStatementCommand(sublime_plugin.TextCommand):
    def run(self, edit, class_name):
        use_region = self.view.find(r'^\s*use\s+.*?;', 0)
        insert_point = use_region.end() + 1 if use_region else self.find_namespace_end()
        self.view.insert(edit, insert_point, f'use {class_name};\n')

    def find_namespace_end(self):
        namespace_region = self.view.find(r'<\?php|\bnamespace\b', 0)
        if namespace_region:
            return self.view.line(namespace_region).end()
        return 0
