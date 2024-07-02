from bot.config import compute_user_hash
from bot.config import WormholeConfig, UserConfig

class UserManagement:
    def __init__(self, config: WormholeConfig):
        self.config = config

    def add_user(self, user_id: int, role: str = "user") -> UserConfig:
        user = UserConfig(hash=compute_user_hash(self, user_id), role=role)
        self.config.users[str(user_id)] = user
        return user

    def get_user(self, user_id: int) -> UserConfig:
        return self.config.users.get(str(user_id))

    def update_user_role(self, user_id: int, new_role: str) -> bool:
        if str(user_id) in self.config.users:
            self.config.users[str(user_id)].role = new_role
            return True
        return False

    def remove_user(self, user_id: int) -> bool:
        if str(user_id) in self.config.users:
            del self.config.users[str(user_id)]
            return True
        return False

    def is_user_banned(self, user_id: int) -> bool:
        return user_id in self.config.banned_users