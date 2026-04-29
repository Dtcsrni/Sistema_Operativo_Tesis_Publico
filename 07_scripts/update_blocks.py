import json

path = "v:/Sistema_Operativo_Tesis_Posgrado/00_sistema_tesis/config/bloques.yaml"
with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)

for bloque in data["bloques"]:
    if bloque["id"] == "B0":
        bloque["estado"] = "cerrado"
    elif bloque["id"] == "B1":
        bloque["estado"] = "activo"

with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("[OK] bloques.yaml actualizado.")
