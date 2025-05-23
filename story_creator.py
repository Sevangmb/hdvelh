import json

def initialize_story() -> dict:
    """Initializes a new story structure."""
    return {
        "title": "", 
        "start_node_id": "", 
        "nodes": {}, 
        "initial_stats": {}, 
        "initial_inventory": [],
        "max_players": 1, # Requirement 6
        "player_character_templates": {} # Requirement 6
    }

def prompt_for_stats_dict() -> dict:
    """Prompts the user to define a dictionary of stat:value pairs."""
    stats = {}
    print("Define stats for this template/character:")
    while True:
        stat_name = input("Enter stat name (e.g., health, agility) or leave empty to finish: ").strip()
        if not stat_name:
            break
        while True:
            try:
                stat_value = int(input(f"Enter initial integer value for '{stat_name}': "))
                stats[stat_name] = stat_value
                print(f"Stat '{stat_name}' set to {stat_value}.")
                break
            except ValueError:
                print("Invalid input. Please enter an integer.")
        if input("Add another stat? (yes/no): ").lower() != 'yes':
            break
    return stats

def prompt_for_inventory_list() -> list:
    """Prompts the user to define a list of inventory items."""
    inventory = []
    print("Define initial inventory items for this template/character:")
    while True:
        item_name = input("Enter item name (e.g., key, sword) or leave empty to finish: ").strip()
        if not item_name:
            break
        if item_name not in inventory:
            inventory.append(item_name)
            print(f"Item '{item_name}' added to inventory.")
        else:
            print(f"Item '{item_name}' is already in the inventory.")
        if input("Add another item? (yes/no): ").lower() != 'yes':
            break
    return inventory

def manage_player_templates(story_data: dict): # Requirement 2
    """Manages player character templates in the story data."""
    if "player_character_templates" not in story_data: # Should be there from initialize_story
        story_data["player_character_templates"] = {}

    while True:
        print("\n--- Manage Player Character Templates ---")
        print("1. Add New Template")
        print("2. View Existing Templates")
        print("3. Return to Main Menu")
        choice = input("Enter your choice: ")

        if choice == '1': # Add Template
            role_name = input("Enter unique role name for the template (e.g., Scout, Technician): ").strip()
            if not role_name:
                print("Role name cannot be empty.")
                continue
            if role_name in story_data["player_character_templates"]:
                print(f"Role name '{role_name}' already exists. Try editing or choose a new name.")
                continue
            
            template = {}
            template["description"] = input(f"Enter description for role '{role_name}': ").strip()
            
            print(f"\n--- Defining initial stats for role '{role_name}' ---")
            template["initial_stats"] = prompt_for_stats_dict()
            
            print(f"\n--- Defining initial inventory for role '{role_name}' ---")
            template["initial_inventory"] = prompt_for_inventory_list()
            
            role_start_node = input(f"Enter a specific start_node_id for role '{role_name}' (optional, leave empty if none): ").strip()
            if role_start_node:
                template["start_node_id"] = role_start_node
            
            story_data["player_character_templates"][role_name] = template
            print(f"Player character template '{role_name}' added successfully.")

        elif choice == '2': # View Templates
            if not story_data["player_character_templates"]:
                print("No player character templates defined yet.")
            else:
                print("\n--- Existing Player Character Templates ---")
                for role_name, template_data in story_data["player_character_templates"].items():
                    print(f"\nRole: {role_name}")
                    print(f"  Description: {template_data.get('description', 'N/A')}")
                    print(f"  Initial Stats: {template_data.get('initial_stats', {})}")
                    print(f"  Initial Inventory: {template_data.get('initial_inventory', [])}")
                    if "start_node_id" in template_data:
                        print(f"  Role-Specific Start Node: {template_data['start_node_id']}")
        elif choice == '3':
            break
        else:
            print("Invalid choice. Please try again.")


