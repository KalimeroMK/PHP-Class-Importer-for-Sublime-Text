import sublime
import sublime_plugin
import os
import re
import threading
from functools import lru_cache

class PhpClassNavigator(sublime_plugin.EventListener):
    def on_hover(self, view, point, hover_zone):
        """Show visual feedback for clickable classes"""
        if hover_zone != sublime.HOVER_TEXT:
            return

        word_region = view.word(point)
        if view.match_selector(point, "source.php, text.html.basic"):
            # Underline the class name when hovered
            view.add_regions(
                "clickable_class",
                [word_region],
                "entity.name.class",
                flags=sublime.DRAW_NO_FILL|sublime.DRAW_NO_OUTLINE
            )

    def on_text_command(self, view, command_name, args):
        """Handle ⌘+Click to open classes"""
        if (command_name == "drag_select" and
            args.get("by") == "words"):

            # CMD key mask for Sublime Text 3 (Python 3.3)
            if sublime.get_mouse_additional_buttons() & 64:  # 64 = CMD key
                point = view.sel()[0].begin()
                if view.match_selector(point, "source.php, text.html.basic"):
                    class_name = view.substr(view.word(point))
                    view.run_command("dynamic_class_search_and_import", {
                        "class_name": class_name
                    })
                    return ("noop", None)  # Cancel default selection
        return None

class DynamicClassSearchAndImportCommand(sublime_plugin.TextCommand):
    def run(self, edit, class_name=None):
        """Main command to find and open PHP classes"""
        if not class_name:
            class_name = self.get_selection()
            if not class_name:
                return sublime.status_message("No class name selected")

        if project_dir := self.get_project_root():
            threading.Thread(
                target=self.find_and_handle_class,
                args=(project_dir, class_name.strip())
            ).start()
        else:
            sublime.status_message("No project directory found")

    def get_project_root(self):
        """Get the first project folder"""
        if folders := sublime.active_window().folders():
            return folders[0]
        return None

    def get_selection(self):
        """Get selected text or word under cursor"""
        for region in self.view.sel():
            if not region.empty():
                return self.view.substr(region)
            return self.view.substr(self.view.word(region))
        return None

    def find_and_handle_class(self, project_dir, class_name):
        """Threaded class search and handling"""
        if class_info := self.find_php_class(project_dir, class_name):
            sublime.set_timeout(
                lambda: self.open_class_file(class_info[1]), 0)
        else:
            sublime.set_timeout(
                lambda: sublime.status_message("Class not found: %s" % class_name), 0)

    @lru_cache(maxsize=100)
    def find_php_class(self, project_dir, class_name):
        """Find class in project with caching"""
        return self.build_class_map(project_dir).get(class_name)

    def build_class_map(self, directory):
        """Create mapping of all classes to their files"""
        class_map = {}
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith('.php'):
                    full_path = os.path.join(root, file)
                    classes = self.extract_classes_from_file(full_path)
                    for cls_name, namespace in classes:
                        fqcn = "%s\\%s" % (namespace, cls_name) if namespace else cls_name
                        class_map[cls_name] = (fqcn, full_path)
                        class_map[fqcn] = (fqcn, full_path)
        return class_map

    def extract_classes_from_file(self, file_path):
        """Extract class definitions from PHP file"""
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
        """Check if position is inside comment or string"""
        preceding = content[:pos]
        return (
            '/*' in preceding or
            '//' in preceding.splitlines()[-1] or
            preceding.count('"') % 2 != 0 or
            preceding.count("'") % 2 != 0
        )

    def open_class_file(self, file_path):
        """Open file and scroll to class definition"""
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
    """Command for inserting use statements"""

    def run(self, edit, class_name):
        """Insert use statement at correct location"""
        insert_point = self.find_insert_position()
        self.view.insert(edit, insert_point, 'use %s;\n' % class_name)

    def find_insert_position(self):
        """Find position after existing use statements or namespace"""
        if use_region := self.view.find(r'^\s*use\s+.*?;', 0):
            return use_region.end() + 1
        if ns_region := self.view.find(r'<\?php|\bnamespace\b', 0):
            return self.view.line(ns_region).end()
        return 0

def plugin_loaded():
    """Initialization callback"""
    print("PHP Class Navigator ready (⌘+Click enabled)")