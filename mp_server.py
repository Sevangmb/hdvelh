import asyncio
import json
import random # For selecting first player if needed

STORY_DATA = {}
MAX_PLAYERS = 0
connected_clients = [] # List of (asyncio.StreamWriter, player_id_temp) before role selection
players_data = {} # player_id: { "writer": writer, "role": role, "stats": {}, "inventory": [], "id": player_id }
player_id_counter = 1

game_state = {
    "current_node_id": None,
    "game_active": False,
    "vote_in_progress": False,
    "vote_choice_data": None,
    "vote_timer_task": None,
    "player_votes": {}, # player_id: "yes"/"no"
    "current_turn_player_idx": 0,
    "available_roles": []
}

# --- Utility Functions ---
async def broadcast(message, exclude_player_id=None, target_player_id=None):
    """Sends a message to players. Can exclude one or target one."""
    print(f"Broadcasting: {message} (Exclude: {exclude_player_id}, Target: {target_player_id})")
    if target_player_id:
        player = players_data.get(target_player_id)
        if player and player["writer"]:
            try:
                player["writer"].write(f"{message}\n".encode())
                await player["writer"].drain()
            except ConnectionResetError:
                await handle_disconnect(target_player_id, player["writer"])
            except Exception as e:
                print(f"Error sending to {target_player_id}: {e}")
        return

    for pid, player in players_data.items():
        if pid == exclude_player_id or not player["writer"]:
            continue
        try:
            player["writer"].write(f"{message}\n".encode())
            await player["writer"].drain()
        except ConnectionResetError:
            await handle_disconnect(pid, player["writer"]) # Schedule disconnect handling
        except Exception as e:
            print(f"Error broadcasting to {pid}: {e}")


async def send_to_player(player_id, message):
    await broadcast(message, target_player_id=player_id)

async def end_game(reason="Game ended."):
    if not game_state["game_active"]:
        return
    game_state["game_active"] = False
    game_state["vote_in_progress"] = False
    if game_state["vote_timer_task"] and not game_state["vote_timer_task"].done():
        game_state["vote_timer_task"].cancel()
    
    await broadcast(f"GAME_END:{reason}")
    for pid, player_data in list(players_data.items()): # Iterate over a copy for modification
        writer = player_data["writer"]
        if writer and not writer.is_closing():
            writer.close()
            try:
                await writer.wait_closed()
            except Exception as e:
                print(f"Error during writer close for {pid}: {e}")
    
    # Reset server state for a potential new game (simplified for PoC)
    connected_clients.clear()
    players_data.clear()
    global player_id_counter
    player_id_counter = 1 # Reset for new connections if server stays up
    game_state["current_node_id"] = None
    game_state["current_turn_player_idx"] = 0
    game_state["available_roles"] = list(STORY_DATA.get("player_character_templates", {}).keys())


    print(f"Game ended: {reason}. Server ready for new connections if applicable.")


def get_player_by_writer(writer_to_find):
    for pid, data in players_data.items():
        if data["writer"] is writer_to_find:
            return pid, data
    # Check temporary connections too
    for writer, temp_id in connected_clients:
        if writer is writer_to_find:
            return temp_id, {"writer": writer, "id": temp_id} # Partial data for temp client
    return None, None

async def handle_disconnect(player_id, writer):
    print(f"Player {player_id} disconnected or connection error.")
    
    # Remove from active players
    if player_id in players_data:
        del players_data[player_id]
        await broadcast(f"PLAYER_LEFT:{player_id} has left the game.")
    
    # Remove from temporary connections if they hadn't chosen a role yet
    client_to_remove = None
    for client_writer, cid in connected_clients:
        if client_writer == writer : # Check by writer object if player_id was temp
            client_to_remove = (client_writer, cid)
            break
    if client_to_remove:
        connected_clients.remove(client_to_remove)
        print(f"Temporary client {client_to_remove[1]} removed.")


    if writer and not writer.is_closing():
        writer.close()
        try:
            await writer.wait_closed()
        except Exception as e:
            print(f"Error closing writer for {player_id}: {e}")

    if game_state["game_active"] and len(players_data) < MAX_PLAYERS:
        await end_game(f"Player {player_id} disconnected. Not enough players to continue.")
    elif not game_state["game_active"] and len(players_data) < MAX_PLAYERS:
        # If game hasn't started, just update available roles if the player had picked one (not implemented here)
        print("A player disconnected before the game started.")


