import secrets
import string

def generate_salt(length=128):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

salt = generate_salt()
print(salt)