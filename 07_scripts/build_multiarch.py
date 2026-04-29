import subprocess
import sys
import argparse

def run_build(image_name, dockerfile, platforms="linux/amd64,linux/arm64"):
    print(f"[*] Iniciando construcción multi-arquitectura para {image_name}...")
    cmd = [
        "docker", "buildx", "build",
        "--platform", platforms,
        "-t", image_name,
        "-f", dockerfile,
        ".",
        "--push" # Nota: Requiere haber hecho login en un registry o usar un driver local
    ]
    
    # Si no hay registry configurado, usar --load para el host local (solo una plataforma a la vez)
    if "--local" in sys.argv:
        print("[!] Modo local: Solo se cargará la arquitectura nativa (amd64).")
        cmd = [
            "docker", "build",
            "-t", image_name,
            "-f", dockerfile,
            "."
        ]

    try:
        subprocess.run(cmd, check=True)
        print(f"[OK] Imagen {image_name} construida exitosamente.")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Falló la construcción de {image_name}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True, help="Nombre de la imagen")
    parser.add_argument("--file", required=True, help="Dockerfile a usar")
    parser.add_argument("--local", action="store_true", help="Construcción local (solo amd64)")
    args = parser.parse_args()
    
    run_build(args.image, args.file)
