# Personal Problems (Fix ASAP)

## ALEX
1. Button to remove words we dont like, should save the new state of the list after removing (if button.onPress: wordlist.remove(current_word)) kind of thing
2. Function to take a string and write it to the END (so we can find and remove it if necessary) of the word list

## ALISTAIR
1. Alistair needs to remove magic variables that broke font size when swapping font
2. Fix ur text wrapping, it breaks when you type more than 0.000001 characters, probably ur shitty variable names, cunt, kys.

## TOMMY
1. END, HOME and DEL should do their thing in text boxes
2. Input box's have different outline when selected
3. Learn how to hse markdown, THERE ARE SPACES AFTER A HASHTAG
4. Please load up add.png and minus.png side by side and just swap between them... youll see it

# Features to add

- Title screen with prompts to log into a server
- Rendering the word (or lack there off) (the client allready gets this send by the server)
- Game logic modes (?)
- The server now has request_game_start, needs to be added when in the lobby
- The server now has request_word_skip, needs to be added when in game
- The server now has .word_pattern, needs to be rendered when in game
- The settings now has username, IP and Port, a settings or login page that updates them is needed.
- The server sends formatted messages _WON and _LOST, these need to be rendered with nice messages.