import asyncio
import sys

player_id = None
is_my_turn = False
expecting_role_choice = False
expecting_action_choice = False
expecting_vote = False

async def display_server_message(message):
    """Helper to print server messages, could be expanded for UI."""
    global is_my_turn, expecting_role_choice, expecting_action_choice, expecting_vote

    print(f"[Server] {message}")

    if message.startswith("WELCOME:"):
        parts = message.split(":", 2)
        # global player_id # Not strictly needed if only one client instance per script
        # player_id = parts[1] # Store our assigned temp ID
        print(f"You are connected. Your temporary ID is {parts[1]}.")
        expecting_role_choice = True
    elif message.startswith("ROLES_AVAILABLE:"):
        roles = message.split(":",1)[1]
        print(f"Available roles: {roles}. Choose one by typing 'ROLE:YourChosenRoleName'")
    elif message.startswith("ROLE_CONFIRMED:"):
        parts = message.split(":",2)
        confirmed_role = parts[1]
        global player_id # Now set the actual player ID to the role name
        player_id = confirmed_role
        print(f"Role confirmed: You are {player_id}.")
        print(f"Initial state: {parts[2]}")
        expecting_role_choice = False
    elif message.startswith("SERVER_FULL:") or message.startswith("GAME_END:"):
        print("Exiting client.")
        asyncio.get_event_loop().stop()
    elif message.startswith("YOUR_TURN:"):
        is_my_turn = True
        print("It's YOUR turn to act.")
        # Server will follow up with ACTIVE_PLAYER_CHOICES if actions are available
    elif message.startswith("TURN:"):
        current_turn_player = message.split(":",1)[1]
        if current_turn_player != player_id:
            is_my_turn = False
            print(f"It is now {current_turn_player}'s turn.")
        else: # Should be caught by YOUR_TURN but as a fallback
            is_my_turn = True
            print("It's YOUR turn.")
    elif message.startswith("ACTIVE_PLAYER_CHOICES:"):
        if is_my_turn:
            choices_str = message.split(":",1)[1]
            choices = choices_str.split("|")
            print("Your available actions:")
            for choice in choices:
                print(f"  {choice}")
            print("Choose an action by typing 'CHOICE:number'.")
            expecting_action_choice = True
            expecting_vote = False # Not expecting vote if choosing action
        else:
            # If it's not our turn, we might still see choices for other players (if server broadcasts all)
            # For Phase 1, server sends ACTIVE_PLAYER_CHOICES only to active player.
            pass
    elif message.startswith("VOTE_START:"):
        vote_text = message.split(":",2)[1]
        print(f"A vote has started: '{vote_text}'.")
        print("Type 'VOTE:yes' or 'VOTE:no'.")
        expecting_vote = True
        expecting_action_choice = False # Not expecting action if voting
    elif message.startswith("VOTE_RESULT:"):
        expecting_vote = False # Vote concluded
    elif message.startswith("PLAYER_UPDATE:"):
        try:
            _, updated_pid, state_json = message.split(":", 2)
            state = json.loads(state_json)
            if updated_pid == player_id:
                print(f"Your state has been updated: Stats: {state.get('stats')}, Inv: {state.get('inventory')}")
            else:
                print(f"Player {updated_pid}'s state updated (details: {state_json}).")
        except Exception as e:
            print(f"Error parsing PLAYER_UPDATE: {e}")


async def receive_messages(reader):
    """Continuously receives messages from the server and displays them."""
    while True:
        try:
            data = await reader.readline()
            if not data:
                print("Server closed the connection.")
                break
            message = data.decode().strip()
            await display_server_message(message) # Use the new display helper

        except ConnectionResetError:
            print("Connection to the server was reset.")
            break
        except asyncio.CancelledError:
            print("Receive messages task cancelled.")
            break
        except Exception as e:
            print(f"Error receiving message: {e}")
            break
    
    if not asyncio.get_event_loop().is_running(): return
    asyncio.get_event_loop().stop()

