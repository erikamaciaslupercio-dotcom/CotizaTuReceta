# Cotizador de Recetas

Proyecto inicial para publicar la aplicación en Streamlit Community Cloud.

## Archivos
- `app.py`: código de la aplicación.
- `requirements.txt`: dependencias que instala Streamlit.
- `README.md`: estas instrucciones.

## Publicar
1. Crea un repositorio en https://github.com/
2. Sube `app.py`, `requirements.txt` y `README.md` a la raíz del repositorio.
3. Entra en https://share.streamlit.io/ e inicia sesión con GitHub.
4. Selecciona el repositorio, la rama `main` y el archivo principal `app.py`.
5. Pulsa **Deploy**.

## Importante antes de usarla públicamente
- La app lee el catálogo desde Google Sheets. Verifica que la hoja permita exportar CSV y que solo contenga información que quieras exponer.
- Las recetas se guardan en `recetas_guardadas.json`. En Streamlit Community Cloud los archivos locales no deben considerarse almacenamiento permanente; podrían perderse al reiniciar o volver a desplegar la app.
- Revisa las unidades del catálogo: la cantidad introducida en una receta debe coincidir con la unidad usada en `Costo por unidad`.
- No guardes contraseñas ni claves privadas dentro del código ni las subas a GitHub.
