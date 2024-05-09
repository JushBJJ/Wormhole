from bot.telegram import TelegramBot
from dotenv import load_dotenv

load_dotenv()

def main():
    bot = TelegramBot()
    bot.start_wormhole()
    
if __name__=="__main__":
    main()