async def send_user_input(writer):
    """Handles user input and sends messages to the server."""
    loop = asyncio.get_event_loop()
    global expecting_role_choice, expecting_action_choice, expecting_vote, is_my_turn
    
    while True:
        try:
            # Use run_in_executor for blocking input()
            raw_input_message = await loop.run_in_executor(None, sys.stdin.readline)
            input_message = raw_input_message.strip()

            if not writer.is_closing():
                if not input_message: continue # Skip empty inputs

                # Basic validation based on expected input state
                if expecting_role_choice and not input_message.upper().startswith("ROLE:"):
                    print("Please choose a role first, e.g., 'ROLE:Scout'")
                    continue
                elif is_my_turn and expecting_action_choice and not input_message.upper().startswith("CHOICE:"):
                    print("It's your turn to act. Please use 'CHOICE:number'.")
                    continue
                elif expecting_vote and not input_message.upper().startswith("VOTE:"):
                     print("A vote is in progress. Please use 'VOTE:yes' or 'VOTE:no'.")
                     continue

                writer.write(f"{input_message}\n".encode())
                await writer.drain()

                # Reset flags after sending
                if input_message.upper().startswith("ROLE:"): expecting_role_choice = False
                if input_message.upper().startswith("CHOICE:"): expecting_action_choice = False; is_my_turn = False # Turn ends after choice
                # expecting_vote is reset by VOTE_RESULT from server

                if input_message.lower() == "quit":
                    print("Disconnecting...")
                    break
            else:
                print("Writer is closing, cannot send message.")
                break
        except ConnectionResetError:
            print("Connection lost while trying to send.")
            break
        except asyncio.CancelledError:
            print("Send input task cancelled.")
            break
        except Exception as e:
            print(f"Error sending message: {e}")
            break
            
    if not writer.is_closing():
        writer.close()
        await writer.wait_closed()
    
    if not asyncio.get_event_loop().is_running(): return
    asyncio.get_event_loop().stop()

async def main_client_logic():
    print("Attempting to connect to HDVELH Phase 1 Server (127.0.0.1:8889)...")
    try:
        # Changed port to 8889
        reader, writer = await asyncio.open_connection('127.0.0.1', 8889) 
    except ConnectionRefusedError:
        print("Connection refused. Is the server running on port 8889?")
        return
    except Exception as e:
        print(f"Failed to connect: {e}")
        return

    print("Connected. Waiting for server messages. Type 'quit' to disconnect.")
    
    receive_task = asyncio.create_task(receive_messages(reader))
    send_task = asyncio.create_task(send_user_input(writer))

    try:
        # Keep main_client_logic alive until event loop is stopped by tasks
        await asyncio.Event().wait() 
    except asyncio.CancelledError:
        print("Client main logic cancelled.")
    finally:
        print("Cleaning up client resources...")
        if not writer.is_closing():
            writer.close()
            try: await writer.wait_closed()
            except: pass
        if not receive_task.done(): receive_task.cancel()
        if not send_task.done(): send_task.cancel()
        # Allow tasks to process cancellation
        await asyncio.sleep(0.1)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    client_task = None
    try:
        client_task = loop.create_task(main_client_logic())
        loop.run_forever() 
    except KeyboardInterrupt:
        print("Client shutting down (KeyboardInterrupt)...")
    finally:
        if client_task and not client_task.done():
            client_task.cancel()
            # Run loop briefly to allow task to cancel
            try: loop.run_until_complete(client_task) 
            except asyncio.CancelledError: pass 
            except Exception as e: print(f"Error during final task cancel: {e}")

        # Additional cleanup for any other tasks that might still be pending
        tasks = [t for t in asyncio.all_tasks(loop) if t is not asyncio.current_task(loop)]
        if tasks:
            for task in tasks: task.cancel()
            loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
        
        if loop.is_running(): # Stop loop if it hasn't been stopped by tasks
            loop.stop()
        if not loop.is_closed():
            loop.close()
        print("Client fully shut down.")
