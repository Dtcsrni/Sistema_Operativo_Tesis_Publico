import hashlib
text = "implementalo, investiga las fuentes oficiales y descarga todo lo que sea necesario"
hash_val = hashlib.sha256(text.encode('utf-8')).hexdigest()
print(f"sha256:{hash_val}")
