# HDVELH - Interactive Story Platform

## Overview

HDVELH (Histoires Dont Vous Êtes Le Héros - Stories You Are the Hero Of) is a Python-based platform for creating and playing interactive, text-based 'Choose Your Own Adventure' style stories. It provides a simple yet flexible way to bring your narratives to life.

The platform consists of two core components:

*   **Story Engine (`story_engine.py`):** A command-line program that loads and runs stories defined in JSON files.
*   **Story Creator (`story_creator.py`):** A command-line tool that guides users through the process of creating their own interactive stories.

## Features

*   Play interactive stories with multiple choices and branching narratives.
*   **Dynamic Gameplay:** Incorporates player stats (e.g., health, gold) and an inventory system.
*   **Conditional Choices:** Choices can appear or disappear based on the player's current stats or inventory items.
*   **Node & Choice Effects:** Story progression can trigger changes to player stats or inventory (e.g., finding an item, taking damage).
*   Load stories from simple and human-readable JSON files.
*   A dedicated command-line tool (`story_creator.py`) to create new stories, including defining:
    *   Story title
    *   Initial player stats and inventory
    *   Story nodes (pages/scenes) with descriptive text
    *   Effects that trigger when a player reaches a node
    *   Choices for each node, linking to other nodes
    *   Effects that trigger when a player selects a choice
    *   Conditions (based on stats or inventory) that must be met for a choice to be available
    *   The starting node of the story
*   Saves created stories in the JSON format, ready to be played or shared.

## Getting Started / Usage

### Prerequisites

*   Python 3.x

### Playing a Story

Stories are defined in JSON files.
*   A basic example is provided in `example_story.json`.
*   A more complex example showcasing stats, inventory, effects, and conditions is in `advanced_example_story.json`.

To play a story, run the following command in your terminal:

```bash
python story_engine.py <path_to_your_story.json>
```

For example:

```bash
python story_engine.py example_story.json
```
Or, to try the advanced features:
```bash
python story_engine.py advanced_example_story.json
```

The engine will load the story, display your initial stats and inventory, and present you with the text and available choices.

### Creating a Story

To create a new interactive story, use the story creator tool:

```bash
python story_creator.py
```

The tool will guide you through the following steps:
1.  **Enter a title** for your story.
2.  **Define initial player stats:** (Optional) Set starting values for stats like health, gold, etc.
3.  **Define initial player inventory:** (Optional) List items the player starts with.
4.  **Add nodes:** For each node (a page or situation):
    *   Define a unique **ID**.
    *   Write the **descriptive text**.
    *   Define **node effects** (Optional): Actions that occur automatically upon entering the node (e.g., taking damage, finding gold).
    *   Add **choices** for the player. Each choice has:
        *   **Text** (e.g., "Go north", "Open the chest").
        *   A **target node ID** that this choice leads to.
        *   **Choice effects** (Optional): Actions that occur if this choice is selected.
        *   **Conditions** (Optional): Requirements (based on player stats or inventory) for this choice to be visible.
5.  **Set the start node:** Specify which node begins the story.
6.  **Save the story:** Provide a filename, and the tool saves it in JSON format.

## Story Format

The stories are stored in JSON files. Here's an overview of the structure:

*   `title`: (String) The title of the story.
*   `initial_stats`: (Object, Optional) Key-value pairs defining the player's starting statistics.
    *   Example: `"initial_stats": {"health": 100, "mana": 50, "gold": 10}`
*   `initial_inventory`: (Array of Strings, Optional) A list of item names the player starts with.
    *   Example: `"initial_inventory": ["rusty_sword", "bread"]`
*   `start_node_id`: (String) The ID of the node where the story begins.
*   `nodes`: (Object) A collection of all nodes in the story, where each key is a node's ID.
    *   Each **node object** can contain:
        *   `id`: (String) A unique identifier for the node.
        *   `text`: (String) The descriptive text displayed to the player.
        *   `effects`: (Array of Effect Objects, Optional) Effects that trigger upon entering this node.
        *   `choices`: (Array of Choice Objects) A list of choices available at this node.
            *   Each **choice object** can contain:
                *   `text`: (String) The text displayed for this choice.
                *   `target_node_id`: (String) The ID of the node this choice leads to.
                *   `effects`: (Array of Effect Objects, Optional) Effects that trigger if this choice is selected.
                *   `conditions`: (Array of Condition Objects, Optional) Conditions that must be met for this choice to be available.

### Effect Objects

Effects modify the player's state. They are defined as objects with a `type` and other properties based on the type:

*   **`stat_change`**: Modifies a player statistic.
    *   `type`: `"stat_change"`
    *   `stat`: (String) The name of the stat to change (e.g., "health").
    *   `change_by`: (Integer, Optional) The amount to add to the stat (can be negative).
    *   `set_to`: (Integer, Optional) The value to set the stat to directly.
    *   Example: `{"type": "stat_change", "stat": "gold", "change_by": 10}`
    *   Example: `{"type": "stat_change", "stat": "health", "set_to": 100}`
*   **`inventory_change`**: Modifies the player's inventory.
    *   `type`: `"inventory_change"`
    *   `item`: (String) The name of the item.
    *   `action`: (String) Either `"add"` or `"remove"`.
    *   Example: `{"type": "inventory_change", "item": "key", "action": "add"}`

### Condition Objects

Conditions determine if a choice is available. All conditions in a choice's `conditions` list must be met. They are objects with a `type` and other properties:

*   **`stat_condition`**: Checks a player statistic.
    *   `type`: `"stat_condition"`
    *   `stat`: (String) The name of the stat to check.
    *   `requires_greater_than`: (Integer, Optional) Stat must be greater than this value.
    *   `requires_less_than`: (Integer, Optional) Stat must be less than this value.
    *   `requires_equal_to`: (Integer, Optional) Stat must be equal to this value.
    *   Example: `{"type": "stat_condition", "stat": "strength", "requires_greater_than": 5}`
*   **`inventory_condition`**: Checks for an item in the player's inventory.
    *   `type`: `"inventory_condition"`
    *   `item`: (String) The name of the item.
    *   `requires`: (String) Either `"present"` or `"absent"`.
    *   Example: `{"type": "inventory_condition", "item": "torch", "requires": "present"}`

You can refer to `example_story.json` for a basic structure and `advanced_example_story.json` for a comprehensive example of these advanced mechanics.

## Future Enhancements (Optional)

This platform provides a solid foundation for interactive storytelling. Potential future enhancements could include:

*   **Graphical Story Editor:** A web-based or desktop GUI for a more visual story creation process.
*   **Advanced Game Mechanics:** Incorporating features like inventory systems, character stats, or dice rolls.
*   **State Variables:** Allowing stories to track player progress or choices using variables that can affect future text or available options.
*   **Multimedia Support:** Adding options to include images or sound effects.
*   **Validation in Story Creator:** More robust validation in the `story_creator.py` tool, such as ensuring all `target_node_id`s in choices point to existing nodes before saving.

We encourage contributions and new ideas!
