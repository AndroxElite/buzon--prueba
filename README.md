# Buzón de Sugerencias — Americar

App interactiva para clasificar y priorizar los comentarios del buzón de sugerencias.

## Pantallas

- **Buzón**: sube el Excel con los comentarios nuevos. Se clasifican automáticamente por prioridad y categoría ("Derivar a").
- **Nómina**: sube la plantilla completa de la empresa (RUT + estado laboral). Se usa para descartar automáticamente comentarios de ex-colaboradores.
- **Áreas**: edita las palabras clave que determinan a qué categoría/departamento se deriva cada comentario, según su contenido.

## Correr localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Notas

- La detección de prioridad y las palabras clave son un punto de partida — se recomienda calibrarlas contra un set de comentarios clasificados manualmente antes de usar en producción.
- Las reglas editadas en la pantalla "Áreas" no se guardan entre sesiones (se pierden al cerrar/recargar). Para persistencia real hace falta conectar una base de datos.