def prompt_for_effects() -> list:
    """Prompts the user to define a list of effects."""
    effects = []
    while True:
        add_effect_prompt = input("Add an effect for this element? (yes/no): ").lower()
        if add_effect_prompt == 'no':
            break
        if add_effect_prompt != 'yes':
            print("Invalid input. Please enter 'yes' or 'no'.")
            continue

        effect = {}
        while True:
            effect_type = input("Effect type? (stat_change / inventory_change): ").lower()
            if effect_type in ["stat_change", "inventory_change"]:
                effect["type"] = effect_type
                break
            print("Invalid effect type. Choose 'stat_change' or 'inventory_change'.")

        if effect["type"] == "stat_change":
            effect["stat"] = input("Enter stat name to change (e.g., health): ").strip()
            while True:
                change_mode = input("Change mode? (change_by / set_to): ").lower()
                if change_mode in ["change_by", "set_to"]:
                    break
                print("Invalid change mode. Choose 'change_by' or 'set_to'.")
            
            while True:
                try:
                    value = int(input(f"Enter integer value for '{change_mode}': "))
                    effect[change_mode] = value
                    break
                except ValueError:
                    print("Invalid input. Please enter an integer.")
        
        elif effect["type"] == "inventory_change":
            effect["item"] = input("Enter item name (e.g., key): ").strip()
            while True:
                action = input("Action? (add / remove): ").lower()
                if action in ["add", "remove"]:
                    effect["action"] = action
                    break
                print("Invalid action. Choose 'add' or 'remove'.")
        
        effects.append(effect)
        print("Effect added.")
    return effects

def prompt_for_conditions() -> list:
    """Prompts the user to define a list of conditions for a choice."""
    conditions = []
    while True:
        add_condition_prompt = input("Add a condition for this choice? (yes/no): ").lower()
        if add_condition_prompt == 'no':
            break
        if add_condition_prompt != 'yes':
            print("Invalid input. Please enter 'yes' or 'no'.")
            continue
        
        condition = {}
        while True:
            condition_type = input("Condition type? (stat_condition / inventory_condition): ").lower()
            if condition_type in ["stat_condition", "inventory_condition"]:
                condition["type"] = condition_type
                break
            print("Invalid condition type. Choose 'stat_condition' or 'inventory_condition'.")

        if condition["type"] == "stat_condition":
            condition["stat"] = input("Enter stat name for condition (e.g., charisma): ").strip()
            while True:
                req_type = input("Requirement type? (requires_greater_than / requires_less_than / requires_equal_to): ").lower()
                if req_type in ["requires_greater_than", "requires_less_than", "requires_equal_to"]:
                    condition[req_type] = None # Placeholder, will be filled next
                    break
                print("Invalid requirement type.")
            
            while True:
                try:
                    value = int(input(f"Enter integer value for '{req_type}': "))
                    condition[req_type] = value
                    break
                except ValueError:
                    print("Invalid input. Please enter an integer.")

        elif condition["type"] == "inventory_condition":
            condition["item"] = input("Enter item name for condition (e.g., map): ").strip()
            while True:
                req = input("Requirement? (present / absent): ").lower()
                if req in ["present", "absent"]:
                    condition["requires"] = req
                    break
                print("Invalid requirement. Choose 'present' or 'absent'.")
        
        conditions.append(condition)
        print("Condition added.")
    return conditions

def add_node(story_data: dict):
    """Adds a new node to the story."""
    while True:
        node_id = input("Enter a unique ID for this node (e.g., 'room1', 'forest_path'): ").strip()
        if node_id in story_data["nodes"]:
            print("Node ID already exists. Please choose a different ID.")
        elif not node_id:
            print("Node ID cannot be empty.")
        else:
            break

    node_text = input(f"Enter the descriptive text for node '{node_id}': ").strip()
    
    print(f"\n--- Define global effects for node '{node_id}' (apply to all players or game state) ---")
    node_effects = prompt_for_effects() # These are global effects for the node
    
    story_data["nodes"][node_id] = {"id": node_id, "text": node_text, "choices": []}
    if node_effects:
        story_data["nodes"][node_id]["effects"] = node_effects # Global effects
    
    print(f"Node '{node_id}' added.")

    print(f"\n--- Define choices for node '{node_id}' ---")
    while True:
        add_choice_prompt = input("Add a choice for this node? (yes/no): ").lower()
        if add_choice_prompt == 'yes':
            choice_text = input("Enter the text for this choice (e.g., 'Go left'): ").strip()
            
            while True:
                target_node_id = input(f"Enter the target node ID for the choice '{choice_text}': ").strip()
                if not target_node_id: # Basic check, actual node existence not validated here
                    print("Target node ID cannot be empty.")
                else:
                    break
            
            choice_dict = {"text": choice_text, "target_node_id": target_node_id}

            # Requirement 3: actionable_by_roles
            if input("Restrict this choice to specific player roles? (yes/no): ").lower() == 'yes':
                roles = []
                while True:
                    role_name = input("Enter role name allowed to make this choice (or leave empty to finish): ").strip()
                    if not role_name: break
                    roles.append(role_name)
                if roles: choice_dict["actionable_by_roles"] = roles
            
            print(f"\n--- Define general effects for choice '{choice_text}' (apply to game state or all players) ---")
            choice_general_effects = prompt_for_effects()
            if choice_general_effects:
                choice_dict["effects"] = choice_general_effects

            # Requirement 4: effects_for_chooser
            if input("Add effects that apply *only* to the player making this choice? (yes/no): ").lower() == 'yes':
                print(f"\n--- Define effects *for the chooser* of choice '{choice_text}' ---")
                chooser_effects = prompt_for_effects()
                if chooser_effects:
                    choice_dict["effects_for_chooser"] = chooser_effects
            
            print(f"\n--- Define conditions for choice '{choice_text}' ---")
            choice_conditions = prompt_for_conditions()
            if choice_conditions:
                choice_dict["conditions"] = choice_conditions

            # Requirement 5: requires_vote
            if input("Does this choice require a vote from all players to proceed? (yes/no): ").lower() == 'yes':
                choice_dict["requires_vote"] = True
            
            story_data["nodes"][node_id]["choices"].append(choice_dict)
            print("Choice added.")
        elif add_choice_prompt == 'no':
            break
        else:
            print("Invalid input. Please enter 'yes' or 'no'.")

