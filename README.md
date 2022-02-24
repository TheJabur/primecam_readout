# CCATpHive

## File Descriptions:
- queen.py: Runs on the command server to publish commands to remote boards, and to listen for messages from the boards. Should be running at all times to pick up board meessages.
- queen_tui.py: A terminal interface to queen.py.
- drone.py: Runs on each of the boards and listens for commands. Upon receiving a command it asks alcove.py to execute it and publishes any necessary messages, e.g. the return statement. Should be running at all times to hear commands.
- alcove.py: Contains the main board functionality functions (commands).
- alcove_tui.py: A terminal interface to alcove.py.

## Redis Channels:
- There is a command channel to send to all boards at once (all_boards)
- Each board has it's own command channel (board_[bid]) and return channel (board_rets_[bid]).