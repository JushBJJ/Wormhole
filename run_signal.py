import time

from bot.signal import SignalBot

def main():
    bot = SignalBot('signal-cli', ['receive', '-t', '3'])
    bot.start_wormhole()

if __name__=="__main__":
    main()