# --- Game Logic Functions ---
def apply_effects_to_player(player_id, effects_list):
    player = players_data.get(player_id)
    if not player or not effects_list:
        return

    for effect in effects_list:
        effect_type = effect.get("type")
        if effect_type == "stat_change":
            stat_name = effect.get("stat")
            if stat_name:
                change_by = effect.get("change_by")
                set_to = effect.get("set_to")
                if change_by is not None:
                    player["stats"][stat_name] = player["stats"].get(stat_name, 0) + change_by
                elif set_to is not None:
                    player["stats"][stat_name] = set_to
                print(f"Applied stat_change to {player_id}: {stat_name} now {player['stats'][stat_name]}")
        elif effect_type == "inventory_change":
            item_name = effect.get("item")
            action = effect.get("action")
            if item_name and action:
                if action == "add" and item_name not in player["inventory"]:
                    player["inventory"].append(item_name)
                    print(f"Applied inventory_change to {player_id}: added {item_name}")
                elif action == "remove" and item_name in player["inventory"]:
                    player["inventory"].remove(item_name)
                    print(f"Applied inventory_change to {player_id}: removed {item_name}")
    
    # Broadcast player update
    updated_data = {"stats": player["stats"], "inventory": player["inventory"]}
    asyncio.create_task(broadcast(f"PLAYER_UPDATE:{player_id}:{json.dumps(updated_data)}"))


def check_conditions_for_player(player_id, conditions_list):
    player = players_data.get(player_id)
    if not player or not conditions_list:
        return True # No conditions means they are met

    for condition in conditions_list:
        condition_type = condition.get("type")
        if condition_type == "stat_condition":
            stat_name = condition.get("stat")
            current_val = player["stats"].get(stat_name, 0)
            if condition.get("requires_greater_than") is not None and not current_val > condition["requires_greater_than"]: return False
            if condition.get("requires_less_than") is not None and not current_val < condition["requires_less_than"]: return False
            if condition.get("requires_equal_to") is not None and not current_val == condition["requires_equal_to"]: return False
        elif condition_type == "inventory_condition":
            item_name = condition.get("item")
            requirement = condition.get("requires")
            if requirement == "present" and item_name not in player["inventory"]: return False
            if requirement == "absent" and item_name in player["inventory"]: return False
    return True

def get_current_player_id():
    if not players_data or not game_state["game_active"]:
        return None
    player_ids = list(players_data.keys())
    return player_ids[game_state["current_turn_player_idx"]]

def advance_turn():
    game_state["current_turn_player_idx"] = (game_state["current_turn_player_idx"] + 1) % len(players_data)
    current_player_id = get_current_player_id()
    if current_player_id:
        asyncio.create_task(broadcast(f"TURN:{current_player_id}"))
        asyncio.create_task(send_to_player(current_player_id, "YOUR_TURN:It's your turn to act."))