def set_start_node(story_data: dict):
    """Sets the start node for the story."""
    while True:
        start_node_id = input("Enter the ID of the node to be the start node: ")
        if start_node_id in story_data["nodes"]:
            story_data["start_node_id"] = start_node_id
            print(f"Node '{start_node_id}' set as the start node.")
            break
        elif not start_node_id:
            print("Start node ID cannot be empty.")
        else:
            print("Node ID not found. Please enter an existing node ID.")

def save_story(story_data: dict):
    """Saves the story to a JSON file."""
    while True:
        filename = input("Enter a filename to save the story (e.g., my_story.json): ").strip()
        if not filename:
            print("Filename cannot be empty.")
        elif not filename.endswith(".json"):
            filename += ".json" # Auto-append .json if not present
            print(f"Filename will be '{filename}'.")
            break
        else:
            break
            
    with open(filename, 'w') as f:
        json.dump(story_data, f, indent=2)
    print(f"Story saved to '{filename}'.")

def main():
    """Main function to run the story creator tool."""
    story_data = initialize_story()
    print("Welcome to the Story Creator Tool!")

    while True:
        title = input("Enter the title for your story: ").strip()
        if title:
            story_data["title"] = title
            break
        else:
            print("Title cannot be empty.")
    print(f"Story title set to: {story_data['title']}")

    # Requirement 1: max_players
    while True:
        try:
            mp_input = input("Enter maximum number of players for this story (e.g., 2, default 1): ").strip()
            if not mp_input:
                story_data["max_players"] = 1 # Default
                print(f"Maximum players set to default: {story_data['max_players']}.")
                break
            max_p = int(mp_input)
            if max_p <= 0:
                print("Maximum players must be a positive integer.")
            else:
                story_data["max_players"] = max_p
                print(f"Maximum players set to: {story_data['max_players']}.")
                break
        except ValueError:
            print("Invalid input. Please enter a number.")

    # --- Global Initial Stats (Optional, for game state not tied to player templates) ---
    if input("Define global initial stats for the story (e.g., team_score)? (yes/no): ").lower() == 'yes':
        print("\n--- Defining Global Initial Stats ---")
        story_data["initial_stats"] = prompt_for_stats_dict() # Reusing new helper
    
    # --- Global Initial Inventory (Optional) ---
    if input("\nDefine global initial inventory items for the story? (yes/no): ").lower() == 'yes':
        print("\n--- Defining Global Initial Inventory ---")
        story_data["initial_inventory"] = prompt_for_inventory_list() # Reusing new helper


    while True:
        print("\n--- Main Menu ---")
        print("1. Add a new node")
        print("2. Set the story's main start node")
        print("3. Manage Player Character Templates") # Requirement 2
        print("4. Save and exit")
        # Future: print("5. Edit an existing node")
        # Future: print("6. Edit story details (title, max_players, global stats/inventory)")

        choice = input("Enter your choice: ")

        if choice == '1':
            add_node(story_data)
        elif choice == '2':
            if not story_data["nodes"]:
                print("Please add some nodes before setting a start node.")
            else:
                set_start_node(story_data) # Sets the global start_node_id
        elif choice == '3':
            manage_player_templates(story_data) # New function for Requirement 2
        elif choice == '4':
            if not story_data["start_node_id"] and story_data["nodes"]:
                print("Warning: The main story start node has not been set.")
            # Additional check: if templates define role-specific start nodes, but no global start node, it might be okay.
            # For now, a global start node is still generally recommended as a fallback.
            save_story(story_data)
            break
        else:
            print("Invalid choice. Please enter a valid number.")

if __name__ == "__main__":
    main()
