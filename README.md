# PHP Class Importer for Sublime Text

PHP Class Importer is a Sublime Text plugin that simplifies the process of searching for PHP classes across your project and quickly adding `use` statements to your PHP files.

## Features

- **Fast Class Search**: Quickly find PHP classes by name throughout your entire project.
- **Quick Panel Selection**: Use Sublime Text's quick panel to choose from a list of classes when multiple matches are found.
- **Automatic `use` Insertion**: Automatically insert the selected class's `use` statement at the appropriate place in your PHP file.
- **Non-blocking Operations**: Searches are performed in a separate thread to keep Sublime Text responsive.

## How to Use

1. Select the class name you wish to import in your PHP file.
2. Activate the command (you can set up a key binding or run it from the command palette).
3. If multiple classes with the same name are found, a quick panel will appear, allowing you to select the correct one.
4. Once selected, the `use` statement for that class will be inserted at the top of your current file, after any existing `use` statements.

## Installation

To install the plugin, follow these steps:

1. Copy the plugin files into your Sublime Text `Packages/User` directory.
2. Restart Sublime Text to ensure the plugin is loaded.
3. Optionally, set up a key binding for the plugin by adding the following to your key bindings file:

```json
{
    "keys": ["<your_preferred_keybinding>"],
    "command": "dynamic_class_search_and_import"
}
