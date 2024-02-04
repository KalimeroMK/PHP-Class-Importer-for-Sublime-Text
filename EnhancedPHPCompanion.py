import sublime
import sublime_plugin
import os
import re
import threading

class DynamicClassSearchAndImportCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        project_dir = sublime.active_window().folders()[0] if sublime.active_window().folders() else None
        if not project_dir:
            sublime.status_message("No project directory found.")
            return

        self.selection = self.get_selection()
        if not self.selection:
            sublime.status_message("No class name selected.")
            return

        threading.Thread(target=self.find_php_classes, args=(project_dir, self.selection, edit)).start()

    def get_selection(self):
        for region in self.view.sel():
            if region.empty():
                word = self.view.word(region)
                return self.view.substr(word)
            else:
                return self.view.substr(region)
        return None

    def find_php_classes(self, directory, class_name, edit):
        namespace_pattern = re.compile(r'^\s*namespace\s+([^;]+);', re.MULTILINE)
        class_pattern = re.compile(
            r'\b(abstract\s+)?(class|interface|trait)\s+' + re.escape(class_name) + 
            r'\b(?!\s*::)(?!\s*->)(?!\s*\{)',
            re.MULTILINE | re.IGNORECASE)

        class_names = []
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith('.php'):
                    full_path = os.path.join(root, file)
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                        namespace_match = namespace_pattern.search(content)
                        namespace = namespace_match.group(1).strip() if namespace_match else ''

                        for class_match in class_pattern.finditer(content):
                            line_start = content.rfind('\n', 0, class_match.start()) + 1
                            line_end = content.find('\n', class_match.end())
                            line = content[line_start:line_end].strip()

                            if line.startswith(("class ", "trait ", "interface ")) and class_name in line:
                                fqcn = f"{namespace}\\{class_name}" if namespace else class_name
                                class_names.append(fqcn)

        sublime.set_timeout(lambda: self.show_quick_panel(class_names, edit), 10)

    def show_quick_panel(self, class_names, edit):
        if class_names:
            sublime.active_window().show_quick_panel(class_names, lambda index: self.on_done(index, class_names))
        else:
            sublime.status_message("No classes found matching: " + self.selection)

    def on_done(self, index, class_names):
        if index >= 0:
            selected_class_name = class_names[index]
            self.view.run_command('insert_use_statement', {'class_name': selected_class_name})

class InsertUseStatementCommand(sublime_plugin.TextCommand):
    def run(self, edit, class_name):
        # Find the position to insert the use statement
        regions = self.view.find_all(r'<\?(php)?|\bnamespace\b')
        if regions:
            insert_point = self.view.line(regions[-1]).end()
            self.view.insert(edit, insert_point, f'\nuse {class_name};\n')
        else:
            self.view.insert(edit, 0, f'<?php\n\nuse {class_name};\n')
