# Relacion entre Repo Privado y Publico

El privado es upstream canonico. El publico es downstream sanitizado, derivado automaticamente y destinado a exposicion externa.

- Solo `main` del repo privado tiene autoridad para publicar al repo publico.
- El repo publico remoto se actualiza automaticamente despues de `verify` exitoso en GitHub Actions.
- El clon local hermano `../Sistema_Operativo_Tesis_Publico` se resincroniza automaticamente mediante hooks locales al hacer commit o merge en `main`.
- Nunca se corrige a mano el repo publico; toda correccion nace en el upstream privado y se reproyecta.
