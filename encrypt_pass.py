from cryptography.fernet import Fernet
import getpass

# Genera una clave y la muestra para guardar (solo la primera vez)
key = Fernet.generate_key()
print("Guarda esta clave en un lugar seguro como ENCRYPT_KEY en tu .env:")
print(key.decode())

f = Fernet(key)
password = getpass.getpass("Introduce la contraseña SMTP: ")
token = f.encrypt(password.encode())
print("\nPega esto en tu .env como EMAIL_HOST_PASSWORD:")
print(token.decode())
