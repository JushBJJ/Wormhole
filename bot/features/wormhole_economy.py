from bot.config import WormholeConfig

class WormholeEconomy:
    def __init__(self, config: WormholeConfig):
        self.config = config

    def mint_coins(self, user_id: int, difficulty: int):
        user_config = self.config.users.get(str(user_id))
        if not user_config:
            return

        base_reward = self.config.economy.base_reward
        total_supply = self.config.economy.total_coin_supply
        coins_minted = self.config.economy.coins_minted

        remaining_coins = total_supply - coins_minted
        remaining_percentage = remaining_coins / total_supply
        adjusted_base_reward = base_reward * (1 + (1 - remaining_percentage))
        coins_to_mint = int(adjusted_base_reward * (difficulty + 1))
        coins_to_mint = min(coins_to_mint, remaining_coins)

        user_config.wormhole_coins += coins_to_mint
        self.config.economy.coins_minted += coins_to_mint

        print(f"User {user_id} minted {coins_to_mint} coins at difficulty {difficulty}")

        return coins_to_mint

    def deduct_coins(self, user_id: int, amount: int) -> bool:
        user_config = self.config.get_user_config_by_id(user_id)
        if not user_config or user_config.wormhole_coins < amount:
            return False

        user_config.wormhole_coins -= amount
        return True