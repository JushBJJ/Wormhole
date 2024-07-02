from bot.config import WormholeConfig, RoleConfig

class RoleManagement:
    def __init__(self, config: WormholeConfig):
        self.config = config

    def add_role(self, role_name: str, color: str, permissions: list) -> bool:
        if role_name not in self.config.roles:
            self.config.roles[role_name] = RoleConfig(color=color, permissions=permissions)
            return True
        return False

    def remove_role(self, role_name: str) -> bool:
        if role_name in self.config.roles:
            del self.config.roles[role_name]
            return True
        return False

    def update_role(self, role_name: str, color: str = None, permissions: list = None) -> bool:
        if role_name in self.config.roles:
            if color:
                self.config.roles[role_name].color = color
            if permissions:
                self.config.roles[role_name].permissions = permissions
            return True
        return False

    def get_role(self, role_name: str) -> RoleConfig:
        return self.config.roles.get(role_name)

    def get_all_roles(self) -> dict:
        return self.config.roles

    def has_permission(self, user_id: int, permission: str) -> bool:
        user = self.config.users.get(str(user_id))
        if user:
            role = self.config.roles.get(user.role)
            if role:
                return permission in role.permissions
        return False