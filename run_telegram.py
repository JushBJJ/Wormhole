from bot.telegram import TelegramBot

def main():
    bot = TelegramBot()
    bot.start_wormhole()
    
if __name__=="__main__":
    main()