async def send_node_to_players(acting_player_id_override=None):
    """acting_player_id_override is for when an action immediately leads to a new state for the same player"""
    if not game_state["current_node_id"] or not game_state["game_active"]:
        return

    node_data = STORY_DATA['nodes'].get(game_state["current_node_id"])
    if not node_data:
        await end_game(f"Error: Node '{game_state['current_node_id']}' not found.")
        return

    current_player_id_for_node = acting_player_id_override if acting_player_id_override else get_current_player_id()
    
    # Text replacement
    node_text = node_data['text']
    if current_player_id_for_node: # Might be None if game ending
        node_text = node_text.replace("{current_player_name}", players_data[current_player_id_for_node]['role']) # Use role as name for now
        node_text = node_text.replace("{acting_player_name}", players_data[current_player_id_for_node]['role']) 
    
    await broadcast(f"NODE_TEXT:{node_text}")

    if not node_data.get('choices'):
        await end_game("Story ended: No more choices.")
        return

    # Check for voting choices first
    voting_choice = next((c for c in node_data['choices'] if c.get("requires_vote")), None)
    if voting_choice:
        if game_state["vote_in_progress"]: return # Should not happen
        game_state["vote_in_progress"] = True
        game_state["vote_choice_data"] = voting_choice
        game_state["player_votes"] = {}
        timeout = 30
        await broadcast(f"VOTE_START:{voting_choice['text']}:timeout={timeout}")
        if game_state["vote_timer_task"] and not game_state["vote_timer_task"].done():
            game_state["vote_timer_task"].cancel()
        game_state["vote_timer_task"] = asyncio.create_task(vote_timeout_logic(timeout))
    else: # Individual choices
        if not current_player_id_for_node: # Should not happen if game active
             print("Error: No current player for individual choices.")
             return

        active_player_role = players_data[current_player_id_for_node]["role"]
        available_choices_for_player = []
        for idx, choice_data in enumerate(node_data['choices']):
            conditions_met = check_conditions_for_player(current_player_id_for_node, choice_data.get("conditions"))
            role_match = True # Assume true unless actionable_by_roles is present
            if "actionable_by_roles" in choice_data:
                role_match = active_player_role in choice_data["actionable_by_roles"]
            
            if conditions_met and role_match:
                available_choices_for_player.append({"text": choice_data['text'], "original_index": idx})
        
        if available_choices_for_player:
            choices_str = "|".join([f"{i+1}. {c['text']}" for i, c in enumerate(available_choices_for_player)])
            await send_to_player(current_player_id_for_node, f"ACTIVE_PLAYER_CHOICES:{choices_str}")
        else:
            await send_to_player(current_player_id_for_node, "INFO:No actions available for you this turn or for your role.")
            # Potentially auto-advance turn if no choices for current player
            # For now, this might stall if a player has no choices.
            # A more robust system would check this or have a default "pass" action.
            await asyncio.sleep(1) # Give a moment
            advance_turn()
            await send_node_to_players() # Send next player the node


async def vote_timeout_logic(timeout_seconds):
    await asyncio.sleep(timeout_seconds)
    if game_state["vote_in_progress"]:
        print("Vote timed out.")
        await broadcast("VOTE_TIMEOUT:The vote has timed out.")
        await process_vote_outcome()

