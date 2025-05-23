import json
import argparse
import sys

def load_story(filepath: str) -> dict:
  """Reads a JSON file and returns it as a Python dictionary."""
  with open(filepath, 'r') as f:
    story_data = json.load(f)
  return story_data

def apply_effects(effects_list: list, player_stats: dict, player_inventory: list) -> None:
    """Applies a list of effects to player stats and inventory."""
    if not effects_list:
        return

    for effect in effects_list:
        effect_type = effect.get("type")
        if effect_type == "stat_change":
            stat_name = effect.get("stat")
            if stat_name: # Ensure stat_name is present
                change_by = effect.get("change_by")
                set_to = effect.get("set_to")
                if change_by is not None:
                    player_stats[stat_name] = player_stats.get(stat_name, 0) + change_by
                elif set_to is not None:
                    player_stats[stat_name] = set_to
        elif effect_type == "inventory_change":
            item_name = effect.get("item")
            action = effect.get("action")
            if item_name and action: # Ensure item_name and action are present
                if action == "add" and item_name not in player_inventory:
                    player_inventory.append(item_name)
                elif action == "remove" and item_name in player_inventory:
                    player_inventory.remove(item_name)

def check_conditions(conditions_list: list, player_stats: dict, player_inventory: list) -> bool:
    """Checks if all conditions in a list are met by the player's current state."""
    if not conditions_list:
        return True # No conditions means the check passes

    for condition in conditions_list:
        condition_type = condition.get("type")
        if condition_type == "stat_condition":
            stat_name = condition.get("stat")
            if stat_name is None: # Skip if stat name is missing
                continue
            current_stat_value = player_stats.get(stat_name, 0)
            
            greater_than = condition.get("requires_greater_than")
            less_than = condition.get("requires_less_than")
            equal_to = condition.get("requires_equal_to")

            # At least one condition value must be present for the condition to be valid
            if greater_than is None and less_than is None and equal_to is None:
                continue

            if greater_than is not None and not current_stat_value > greater_than:
                return False
            if less_than is not None and not current_stat_value < less_than:
                return False
            if equal_to is not None and not current_stat_value == equal_to:
                return False
        elif condition_type == "inventory_condition":
            item_name = condition.get("item")
            requirement = condition.get("requires")
            if item_name is None or requirement is None: # Skip if item name or requirement is missing
                continue
            if requirement == "present" and item_name not in player_inventory:
                return False
            if requirement == "absent" and item_name in player_inventory:
                return False
        # else:
            # Optionally handle unknown condition types, for now, they are ignored (effectively pass)
    return True

def play_story(story_data: dict):
  """Plays the story using the provided story data."""
  player_stats = {}
  player_inventory = []

  # Initialize player state from story_data (Requirement 1)
  initial_stats = story_data.get("initial_stats", {})
  player_stats.update(initial_stats)
  
  initial_inventory = story_data.get("initial_inventory", [])
  for item in initial_inventory:
      if item not in player_inventory: # Ensure uniqueness
          player_inventory.append(item)

  current_node_id = story_data.get('start_node_id')
  if not current_node_id:
      print("Error: Story has no 'start_node_id'. Cannot begin.")
      sys.exit(1)

  while True:
    current_node = story_data.get('nodes', {}).get(current_node_id)
    if not current_node:
        print(f"Error: Node '{current_node_id}' not found in story data. Exiting.")
        sys.exit(1)

    # Apply node effects (Requirement 4a)
    node_effects = current_node.get("effects")
    if node_effects:
        apply_effects(node_effects, player_stats, player_inventory)

    # Display player state (Requirement 2)
    print("\n--- Stats ---")
    if player_stats:
        for stat, value in player_stats.items():
            print(f"{stat.capitalize()}: {value}")
    else:
        print("None")
    
    print("--- Inventory ---")
    if player_inventory:
        for item in player_inventory:
            print(f"- {item.capitalize()}")
    else:
        print("Empty")
    print("------------")
    
    print(f"\n{current_node.get('text', 'This node has no text.')}")

    # Filter and display available choices (Requirement 6)
    available_choices_display = [] # For displaying to user (text and new index)
    possible_choices_data = [] # For mapping selection back to original choice data

    original_choices = current_node.get("choices", [])
    for original_idx, choice_data in enumerate(original_choices):
        conditions = choice_data.get("conditions")
        if check_conditions(conditions, player_stats, player_inventory):
            available_choices_display.append(choice_data.get("text", "Unnamed choice"))
            possible_choices_data.append(choice_data) # Store the full choice data

    if not available_choices_display:
      print("The End.") # Or some other message if no choices are available but it's not an explicit end node
      break

    for i, choice_text in enumerate(available_choices_display):
      print(f"{i + 1}. {choice_text}")

    selected_choice_data = None
    while True:
      try:
        choice_num_str = input("Enter your choice: ")
        if not choice_num_str:
            print("Invalid choice. Please try again.")
            continue
        choice_num = int(choice_num_str)
        if 1 <= choice_num <= len(available_choices_display):
          selected_choice_data = possible_choices_data[choice_num - 1]
          break
        else:
          print("Invalid choice. Please try again.")
      except ValueError:
        print("Invalid input. Please enter a number.")
      except EOFError: 
        print("\nExiting game.")
        sys.exit(0)
    
    # Apply choice effects (Requirement 4b)
    choice_effects = selected_choice_data.get("effects")
    if choice_effects:
        apply_effects(choice_effects, player_stats, player_inventory)
        
    current_node_id = selected_choice_data.get("target_node_id")
    if not current_node_id:
        print("Error: Choice has no 'target_node_id'. Game cannot continue.")
        sys.exit(1)


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Play a Choose Your Own Adventure story from a JSON file.")
  parser.add_argument("story_filepath", help="Path to the story JSON file")
  args = parser.parse_args()

  try:
    story_data = load_story(args.story_filepath)
  except FileNotFoundError:
    print(f"Error: Story file not found at '{args.story_filepath}'")
    sys.exit(1)
  except json.JSONDecodeError:
    print(f"Error: Invalid JSON format in story file '{args.story_filepath}'")
    sys.exit(1)
  # Removed KeyError check here as play_story now handles missing keys more gracefully.
  
  play_story(story_data)