async def process_vote_outcome():
    if not game_state["vote_in_progress"]: return

    game_state["vote_in_progress"] = False
    yes_votes = sum(1 for vote in game_state["player_votes"].values() if vote == "yes")
    no_votes = sum(1 for vote in game_state["player_votes"].values() if vote == "no")
    total_players_with_roles = len(players_data) # Count players who have selected roles

    outcome_message = ""
    vote_passed = False

    if len(game_state["player_votes"]) == total_players_with_roles: # All voted
        if yes_votes > no_votes: # Majority wins
            vote_passed = True
        outcome_message = f"Vote for '{game_state['vote_choice_data']['text']}' {'passed' if vote_passed else 'failed'}! ({yes_votes} yes, {no_votes} no)"
    else: # Timeout or not all voted
        # PoC: if not everyone votes, it fails (could be majority of actual votes cast too)
        vote_passed = False 
        outcome_message = f"Vote for '{game_state['vote_choice_data']['text']}' timed out or not all voted, outcome: failed. ({yes_votes} yes, {no_votes} no, {total_players_with_roles - len(game_state['player_votes'])} did not vote)"
    
    await broadcast(f"VOTE_RESULT:{'passed' if vote_passed else 'failed'}:{outcome_message}")
    game_state["player_votes"] = {}

    target_node = None
    if vote_passed:
        target_node = game_state["vote_choice_data"].get("target_node_id")
        # Apply global effects of the vote (if any) - not player specific
        if "effects" in game_state["vote_choice_data"]:
            # These are global effects. For PoC, assume they are handled by story (e.g. team_morale)
            # or apply to all players if that's the design.
            # For now, we'll just print them. A real system needs a target for these effects.
            print(f"Global effects for passed vote: {game_state['vote_choice_data']['effects']}")
            # Example: for effect in game_state["vote_choice_data"]["effects"]: if effect["stat"] == "team_morale": update_global_stat("team_morale", ...)
    else: # Vote failed
        current_node_data = STORY_DATA['nodes'][game_state["current_node_id"]]
        # Find a fallback choice if vote fails (e.g., a choice not requiring a vote or a default path)
        # This part of logic needs refinement based on story design.
        # For mp_story_phase1, there isn't an explicit "else" path for the vote.
        # We might just re-present the node or end if no alternative.
        # For now, let's assume the story continues from the same node, and it's next player's turn.
        await broadcast("INFO:The vote failed. The situation remains.")
        # No target_node means we stay, advance turn and re-evaluate.


    if target_node:
        game_state["current_node_id"] = target_node
    
    # Whether vote passed or failed, it's usually the end of the "group action" part of the turn.
    # Advance turn and send new node state.
    advance_turn() 
    await send_node_to_players()


# --- Network Handling ---
async def handle_client_connection(reader, writer):
    global player_id_counter, MAX_PLAYERS, game_state
    
    temp_player_id = f"Player_{player_id_counter}"
    player_id_counter += 1
    addr = writer.get_extra_info('peername')
    print(f"Incoming connection from {addr}, temp ID: {temp_player_id}")

    if len(players_data) + len(connected_clients) >= MAX_PLAYERS and not any(w == writer for w, _ in connected_clients):
        print(f"Refusing connection from {addr}: server full.")
        writer.write("SERVER_FULL:Server is full.\n".encode())
        await writer.drain()
        writer.close(); await writer.wait_closed()
        return

    connected_clients.append((writer, temp_player_id))
    writer.write(f"WELCOME:{temp_player_id}:Welcome! Choose your role.\n".encode())
    await writer.drain()
    
    roles_str = ",".join(game_state["available_roles"])
    writer.write(f"ROLES_AVAILABLE:{roles_str}\n".encode())
    await writer.drain()

    player_id_for_logic = temp_player_id # This will be replaced by chosen role if unique, or kept if not unique for some reason
    player_role_chosen = False

    try:
        while True: # Loop for role selection and then game messages
            data = await reader.readline()
            if not data:
                # If data is empty, client disconnected before role selection or during game
                # Find which player_id this writer corresponds to for proper cleanup
                pid, _ = get_player_by_writer(writer) # May be temp_id or actual role id
                if pid: await handle_disconnect(pid, writer)
                else: print(f"Unknown client disconnected from {addr}")
                break 
            
            message = data.decode().strip()
            print(f"Received from {temp_player_id} ({addr}): {message}")

            # --- Role Selection Phase ---
            if not player_role_chosen and message.startswith("ROLE:"):
                chosen_role = message.split(":", 1)[1]
                if chosen_role in game_state["available_roles"]:
                    game_state["available_roles"].remove(chosen_role) # Make role unavailable
                    
                    # Transition from temp client to actual player
                    connected_clients.remove((writer, temp_player_id))
                    player_id_for_logic = chosen_role # Use Role as Player ID for this phase
                    
                    template = STORY_DATA["player_character_templates"][chosen_role]
                    players_data[player_id_for_logic] = {
                        "writer": writer,
                        "role": chosen_role,
                        "stats": dict(template.get("initial_stats", {})), # Deep copy
                        "inventory": list(template.get("initial_inventory", [])), # Deep copy
                        "id": player_id_for_logic
                    }
                    player_role_chosen = True
                    await send_to_player(player_id_for_logic, f"ROLE_CONFIRMED:{chosen_role}:Your stats: {json.dumps(players_data[player_id_for_logic]['stats'])}. Inventory: {json.dumps(players_data[player_id_for_logic]['inventory'])}")
                    await broadcast(f"PLAYER_JOINED:{chosen_role} has joined the game.", exclude_player_id=player_id_for_logic)

                    if len(players_data) == MAX_PLAYERS and not game_state["game_active"]:
                        game_state["game_active"] = True
                        game_state["current_node_id"] = STORY_DATA['start_node_id']
                        # Randomly pick starting player or default to first who joined/chose role
                        game_state["current_turn_player_idx"] = 0 # Or random.randrange(MAX_PLAYERS)
                        
                        await broadcast("GAME_START:All players have chosen roles. The adventure begins!")
                        # Announce first turn
                        first_player_id = list(players_data.keys())[game_state["current_turn_player_idx"]]
                        await broadcast(f"TURN:{first_player_id}")
                        await send_to_player(first_player_id, "YOUR_TURN:It's your turn to act.")
                        await send_node_to_players()

                else: # Role not available or invalid
                    await send_to_player(temp_player_id, f"ERROR:Role '{chosen_role}' is not available or invalid. Available: {','.join(game_state['available_roles'])}")

            # --- Game Phase ---
            elif player_role_chosen and game_state["game_active"]:
                current_player_id = get_current_player_id()

                if message.startswith("CHOICE:") and player_id_for_logic == current_player_id and not game_state["vote_in_progress"]:
                    try:
                        choice_idx_from_player = int(message.split(":", 1)[1]) -1 # 1-based from player
                        
                        # Re-filter choices for the current player to map choice_idx_from_player
                        node_data = STORY_DATA['nodes'][game_state["current_node_id"]]
                        active_player_role = players_data[current_player_id]["role"]
                        
                        valid_choices_for_active_player = []
                        for c_data in node_data['choices']:
                            if c_data.get("requires_vote"): continue # Should not be handled here
                            conditions_met = check_conditions_for_player(current_player_id, c_data.get("conditions"))
                            role_match = True
                            if "actionable_by_roles" in c_data:
                                role_match = active_player_role in c_data["actionable_by_roles"]
                            if conditions_met and role_match:
                                valid_choices_for_active_player.append(c_data)

                        if 0 <= choice_idx_from_player < len(valid_choices_for_active_player):
                            chosen_action_data = valid_choices_for_active_player[choice_idx_from_player]
                            
                            action_text = chosen_action_data['text'].replace("{acting_player_name}", players_data[current_player_id]['role'])
                                                                    
                            await broadcast(f"PLAYER_ACTION:{current_player_id} (as {players_data[current_player_id]['role']}) chose: '{action_text}'")

                            if "effects_for_chooser" in chosen_action_data:
                                apply_effects_to_player(current_player_id, chosen_action_data["effects_for_chooser"])
                            
                            game_state["current_node_id"] = chosen_action_data["target_node_id"]
                            # If player acts, it's their turn again for the new node's text, but then turn advances.
                            # Or, advance turn first, then send node. Let's try advancing turn first.
                            advance_turn()
                            await send_node_to_players() 

                        else:
                            await send_to_player(current_player_id, "ERROR:Invalid choice index.")
                    except ValueError:
                        await send_to_player(current_player_id, "ERROR:Invalid choice format. Send CHOICE:number.")
                
                elif message.startswith("VOTE:") and game_state["vote_in_progress"]:
                    vote_value = message.split(":",1)[1].lower()
                    if vote_value in ["yes", "no"]:
                        if player_id_for_logic not in game_state["player_votes"]:
                            game_state["player_votes"][player_id_for_logic] = vote_value
                            await broadcast(f"PLAYER_VOTED:{player_id_for_logic} (as {players_data[player_id_for_logic]['role']}) has voted.")
                            if len(game_state["player_votes"]) == len(players_data): # All active players voted
                                if game_state["vote_timer_task"] and not game_state["vote_timer_task"].done():
                                    game_state["vote_timer_task"].cancel() # Cancel timer
                                await process_vote_outcome()
                        else:
                            await send_to_player(player_id_for_logic, "INFO:You have already voted.")
                    else:
                        await send_to_player(player_id_for_logic, "ERROR:Invalid vote. Send VOTE:yes or VOTE:no.")
                # else:
                #     await send_to_player(player_id_for_logic, "ERROR:Not your turn or no action expected.")

    except ConnectionResetError:
        print(f"Connection reset by {addr} (ID: {player_id_for_logic if player_role_chosen else temp_player_id})")
        await handle_disconnect(player_id_for_logic if player_role_chosen else temp_player_id, writer)
    except asyncio.CancelledError:
        print(f"Client handler for {player_id_for_logic if player_role_chosen else temp_player_id} cancelled.")
        # Ensure cleanup if task is cancelled externally
        await handle_disconnect(player_id_for_logic if player_role_chosen else temp_player_id, writer)
    except Exception as e:
        print(f"Unhandled error for {player_id_for_logic if player_role_chosen else temp_player_id} ({addr}): {e}")
        await handle_disconnect(player_id_for_logic if player_role_chosen else temp_player_id, writer)
    finally:
        # Final cleanup if not already handled by a specific disconnect path
        # This ensures writer is closed even if loop exits unexpectedly
        if writer and not writer.is_closing():
            writer.close()
            try:
                await writer.wait_closed()
            except: pass # Ignore errors during final cleanup
        
        # Check if player_id_for_logic was ever promoted from temp_player_id
        final_id_to_check = player_id_for_logic if player_role_chosen else temp_player_id
        is_temp = not player_role_chosen

        if is_temp and any(w == writer for w, tid in connected_clients if tid == final_id_to_check):
            connected_clients.remove((writer, final_id_to_check))
            print(f"Temporary client {final_id_to_check} cleaned up from connected_clients.")
        elif not is_temp and final_id_to_check in players_data and players_data[final_id_to_check]["writer"] == writer:
             # This case should ideally be caught by handle_disconnect, but as a safeguard:
            if final_id_to_check in players_data: # Check again as handle_disconnect might have run
                del players_data[final_id_to_check]
                print(f"Player {final_id_to_check} cleaned up from players_data.")
                # Potential broadcast if game was active and player dropped.
                if game_state["game_active"]:
                     asyncio.create_task(broadcast(f"PLAYER_LEFT:{final_id_to_check} has left the game unexpectedly."))
                     if len(players_data) < MAX_PLAYERS:
                         asyncio.create_task(end_game(f"Player {final_id_to_check} disconnected. Not enough players."))


async def main_server():
    global STORY_DATA, MAX_PLAYERS, game_state
    try:
        with open("mp_story_phase1.json", 'r') as f:
            STORY_DATA = json.load(f)
        MAX_PLAYERS = STORY_DATA.get("max_players", 1)
        game_state["available_roles"] = list(STORY_DATA.get("player_character_templates", {}).keys())
        if not game_state["available_roles"]:
            print("Error: No player character templates defined in the story file!")
            return
    except FileNotFoundError:
        print("Error: mp_story_phase1.json not found.")
        return
    except json.JSONDecodeError:
        print("Error: mp_story_phase1.json is not valid JSON.")
        return

    server = await asyncio.start_server(
        handle_client_connection, '127.0.0.1', 8889) # Changed port to 8889

    addr = server.sockets[0].getsockname()
    print(f'HDVELH Multiplayer Phase 1 Server serving on {addr}')

    async with server:
        await server.serve_forever()

if __name__ == '__main__':
    try:
        asyncio.run(main_server())
    except KeyboardInterrupt:
        print("Server shutting down manually.")
    except Exception as e:
        print(f"Server encountered a critical unhandled error: {e}")
    finally:
        print("Server shutdown sequence complete.")
